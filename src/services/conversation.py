from services.base import BaseService
from services.schema import MessagesInsert, ConversationsInsert
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
        msg_data.pop("message_id", None)  # Let DB generate UUID
        msg_data.pop("created_at", None)  # Let DB generate created_at
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
    
    # NOTE: This is for testing purposes only
    def create_conversation(self, conversation: ConversationsInsert) -> Dict:
        """Create a new conversation"""
        conv_data = conversation.model_dump()
        conv_data.pop("conversation_id", None)  # Let DB generate UUID
        conv_data.pop("created_at", None)  # Let DB generate created_at
        conv_data.pop("updated_at", None)  # Let DB generate updated_at

        data = self._execute_query(
            lambda: self.client.table("conversations").insert(conv_data),
            "Create conversation"
        )
        return data[0] if data else {}