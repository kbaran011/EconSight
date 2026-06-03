from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from econsight.config import get_logger, settings

logger = get_logger(__name__)


class BaseApiClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=settings.http_timeout,
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(settings.http_max_retries),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        reraise=True,
    )
    async def _get(self, path: str, **params: str) -> Any:
        logger.debug("http.get", path=path, params=params)
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(settings.http_max_retries),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        reraise=True,
    )
    async def _post(self, path: str, body: Any) -> Any:
        logger.debug("http.post", path=path)
        response = await self._client.post(path, json=body)
        response.raise_for_status()
        return response.json()

    async def __aenter__(self) -> "BaseApiClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()
