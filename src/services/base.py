from core.exceptions import OperationError, NotFoundError
from modules.supabase_instance import supabase_client
from typing import List, Dict, Any, Optional
        
class BaseService:
    """Base service with error handling"""
    
    def __init__(self):
        self.client = supabase_client

    def _execute_query(self, query_fn, error_context: str = "Database operation"):
        """Execute query with consistent error handling"""
        try:
            query = query_fn()
            response = query.execute()  # Execute the query
            return response.data
        except Exception as e:
            raise OperationError(f"{error_context} failed: {str(e)}")
    
    def _get_single(self, query_fn, error_context: str = "Query") -> Optional[Dict]:
        """Execute query expecting single result"""
        data = self._execute_query(query_fn, error_context)
        if not data:
            raise NotFoundError(f"{error_context} - Resource not found")
        return data[0]
    
    def _get_multiple(self, query_fn, error_context: str = "Query") -> List[Dict]:
        """Execute query expecting multiple results"""
        return self._execute_query(query_fn, error_context) or []