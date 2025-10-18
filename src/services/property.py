from services.base import BaseService
from services.schema import PropertyPreferencesInsert, PropertyPreferencesUpdate
from uuid import UUID
from typing import Optional, Dict, List

class PropertyService(BaseService):
    """Property and preference operations"""

    def get_preferences(self, user_id: UUID) -> Dict:
        """Get user's property preferences"""
        try:
            response = self.client.table("property_preferences").select("*").eq("user_id", str(user_id)).execute()
            if not response.data:
                raise NotFoundError(f"Preferences not found for user {user_id}")
            return response.data[0]
        except Exception as e:
            from core.exceptions import OperationError, NotFoundError
        raise OperationError(f"Get preferences failed: {str(e)}")


    def create_preferences(self, preferences: PropertyPreferencesInsert) -> Dict:
        """Create property preferences"""
        preferences_data = preferences.model_dump()
        preferences_data.pop("preference_id", None)
        preferences_data.pop("created_at", None)
        preferences_data.pop("updated_at", None)

        data = self._execute_query(
            lambda: self.client.table("property_preferences").insert(preferences_data),
            "Create preferences"
        )
        return data[0] if data else {}

    def update_preferences(self, preference_id: UUID, preferences: PropertyPreferencesUpdate) -> Dict:
        """Update preferences"""
        data = self._execute(
            self.client.table("property_preferences")
            .update(preferences.model_dump(exclude_unset=True))
            .eq("preference_id", str(preference_id))
        )
        return data[0] if data else None

    def get_properties(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Get properties with pagination"""
        try:
            response = self.client.table("properties").select("*").range(offset, offset + limit - 1).execute()
            return response.data or []
        except Exception as e:
            from core.exceptions import OperationError
            raise OperationError(f"Get properties failed: {str(e)}")

    # TODO: Enhance search to consider location proximity using max_distance_from_mrt_in_km
    # and to allow searching by image embeddings
    def search_by_preferences(self, user_id: UUID) -> List[Dict]:
        """Search properties matching user preferences"""
        try:
            # Just get all properties without filters
            query = self.client.table("properties").select("*")
            response = query.execute()
            return response.data or []
        except Exception as e:
            from core.exceptions import OperationError
            raise OperationError(f"Search properties failed: {str(e)}")
    
    # NOTE: This is just for testing purposes, unless we have an interface
    # for property agents to add properties.
    def create_property(self, property_data: dict) -> Dict:
        """Create a new property"""
        property_data.pop("property_id", None)

        data = self._execute_query(
            lambda: self.client.table("properties").insert(property_data),
            "Create property"
        )
        return data[0] if data else {}
