from ..services.base import BaseService
from ..services.schema import PropertyPreferencesInsert, PropertyPreferencesUpdate
from uuid import UUID
from typing import Optional, Dict, List

class PropertyService(BaseService):
    """Property and preference operations"""
    
    def get_preferences(self, user_id: UUID) -> Optional[Dict]:
        """Get user's property preferences"""
        data = self._execute(
            self.client.table("property_preferences")
            .select("*")
            .eq("user_id", str(user_id))
        )
        return data[0] if data else None
    
    def create_preferences(self, preferences: PropertyPreferencesInsert) -> Dict:
        """Create property preferences"""
        data = self._execute(
            self.client.table("property_preferences")
            .insert(preferences.model_dump())
        )
        return data[0] if data else None
    
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
        return self._execute(
            self.client.table("properties")
            .select("*")
            .range(offset, offset + limit - 1)
        ) or []
    
    def search_by_preferences(self, user_id: UUID) -> List[Dict]:
        """Search properties matching user preferences"""
        prefs = self.get_preferences(user_id)
        if not prefs:
            raise ValueError("User preferences not found")
        
        query = self.client.table("properties").select("*")
        
        if prefs.get("min_budget"):
            query = query.gte("rent", prefs["min_budget"])
        if prefs.get("max_budget"):
            query = query.lte("rent", prefs["max_budget"])
        if prefs.get("min_bedrooms"):
            query = query.gte("num_bedrooms", prefs["min_bedrooms"])
        if prefs.get("max_bedrooms"):
            query = query.lte("num_bedrooms", prefs["max_bedrooms"])
        if prefs.get("property_type"):
            query = query.in_("property_type", prefs["property_type"])
        
        return self._execute(query) or []
