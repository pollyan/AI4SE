
class APIClient:
    """带有 JSON Content-Type 的 API 客户端包装器"""
    
    def __init__(self, client, prefix=""):
        self.client = client
        self.prefix = prefix
        
    def _get_path(self, path):
        # Prepend prefix if not present and matches API or health routes
        if path.startswith('/api') or path.startswith('/health'):
            # Simple check to avoid double prefixing if path already has it
            if self.prefix and not path.startswith(self.prefix):
                return f"{self.prefix}{path}"
        return path
        
    def get(self, path, *args, **kwargs):
        return self.client.get(self._get_path(path), *args, **kwargs)
        
    def post(self, path, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['content_type'] = 'application/json'
        return self.client.post(self._get_path(path), *args, **kwargs)
        
    def put(self, path, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['content_type'] = 'application/json'
        return self.client.put(self._get_path(path), *args, **kwargs)
        
    def delete(self, path, *args, **kwargs):
        return self.client.delete(self._get_path(path), *args, **kwargs)
