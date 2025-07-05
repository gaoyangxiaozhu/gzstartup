"""
WeChat Access Token Manager

Handles WeChat API access token caching, refresh, and concurrency control.
Ensures all API calls always use a valid token without race conditions.
"""

import asyncio
import time
import configparser
import os
from typing import Optional
import httpx
from ..logger.logger import log_info, log_error


def log_warning(message):
    """Temporary wrapper for warning log until log_warning is added to logger module"""
    log_error(f"WARNING: {message}")


class WeChatTokenManager:
    """
    Manages WeChat access token with automatic refresh and caching.
    Thread-safe and prevents race conditions during token refresh.
    """

    def __init__(self):
        """Initialize the token manager."""
        # Load configuration
        config = configparser.ConfigParser()
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
        if not config.read(config_path, encoding='utf-8'):
            raise RuntimeError(f'Config file not found: {config_path}')
        if not config.has_section('wechat'):
            raise RuntimeError(f'[wechat] section not found in {config_path}')

        self._appid = config.get('wechat', 'appid', fallback='')
        self._secret = config.get('wechat', 'secret', fallback='')
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        
        # Concurrency control - initialize lock when needed
        self._refresh_lock: Optional[asyncio.Lock] = None
        self._refresh_in_progress = False
        
        # Buffer time before token expiry (5 minutes)
        self._refresh_buffer_seconds = 300

    def _get_refresh_lock(self) -> asyncio.Lock:
        """Get or create the refresh lock (lazy initialization)"""
        if self._refresh_lock is None:
            self._refresh_lock = asyncio.Lock()
        return self._refresh_lock

    async def get_access_token(self) -> Optional[str]:
        """
        Get a valid access token.
        Returns cached token if valid, otherwise refreshes it.
        Thread-safe - multiple concurrent calls will not cause race conditions.
        """
        current_time = time.time()
        
        # Check if current token is still valid (with buffer)
        if (self._access_token and 
            current_time < (self._token_expires_at - self._refresh_buffer_seconds)):
            log_info("Using cached WeChat access token")
            return self._access_token
        
        # Token needs refresh - use lock to prevent race conditions
        refresh_lock = self._get_refresh_lock()
        async with refresh_lock:
            # Double-check after acquiring lock (another coroutine might have refreshed)
            current_time = time.time()
            if (self._access_token and 
                current_time < (self._token_expires_at - self._refresh_buffer_seconds)):
                log_info("Using cached WeChat access token (double-check)")
                return self._access_token
            
            # Refresh the token
            log_info("Refreshing WeChat access token")
            return await self._refresh_token()

    async def _refresh_token(self) -> Optional[str]:
        """
        Refresh the access token from WeChat API.
        Should only be called while holding the refresh lock.
        """
        if not self._appid or not self._secret:
            log_error("WeChat APPID or SECRET not configured")
            return None
        
        url = (f"https://api.weixin.qq.com/cgi-bin/token?"
               f"grant_type=client_credential&appid={self._appid}&secret={self._secret}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if "access_token" in data and "expires_in" in data:
                    self._access_token = data["access_token"]
                    expires_in = data["expires_in"]  # Usually 7200 seconds (2 hours)
                    self._token_expires_at = time.time() + expires_in
                    
                    log_info(f"WeChat access token refreshed successfully, expires in {expires_in} seconds")
                    return self._access_token
                else:
                    error_code = data.get("errcode", "unknown")
                    error_msg = data.get("errmsg", "unknown error")
                    log_error(f"Failed to get WeChat access token: {error_code} - {error_msg}")
                    return None
                    
        except httpx.TimeoutException:
            log_error("Timeout while refreshing WeChat access token")
            return None
        except httpx.HTTPStatusError as e:
            log_error(f"HTTP error while refreshing WeChat access token: {e}")
            return None
        except Exception as e:
            log_error(f"Unexpected error while refreshing WeChat access token: {e}")
            return None

    def invalidate_token(self):
        """
        Invalidate the current token, forcing a refresh on next access.
        Useful when API calls return token-related errors.
        """
        log_warning("Invalidating WeChat access token")
        self._access_token = None
        self._token_expires_at = 0

    def get_token_info(self) -> dict:
        """
        Get information about the current token state.
        Useful for debugging and monitoring.
        """
        current_time = time.time()
        return {
            "has_token": self._access_token is not None,
            "expires_at": self._token_expires_at,
            "expires_in_seconds": max(0, self._token_expires_at - current_time),
            "is_valid": (self._access_token is not None and 
                        current_time < self._token_expires_at),
            "needs_refresh": (self._access_token is None or 
                            current_time >= (self._token_expires_at - self._refresh_buffer_seconds))
        }


# Global singleton instance and lock
_token_manager: Optional[WeChatTokenManager] = None
_manager_lock: Optional[asyncio.Lock] = None

def _get_manager_lock() -> asyncio.Lock:
    """Get or create the manager lock (lazy initialization)"""
    global _manager_lock
    if _manager_lock is None:
        _manager_lock = asyncio.Lock()
    return _manager_lock

async def get_token_manager() -> WeChatTokenManager:
    """
    Get the global WeChat token manager instance.
    Creates it if it doesn't exist (singleton pattern).
    Async-safe to prevent multiple instances being created.
    """
    global _token_manager
    
    # Fast path: if already created, return immediately
    if _token_manager is not None:
        return _token_manager
    
    # Slow path: need to create instance with lock protection
    manager_lock = _get_manager_lock()
    async with manager_lock:
        # Double-check pattern: another coroutine might have created it
        if _token_manager is None:
            _token_manager = WeChatTokenManager()
        return _token_manager
