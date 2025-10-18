from services.base import BaseService
from services.schema import TenantProfilesInsert, TenantProfilesUpdate
from core.exceptions import NotFoundError
from uuid import UUID
from typing import Dict

class TenantProfileService(BaseService):
    """Tenant profile management"""
    
    def get_profile(self, user_id: UUID) -> Dict:
        """Get user's tenant profile. Raises NotFoundError if not found."""
        return self._get_single(
            lambda: self.client.table("tenant_profiles")
                .select("*")
                .eq("user_id", str(user_id)),
            error_context=f"Get profile for user {user_id}"
        )
    
    def create_profile(self, profile: TenantProfilesInsert) -> Dict:
        """Create tenant profile"""
        data = self._execute_query(
            lambda: self.client.table("tenant_profiles").insert(profile.model_dump()),
            "Create tenant profile"
        )
        return data[0] if data else {}

    # TODO: Implement update methods for tenant profile