from ..services.base import BaseService
from ..services.schema import MessagesInsert
from uuid import UUID
from typing import List, Dict

class ConversationService(BaseService):
    """Conversation and message management"""
    
    def list_conversations(self, user_id: UUID) -> List[Dict]:
        """List all conversations for user"""
        return self._get_multiple(
            lambda: self.client.table("conversations")
                .select("*")
                .eq("user_id", str(user_id)),
            f"List conversations for user {user_id}"
        )
    
    def add_message(self, conversation_id: UUID, message: MessagesInsert) -> Dict:
        """Add message to conversation"""
        msg_data = message.model_dump()
        msg_data["conversation_id"] = str(conversation_id)
        data = self._execute_query(
            lambda: self.client.table("messages").insert(msg_data),
            f"Add message to conversation {conversation_id}"
        )
        return data[0] if data else {}
    
    def get_messages(self, conversation_id: UUID, limit: int = 50) -> List[Dict]:
        """Get messages from conversation"""
        return self._get_multiple(
            lambda: self.client.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("created_at", desc=False)
                .limit(limit),
            f"Get messages from conversation {conversation_id}"
        )