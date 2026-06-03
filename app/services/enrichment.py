import anthropic
import httpx
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger


class EnrichmentService:
    def __init__(self):
        self.proxycurl_key = settings.proxycurl_api_key
        self.tavily = TavilyClient(api_key=settings.tavily_api_key)
        self.anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def enrich_person_proxycurl(self, linkedin_url: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nubela.co/proxycurl/api/v2/linkedin",
                params={"url": linkedin_url},
                headers={"Authorization": f"Bearer {self.proxycurl_key}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        return {
            "full_name": data.get("full_name", ""),
            "headline": data.get("headline", ""),
            "summary": data.get("summary", ""),
            "experiences": data.get("experiences", []),
            "education": data.get("education", []),
            "raw": data,
        }

    async def enrich_company_tavily(self, company_name: str, website: str | None = None) -> dict:
        query = f"{company_name} startup funding news"
        results = self.tavily.search(query, max_results=5, days=90)

        context = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
            for r in results.get("results", [])
        )

        message = await self.anthropic.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    f"Based on these search results about {company_name}, extract:\n"
                    f"1. A one-sentence company summary\n"
                    f"2. Funding info if mentioned\n"
                    f"3. Up to 3 recent news items as JSON: [{{title, url, date}}]\n\n"
                    f"Results:\n{context}\n\n"
                    f"Reply as JSON: {{summary, funding_info, news}}"
                ),
            }],
        )

        import json
        try:
            extracted = json.loads(message.content[0].text)
        except (json.JSONDecodeError, IndexError, KeyError):
            extracted = {"summary": "", "funding_info": "", "news": []}

        return extracted

    async def generate_intel_brief(self, person_id: str, db_session) -> str:
        from sqlalchemy import select

        from app.models.interaction import Interaction
        from app.models.person import Person

        result = await db_session.execute(select(Person).where(Person.id == person_id))
        person = result.scalar_one_or_none()
        if not person:
            return "Person not found."

        interactions_result = await db_session.execute(
            select(Interaction)
            .where(Interaction.person_id == person_id)
            .order_by(Interaction.occurred_at.desc())
            .limit(3)
        )
        interactions = list(interactions_result.scalars().all())

        context_parts = [
            f"Name: {person.full_name}",
            f"Role: {person.role or 'Unknown'}",
            f"Bio: {person.bio_snapshot or person.linkedin_summary or 'No enrichment data yet'}",
            f"How we met: {person.how_met or 'Unknown'}",
            f"Interest level: {person.interest_level}",
        ]
        if interactions:
            context_parts.append("Recent interactions:")
            for i in interactions:
                context_parts.append(f"  - {i.processed_summary or i.raw_note or '(no notes)'}")

        context = "\n".join(context_parts)

        message = await self.anthropic.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    f"Generate a 5-bullet pre-meeting brief for this contact. "
                    f"Be concise and actionable. Focus on: who they are, what they do, "
                    f"what we discussed, what they care about, and one tailored opener.\n\n"
                    f"{context}"
                ),
            }],
        )

        return message.content[0].text


enrichment_service = EnrichmentService()
