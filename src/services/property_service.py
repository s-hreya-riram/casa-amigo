from services.base import BaseService
from services.schema import PropertyPreferencesInsert, PropertyPreferencesUpdate
from uuid import UUID
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

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
        
    def bulk_insert_properties(self, properties: List[Dict]) -> Dict:

        """Bulk insert scraped properties into database"""
        inserted = 0
        errors = []
        
        for prop in properties:
            try:
                # Remove fields that shouldn't be in database or are auto-generated
                prop_data = {
                    'address': prop.get('address'),
                    'rent': prop.get('price'),
                    'rent_psf': prop.get('price_psf'),
                    'num_bedrooms': prop.get('bedrooms'),
                    'num_bathrooms': prop.get('bathrooms'),
                    'sqft': prop.get('area_sqft'),
                    'property_type': prop.get('unit_type'),
                    'listing_status': prop.get('availability'),
                    'mrt_info': prop.get('mrt_info'),
                    'listing_id': prop.get('listing_id'),
                    # Add any other fields that match your database schema
                }
                
                # Remove None values
                prop_data = {k: v for k, v in prop_data.items() if v is not None}
                
                # Insert into database
                self.client.table("properties").insert(prop_data).execute()
                inserted += 1
                
            except Exception as e:
                from core.exceptions import OperationError
                error_msg = f"Failed to insert property {prop.get('listing_id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
        
        return {
            'success': True,
            'inserted': inserted,
            'total': len(properties),
            'errors': errors
        }
    
    def check_duplicate_listing(self, listing_id: str) -> bool:
        """Check if a listing already exists in database"""
        try:
            response = self.client.table("properties").select("property_id").eq("listing_id", listing_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Duplicate check failed: {str(e)}")
            return False
    
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
