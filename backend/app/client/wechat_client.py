"""
WeChat API Client

A comprehensive client for making HTTP requests to WeChat API endpoints.
Handles authentication, error handling, and retry logic.
"""

import asyncio
from typing import Optional, Dict, Any, Union
import httpx
from ..logger.logger import log_info, log_error
from ..auth.wechat_token_manager import get_token_manager


class WeChatAPIClient:
    """
    WeChat API HTTP client with automatic token management and error handling.
    """
    
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"
    
    def __init__(self, timeout: float = 30.0, max_retries: int = 2):
        """
        Initialize the WeChat API client.
        
        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retries for token-related errors
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._token_manager = None
    
    async def _get_token_manager(self):
        """Get the token manager instance (lazy initialization)"""
        if self._token_manager is None:
            self._token_manager = await get_token_manager()
        return self._token_manager
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request to WeChat API with automatic token handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: JSON data for POST requests
            params: Query parameters
            require_token: Whether this endpoint requires an access token
            
        Returns:
            Response JSON or None if failed
        """
        token_manager = await self._get_token_manager()
        
        # Try up to max_retries times in case of token expiry
        for attempt in range(self.max_retries):
            # Get access token if required
            access_token = None
            if require_token:
                access_token = await token_manager.get_access_token()
                if not access_token:
                    log_error(f"Cannot make {method} request to {endpoint}: no access token")
                    return None
            
            # Build URL
            url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
            
            # Add token to query params if required
            request_params = params or {}
            if require_token and access_token:
                request_params["access_token"] = access_token
            
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, params=request_params)
                    elif method.upper() == "POST":
                        response = await client.post(url, params=request_params, json=data)
                    elif method.upper() == "PUT":
                        response = await client.put(url, params=request_params, json=data)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, params=request_params)
                    else:
                        log_error(f"Unsupported HTTP method: {method}")
                        return None
                    
                    response.raise_for_status()
                    result = response.json()
                    
                    # Check WeChat API response
                    if result.get("errcode") == 0 or "errcode" not in result:
                        log_info(f"Successfully made {method} request to {endpoint}")
                        return result
                    elif require_token and result.get("errcode") in [40001, 40014, 42001]:
                        # Token expired or invalid - invalidate and retry
                        log_error(f"WeChat API token error: {result}")
                        token_manager.invalidate_token()
                        if attempt < self.max_retries - 1:
                            log_info("Retrying with refreshed token...")
                            continue
                        else:
                            log_error(f"Failed to make {method} request after token refresh")
                            return None
                    else:
                        log_error(f"WeChat API error: {result}")
                        return None
                        
            except httpx.TimeoutException:
                log_error(f"Timeout while making {method} request to {endpoint}")
                return None
            except httpx.HTTPStatusError as e:
                log_error(f"HTTP error while making {method} request to {endpoint}: {e}")
                return None
            except Exception as e:
                log_error(f"Unexpected error while making {method} request to {endpoint}: {e}")
                return None
        
        return None
    
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to WeChat API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            require_token: Whether this endpoint requires an access token
            
        Returns:
            Response JSON or None if failed
        """
        return await self._make_request("GET", endpoint, params=params, require_token=require_token)
    
    async def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to WeChat API.
        
        Args:
            endpoint: API endpoint
            data: JSON data to send
            params: Query parameters
            require_token: Whether this endpoint requires an access token
            
        Returns:
            Response JSON or None if failed
        """
        return await self._make_request("POST", endpoint, data=data, params=params, require_token=require_token)
    
    async def put(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make a PUT request to WeChat API.
        
        Args:
            endpoint: API endpoint
            data: JSON data to send
            params: Query parameters
            require_token: Whether this endpoint requires an access token
            
        Returns:
            Response JSON or None if failed
        """
        return await self._make_request("PUT", endpoint, data=data, params=params, require_token=require_token)
    
    async def delete(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        require_token: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make a DELETE request to WeChat API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            require_token: Whether this endpoint requires an access token
            
        Returns:
            Response JSON or None if failed
        """
        return await self._make_request("DELETE", endpoint, params=params, require_token=require_token)
    
    # Convenience methods for specific WeChat API endpoints
    
    async def send_custom_message(self, openid: str, message_data: Dict[str, Any]) -> bool:
        """
        Send a custom message to a user.
        
        Args:
            openid: User's OpenID
            message_data: Message data according to WeChat API format
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.post("message/custom/send", data=message_data)
        return result is not None
    
    async def send_text_message(self, openid: str, content: str) -> bool:
        """
        Send a text message to a user.
        
        Args:
            openid: User's OpenID
            content: Text content to send
            
        Returns:
            True if successful, False otherwise
        """
        message_data = {
            "touser": openid,
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        return await self.send_custom_message(openid, message_data)
    
    async def get_user_info(self, openid: str, lang: str = "zh_CN") -> Optional[Dict[str, Any]]:
        """
        Get user information.
        
        Args:
            openid: User's OpenID
            lang: Language code
            
        Returns:
            User info or None if failed
        """
        return await self.get("user/info", params={"openid": openid, "lang": lang})
    
    async def get_access_token_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current access token.
        
        Returns:
            Token info or None if failed
        """
        token_manager = await self._get_token_manager()
        token = await token_manager.get_access_token()
        if not token:
            return None
        
        return await self.get("getcallbackip", require_token=True)


# Global singleton instance and lock
_wechat_client: Optional[WeChatAPIClient] = None
_client_lock: Optional[asyncio.Lock] = None

def _get_client_lock() -> asyncio.Lock:
    """Get or create the client lock (lazy initialization)"""
    global _client_lock
    if _client_lock is None:
        _client_lock = asyncio.Lock()
    return _client_lock

async def get_wechat_client() -> WeChatAPIClient:
    """
    Get the global WeChat API client instance.
    Creates it if it doesn't exist (singleton pattern).
    Async-safe to prevent multiple instances being created.
    """
    global _wechat_client
    
    # Fast path: if already created, return immediately
    if _wechat_client is not None:
        return _wechat_client
    
    # Slow path: need to create instance with lock protection
    client_lock = _get_client_lock()
    async with client_lock:
        # Double-check pattern: another coroutine might have created it
        if _wechat_client is None:
            _wechat_client = WeChatAPIClient()
        return _wechat_client
