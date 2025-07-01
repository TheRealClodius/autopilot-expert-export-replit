"""
DeepSeek Client - Wrapper for DeepSeek API interactions.
Provides interfaces for AI model calls compatible with evaluation framework.
"""

import json
import logging
import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """
    Client wrapper for DeepSeek API interactions.
    Provides evaluation-compatible interface for LLM calls.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"
        
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY environment variable.")
        
        self._session = None
        self._last_request_time = 0
        
    async def _get_session(self):
        """Get or create async HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _rate_limit(self):
        """Simple rate limiting to prevent API overload"""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < 1.0:  # 1 second between requests
            await asyncio.sleep(1.0 - time_since_last)
        self._last_request_time = time.time()
    
    async def generate_response(
        self,
        prompt: str,
        temperature: float = 0.7,
        timeout_seconds: int = 30,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Generate a response using DeepSeek API.
        
        Args:
            prompt: The prompt to send to the model
            temperature: Sampling temperature (0.0 to 1.0)
            timeout_seconds: Request timeout
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text response or None on failure
        """
        try:
            await self._rate_limit()
            
            session = await self._get_session()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        message = data["choices"][0].get("message", {})
                        content = message.get("content", "").strip()
                        
                        if content:
                            logger.debug(f"DeepSeek response generated successfully")
                            return content
                        else:
                            logger.warning("DeepSeek returned empty content")
                            return None
                    else:
                        logger.warning("DeepSeek response missing choices")
                        return None
                        
                else:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API error {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"DeepSeek API timeout after {timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return None
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def test_connection(self) -> bool:
        """Test if the API connection works"""
        try:
            test_response = await self.generate_response(
                prompt="Hello, this is a test. Please respond with 'Connection successful.'",
                temperature=0.0,
                timeout_seconds=10,
                max_tokens=50
            )
            
            if test_response and "successful" in test_response.lower():
                logger.info("DeepSeek API connection test successful")
                return True
            else:
                logger.warning(f"DeepSeek API test response unexpected: {test_response}")
                return False
                
        except Exception as e:
            logger.error(f"DeepSeek API connection test failed: {e}")
            return False 