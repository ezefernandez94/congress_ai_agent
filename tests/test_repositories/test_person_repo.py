from app.repositories.person_repo import PersonRepository


async def test_uc001_contact_saved_and_found(db_session):
    repo = PersonRepository(db_session)

    saved = await repo.create({"full_name": "Ada Lovelace", "role": "CTO"})
    found = await repo.search_by_name("lovelace")

    assert [p.id for p in found] == [saved.id]
    assert found[0].role == "CTO"
