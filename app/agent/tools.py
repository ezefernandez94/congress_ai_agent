TOOLS = [
    # --- CONTACT TOOLS ---
    {
        "name": "create_contact",
        "description": "Create a new contact record. Call this when the user mentions meeting someone new.",
        "input_schema": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "role": {"type": "string"},
                "company_name": {"type": "string"},
                "contact_type": {
                    "type": "string",
                    "enum": ["investor", "customer", "partner", "founder", "speaker", "other"],
                },
                "interest_level": {
                    "type": "string",
                    "enum": ["hot", "warm", "cold", "unknown"],
                },
                "how_met": {"type": "string"},
                "notes": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "email": {"type": "string"},
            },
            "required": ["full_name"],
        },
    },
    {
        "name": "log_interaction",
        "description": "Log an interaction with an existing contact. Use after a meeting or conversation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "interaction_type": {"type": "string"},
                "summary": {"type": "string"},
                "sentiment": {
                    "type": "string",
                    "enum": ["very_positive", "positive", "neutral", "negative"],
                },
                "topics_discussed": {"type": "array", "items": {"type": "string"}},
                "commitments_made": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "who": {"type": "string", "enum": ["me", "them"]},
                            "what": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["person_name", "summary"],
        },
    },
    {
        "name": "create_task",
        "description": "Create an action item or follow-up task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "task_type": {
                    "type": "string",
                    "enum": [
                        "send_email",
                        "send_deck",
                        "schedule_meeting",
                        "linkedin_connect",
                        "research",
                        "follow_up",
                        "other",
                    ],
                },
                "person_name": {"type": "string"},
                "priority": {
                    "type": "string",
                    "enum": ["urgent", "high", "medium", "low"],
                },
                "due_date": {
                    "type": "string",
                    "description": "ISO date string YYYY-MM-DD",
                },
                "draft_content": {
                    "type": "string",
                    "description": "Pre-written draft if applicable",
                },
            },
            "required": ["title", "task_type"],
        },
    },
    {
        "name": "search_contacts",
        "description": (
            "Search for contacts by name, company, or description. "
            "Use when user refers to someone by partial name or context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "contact_type": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_contact_brief",
        "description": "Get full context on a contact: bio, enrichment data, interaction history, open tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "get_pending_tasks",
        "description": "Get all pending tasks, optionally filtered by priority or person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string"},
                "person_name": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "task_title": {
                    "type": "string",
                    "description": "Can be used instead of task_id for fuzzy match",
                },
            },
        },
    },

    # --- ENRICHMENT TOOLS ---
    {
        "name": "enrich_contact",
        "description": (
            "Fetch LinkedIn and company data for a contact. "
            "Call when user provides a LinkedIn URL or asks for background on someone."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "linkedin_url": {"type": "string"},
                "company_name": {"type": "string"},
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "search_web",
        "description": "Search the web for news or information about a person or company.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "days_back": {"type": "integer", "default": 90},
            },
            "required": ["query"],
        },
    },

    # --- DRAFT TOOLS ---
    {
        "name": "draft_followup",
        "description": "Generate a personalized follow-up email draft for a contact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "tone": {
                    "type": "string",
                    "enum": ["warm", "professional", "casual"],
                    "default": "warm",
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific things to mention",
                },
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "generate_meeting_prep",
        "description": (
            "Generate a pre-meeting brief with talking points and questions for an upcoming meeting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {"type": "string"},
                "meeting_context": {
                    "type": "string",
                    "description": "Type of meeting: pitch, intro, coffee, etc.",
                },
            },
            "required": ["person_name"],
        },
    },

    # --- DIGEST / SUMMARY TOOLS ---
    {
        "name": "get_daily_digest",
        "description": (
            "Generate the full daily digest: pending tasks, today's meetings, "
            "priority contacts to approach."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_conference_summary",
        "description": (
            "Generate a summary of all contacts, opportunities, and follow-ups from the conference."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]
