from ..services.base import BaseService
from ..services.schema import RemindersInsert, RemindersUpdate
from ..core.exceptions import NotFoundError
from uuid import UUID
from datetime import datetime
from typing import List, Dict

class ReminderService(BaseService):
    """Reminder management"""
    
    def list_reminders(self, user_id: UUID) -> List[Dict]:
        """List all reminders for user"""
        return self._get_multiple(
            lambda: self.client.table("reminders")
                .select("*")
                .eq("user_id", str(user_id)),
            f"List reminders for user {user_id}"
        )
    
    def create_reminder(self, reminder: RemindersInsert) -> Dict:
        """Create new reminder"""
        data = self._execute_query(
            lambda: self.client.table("reminders").insert(reminder.model_dump()),
            "Create reminder"
        )
        return data[0] if data else {}
    
    # TODO: Evaluate renaming this to scheduling reminders instead
    def send_reminder(self, reminder_id: UUID, user_id: UUID) -> Dict:
        """Trigger reminder sending"""
        # Verify reminder exists
        reminder = self._execute_query(
            lambda: self.client.table("reminders")
                .select("*")
                .eq("reminder_id", str(reminder_id)),
            f"Get reminder {reminder_id}"
        )
        if not reminder:
            raise NotFoundError(f"Reminder {reminder_id} not found")
        
        # TODO: Implement actual sending logic (email, SMS, etc.)
        
        notification_data = {
            "reminder_id": str(reminder_id),
            "user_id": str(user_id),
            "delivery_status": "sent",
            "sent_at": datetime.utcnow().isoformat()
        }
        data = self._execute_query(
            lambda: self.client.table("reminder_notifications").insert(notification_data),
            "Send reminder notification"
        )
        return data[0] if data else {}