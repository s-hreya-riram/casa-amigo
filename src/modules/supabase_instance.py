from core.config.supabase_client import SupabaseClient, SupabaseCredentialsError, SupabaseConnectionError

class SingletonSupabaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = SupabaseClient().client
            except SupabaseCredentialsError as e:
                raise RuntimeError(f"Supabase credentials missing: {e}")
            except SupabaseConnectionError as e:
                raise RuntimeError(f"Unable to connect to Supabase: {e}")
        return cls._instance

# Initialize once at module load
supabase_client = SingletonSupabaseClient()