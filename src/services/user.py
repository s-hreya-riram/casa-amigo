from .base import BaseService
from .schema import UsersInsert, UsersUpdate
from ..core.exceptions import NotFoundError, ValidationError
from uuid import UUID
from typing import Dict, Optional

class UserService(BaseService):
    """User management"""
    
    def get_user(self, user_id: UUID) -> Dict:
        """Get user by ID. Raises NotFoundError if not found."""
        return self._get_single(
            lambda: self.client.table("users")
                .select("*")
                .eq("user_id", str(user_id)),
            error_context=f"Get user {user_id}"
        )
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email. Returns None if not found."""
        try:
            return self._get_single(
                lambda: self.client.table("users")
                    .select("*")
                    .eq("email_id", email),
                error_context=f"Get user by email {email}"
            )
        except NotFoundError:
            return None
    
    def create_user(self, user: UsersInsert) -> Dict:
        """Create new user. Raises ValidationError if email exists."""
        if self.get_user_by_email(user.email_id):
            raise ValidationError(f"User with email {user.email_id} already exists")
        
        data = self._execute_query(
            lambda: self.client.table("users").insert(user.model_dump()),
            "Create user"
        )
        return data[0] if data else {}
    
    # TODO: Implement update methods for updating user name, email etc.