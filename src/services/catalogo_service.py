from src.core.api_client import ApiClient
from src.services.cache_manager import CacheManager

class CatalogoService:
    def __init__(self):
        self.api = ApiClient()
        self.cache = CacheManager()

    def get_catalogo(self, endpoint, cache_key=None):
        if cache_key:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data
        
        try:
           # If not in cache or no key provided, fetch from API
            data = self.api.get(endpoint)
            
            if cache_key and data:
                self.cache.set(cache_key, data)
                
            return data
        except Exception as e:
            print(f"Error fetching catalog {endpoint}: {e}")
            return []

    def clear_cache(self):
        self.cache.clear()
