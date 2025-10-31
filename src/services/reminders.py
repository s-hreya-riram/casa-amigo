"""
Reminder Service with notification support
Email notifications are sent via Eventbridge and SES (through Lambda), 
Lambda updates the status of reminders and updates records in reminder_notifications.
"""

from services.base import BaseService
from services.schema import RemindersInsert, RemindersUpdate
from core.exceptions import NotFoundError
from uuid import UUID
from datetime import datetime
from typing import List, Dict

class ReminderService(BaseService):
    """Reminder management"""

    def list_reminders(self, user_id: UUID, include_sent: bool = False) -> List[Dict]:
        """List all reminders for user"""
        all_reminders = self._get_multiple(
            lambda: self.client.table("reminders")
                .select("*")
                .eq("user_id", str(user_id)),
            f"List reminders for user {user_id}"
        )
        if not include_sent:
            all_reminders = [r for r in all_reminders if r.get("status") != "sent"]
        return all_reminders
    
    def create_reminder(self, reminder: RemindersInsert) -> Dict:
        """Create new reminder"""
        reminder_data = reminder.model_dump()
        reminder_data.pop("reminder_id", None)  # Let DB generate UUID
        reminder_data.pop("created_at", None)  # Let DB generate created_at
        reminder_data.pop("updated_at", None)  # Let DB generate updated_at
        data = self._execute_query(
            lambda: self.client.table("reminders").insert(reminder_data),
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