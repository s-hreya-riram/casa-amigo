from services.base import BaseService
from services.schema import TenancyAgreementsInsert
from uuid import UUID
from typing import Dict

class TenancyService(BaseService):
    """Tenancy agreement management"""
    
    def create_agreement(self, agreement: TenancyAgreementsInsert) -> Dict:
        """Create tenancy agreement"""
        data = agreement.model_dump()
        data.pop("agreement_id", None)  # Let DB generate UUID
        data.pop("created_at", None)  # Let DB generate created_at
        data.pop("updated_at", None)  # Let DB generate updated_at
        data = self._execute_query(
            lambda: self.client.table("tenancy_agreements").insert(data),
            "Create agreement"
        )
        return data[0] if data else {}
    
    def get_agreement(self, agreement_id: UUID) -> Dict:
        """Get tenancy agreement. Raises NotFoundError if not found."""
        return self._get_single(
            lambda: self.client.table("tenancy_agreements")
            .select("*")
            .eq("id", str(agreement_id)),
        f"Get agreement {agreement_id}"
    )