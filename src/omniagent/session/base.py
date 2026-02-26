"""
Base SessionManager abstract class for OmniAgent.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Tuple

import logging

from omniagent.types.state import State
from omniagent.types.message import MessageDTO
from omniagent.domain_protocols import UserProtocol, SessionProtocol, MessageProtocol, SummaryProtocol
from omniagent.config import MAX_TOKEN_THRESHOLD
from omniagent.utils.general import generate_id
from omniagent.config import AISDK_ID_LENGTH
from omniagent.tracing import track_state_change
from omniagent.ai.providers.utils import StreamCallback

logger = logging.getLogger(__name__)


class SessionManager(ABC):
    """
    Abstract base class for session management.
    
    Provides common logic for state management and context orchestration.
    Subclasses must implement database-specific methods for fetching and persisting data.
    """

    def __init__(
        self, 
        session_id: str | None, 
        user_client_id: str,
        state: dict = {}, 
    ):
        self.state = self._inititialise_state(state=state)
        self.session_id = session_id
        self.user_client_id = user_client_id
        self.user: UserProtocol | None = None
        self.session: SessionProtocol | None = None
        self.new_chat: bool = False
        self.new_user: bool = False

    def _inititialise_state(self, state: dict) -> State:
        return State(user_defined_state=state)

    @classmethod
    @abstractmethod
    async def generate_chat_name(
        cls,
        *,
        query: str,
        turns_between_chat_name: int = 20,
        max_chat_name_length: int = 50,
        max_chat_name_words: int = 5,
        session_id: str | None = None,
        client_id: str | None = None,
    ) -> str:
        """
        Generate a chat name using backend-specific context retrieval and provider calls.

        Must be implemented by backend-specific session managers.
        """
        ...

    @abstractmethod
    async def _fetch_user_or_session(self) -> None:
        """
        Fetch user and session in parallel based on client_id and session_id.
        
        Sets instance variables:
        - self.new_user = True if user not found
        - self.new_chat = True if session not found (or new user)
        - self.user and self.session populated if found or created
        
        If user not found: creates user + session atomically.
        If user found but session not found: creates session for existing user.
        
        Must be implemented by subclasses for specific database backends.
        """
        ...

    @abstractmethod
    async def _fetch_context(self) -> Tuple[List[MessageProtocol], SummaryProtocol | None]:
        """
        Fetch the latest N turns (as messages) and the latest summary in parallel.
        
        Returns:
            Tuple of (messages, summary) where messages is a list of Message objects
            from the latest turns and summary is the latest Summary or None.
        
        Must be implemented by subclasses for specific database backends.
        """
        ...

    @abstractmethod
    async def update_user_session(
        self, 
        messages: List[MessageDTO], 
        summary: SummaryProtocol | None, 
        regenerated_summary: bool,
        on_stream_event: StreamCallback | None = None,
    ) -> List[MessageDTO]:
        """
        Create/update user and session, then insert messages.
        
        Must be implemented by subclasses for specific database backends.
        """
        ...

    @abstractmethod
    def _convert_messages_to_dtos(self, messages: List[MessageProtocol]) -> List[MessageDTO]:
        """
        Convert database message objects to MessageDTOs.
        
        Must be implemented by subclasses for specific database backends.
        """
        ...

    def update_state(self, **kwargs) -> None:
        """
        Update state with provided key-value pairs.
        
        Automatically tracks state changes in the current span for observability.
        
        Args:
            **kwargs: Key-value pairs to update in state.
        """
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                old_value = getattr(self.state, key)
                setattr(self.state, key, value)
                
                # Track state change in current span
                track_state_change(key, old_value, value)

    async def get_context_and_update_state(self) -> Tuple[List[MessageDTO], SummaryProtocol | None]:
        """
        Fetch context (messages + summary) and user/session in parallel, then update state.
        
        Algorithm:
        1. Fetch messages from latest turns and calculate tokens after summary
        2. If tokens < MAX_TOKEN_THRESHOLD, include additional older messages until threshold met
        3. Update state with turns_after_last_summary, total_token_after_last_summary, active_summary
        4. Return messages in chronological order with summary
        
        Returns:
            Tuple of (messages, summary) - messages from selected turns in order of arrival.
        """
        # Fetch context and user/session in parallel
        context_task = self._fetch_context()
        user_or_session_task = self._fetch_user_or_session()
        (all_messages, summary), _ = await asyncio.gather(context_task, user_or_session_task)
        if self.session:
            self.update_state(turn_number=self.session.latest_turn_number+1)
        
        if not all_messages:
            return [], summary
        
        # Messages are already in chronological order from get_latest_by_session
        
        # Determine the start point based on summary
        end_turn_number = summary.end_turn_number if summary else 0
        
        # Step 1: Get messages after summary (end_turn_number + 1 to current)
        messages_after_summary = [m for m in all_messages if m.turn_number > end_turn_number]
        
        # Count unique turns after summary
        turns_after_summary = {m.turn_number for m in messages_after_summary}
        turns_after_last_summary = len(turns_after_summary)
        total_token_after_last_summary = sum(m.token_count for m in messages_after_summary)
        
        # Step 2: Collect context messages - start with messages after summary
        context_messages = messages_after_summary.copy()
        
        # Step 3 & 4: If tokens < threshold, fetch additional older messages
        if total_token_after_last_summary < MAX_TOKEN_THRESHOLD:
            # Get messages at or before end_turn_number (older messages)
            older_messages = [m for m in all_messages if m.turn_number <= end_turn_number]
            # Reverse to process from most recent to oldest
            older_messages.reverse()
            
            for message in older_messages:
                total_token_after_last_summary += message.token_count
                context_messages.insert(0, message)  # Insert at beginning to maintain order
                if total_token_after_last_summary >= MAX_TOKEN_THRESHOLD:
                    break
        
        # Update state
        self.update_state(
            turns_after_last_summary=turns_after_last_summary,
            total_token_after_last_summary=total_token_after_last_summary,
            active_summary=summary
        )
        
        # Convert Message documents to MessageDTOs (implemented by subclass)
        message_dtos = self._convert_messages_to_dtos(context_messages)
        
        return message_dtos, summary
    
    def create_fallback_messages(self, user_query_dto: MessageDTO) -> List[MessageDTO]:
        """
        Create fallback messages with user query and error response.
        
        Args:
            user_query_dto: The original user query message
            
        Returns:
            List containing user query and error response message
        """
        # Create error response DTO using new schema
        error_message_dto = MessageDTO.create_ai_message(
            message_id=generate_id(AISDK_ID_LENGTH, "nanoid"),
            metadata={"error": True}
        ).update_ai_text_message(
            text="I apologize, but something went wrong while processing your request. Please try again."
        )
        
        # Return list with user message and error response
        return [user_query_dto, error_message_dto]
