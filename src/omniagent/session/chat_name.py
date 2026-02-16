from omniagent.session.mongo import MongoSessionManager


async def generate_chat_name(
    *,
    query: str,
    turns_between_chat_name: int = 20,
    max_chat_name_length: int = 50,
    max_chat_name_words: int = 5,
    session_id: str | None = None,
    user_id: str | None = None,
    provider_name: str | None = None,
) -> str:
    return await MongoSessionManager.generate_chat_name(
        query=query,
        turns_between_chat_name=turns_between_chat_name,
        max_chat_name_length=max_chat_name_length,
        max_chat_name_words=max_chat_name_words,
        session_id=session_id,
        user_id=user_id,
        provider_name=provider_name,
    )
