import httpx
from typing import Optional

class HttpClientManager:
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0),
                headers={
                    "User-Agent": "Crypto-Sniper-V11/1.0",
                    "Accept": "application/json"
                }
            )
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None

http_manager = HttpClientManager()
