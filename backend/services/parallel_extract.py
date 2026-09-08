import os
import time
import json
import hashlib
import logging
import httpx
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger("lienmark.parallel_extract")

class ExtractResult(BaseModel):
    url: str
    full_content: str = ""
    excerpts: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    payload_hash: str = ""
    http_status: int = 200
    fail_closed: bool = False
    error: Optional[str] = None

class ParallelExtractService:
    """Client for Parallel Extract API."""
    
    API_URL = os.getenv("PARALLEL_EXTRACT_URL", "https://api.parallel.ai/v1/extract")
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_fallback: bool = False,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.use_fallback = use_fallback
        self.timeout = timeout

    def _validate_url(self, url: str) -> bool:
        """Validates if URL is well-formed."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    def _compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def extract(
        self,
        urls: List[str],
        objective: Optional[str] = None
    ) -> List[ExtractResult]:
        """Extracts text from given URLs using Parallel API."""
        valid_urls = [u for u in urls if self._validate_url(u)][:20]
        if not valid_urls:
            return []

        payload = {"urls": valid_urls}
        if objective:
            payload["objective"] = objective
            
        payload_hash = self._compute_payload_hash(payload)
        
        if self.use_fallback:
            return self._mock_extraction(valid_urls, payload_hash)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.API_URL, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                if resp.status_code == 429 or resp.status_code >= 500:
                    return [self._fail_closed(u, payload_hash, latency_ms, resp.status_code, "HTTP Error") for u in valid_urls]
                    
                resp.raise_for_status()
                data = resp.json()
                
                results = []
                for result_data in data.get("results", []):
                    url = result_data.get("url")
                    if url not in valid_urls:
                        continue
                    results.append(ExtractResult(
                        url=url,
                        full_content=result_data.get("full_content", ""),
                        excerpts=result_data.get("excerpts", []),
                        latency_ms=latency_ms,
                        payload_hash=payload_hash,
                        http_status=resp.status_code
                    ))
                return results
                
        except (httpx.TimeoutException, httpx.RequestError) as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return [self._fail_closed(u, payload_hash, latency_ms, 504, str(e)) for u in valid_urls]
            
    def _fail_closed(self, url: str, hash_val: str, latency: float, status: int, err: str) -> ExtractResult:
        return ExtractResult(
            url=url,
            latency_ms=latency,
            payload_hash=hash_val,
            http_status=status,
            fail_closed=True,
            error=err
        )
        
    def _mock_extraction(self, urls: List[str], hash_val: str) -> List[ExtractResult]:
        return [
            ExtractResult(
                url=u,
                full_content=f"Mocked content for {u}",
                excerpts=["Mocked excerpt"],
                latency_ms=100.0,
                payload_hash=hash_val,
                http_status=200
            ) for u in urls
        ]
