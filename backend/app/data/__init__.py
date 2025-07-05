"""
Data Access Layer Module
Provides unified data reading interface, supports local markdown files and future remote data source extensions
"""

import os
import asyncio
from typing import Dict, Optional
from pathlib import Path
import aiofiles
from ..logger.logger import log_error, log_info, log_warn

class DataAccessLayer:
    """
    Data Access Layer that provides unified data reading interface
    Supports local markdown file reading with reserved interface for remote data source extensions
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize Data Access Layer
        
        Args:
            data_dir: Data directory path, defaults to app/data/markdown
        """
        if data_dir is None:
            # Get the app/data/markdown path relative to current file directory
            current_dir = Path(__file__).parent.parent
            self.data_dir = current_dir / "data" / "markdown"
        else:
            self.data_dir = Path(data_dir)
        
        # Content cache
        self._cache: Dict[str, str] = {}
        self._cache_lock = asyncio.Lock()
        
        log_info(f"DataAccessLayer initialized with data_dir: {self.data_dir}")
    
    async def get_content(self, content_type: str, use_cache: bool = True) -> Optional[str]:
        """
        Get content of specified type
        
        Args:
            content_type: Content type (e.g.: brand, pricing, styles, purchase, other)
            use_cache: Whether to use cache, defaults to True
            
        Returns:
            Content string, returns None if file doesn't exist
        """
        try:
            # Check cache
            if use_cache and content_type in self._cache:
                # log_info(f"Returning cached content for {content_type}")
                return self._cache[content_type]
            
            # Build file path
            file_path = self.data_dir / f"{content_type}.md"
            
            if not file_path.exists():
                log_warn(f"Content file not found: {file_path}")
                return None
            
            # Read file content asynchronously
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Update cache
            if use_cache:
                async with self._cache_lock:
                    self._cache[content_type] = content

            log_info(f"[DataAccessLayer] Successfully loaded content for {content_type}")
            return content
            
        except Exception as e:
            log_error(f"[DataAccessLayer] Error loading content for {content_type}: {str(e)}")
            return None
    
    async def refresh_cache(self, content_type: str = None):
        """
        Refresh cache
        
        Args:
            content_type: Specific content type to refresh, None means refresh all cache
        """
        async with self._cache_lock:
            if content_type:
                # Refresh cache for specific type
                if content_type in self._cache:
                    del self._cache[content_type]
                    log_info(f"[DataAccessLayer] Cache refreshed for {content_type}")
            else:
                # Clear all cache
                self._cache.clear()
                log_info("[DataAccessLayer] All cache cleared")

    async def preload_all_content(self):
        """
        Preload all content to cache
        """
        content_types = ['brand', 'pricing', 'styles', 'purchase', 'other']
        
        tasks = []
        for content_type in content_types:
            tasks.append(self.get_content(content_type, use_cache=True))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        loaded_count = sum(1 for result in results if isinstance(result, str))
        log_info(f"[DataAccessLayer] Preloaded {loaded_count}/{len(content_types)} content files")

    def get_available_content_types(self) -> list:
        """
        Get all available content types
        
        Returns:
            List of available content types
        """
        if not self.data_dir.exists():
            return []
        
        content_types = []
        for file_path in self.data_dir.glob("*.md"):
            content_types.append(file_path.stem)
        
        return sorted(content_types)

# Global data access layer instance
_data_access_layer = None
_dal_lock = asyncio.Lock()

async def get_data_access_layer() -> DataAccessLayer:
    """
    Get global data access layer instance (singleton pattern)
    
    Returns:
        DataAccessLayer instance
    """
    global _data_access_layer
    
    if _data_access_layer is None:
        async with _dal_lock:
            if _data_access_layer is None:
                _data_access_layer = DataAccessLayer()
                # Preload content
                await _data_access_layer.preload_all_content()
    
    return _data_access_layer

# Convenience function
async def get_yuehua_content(content_type: str, use_cache: bool = True) -> Optional[str]:
    """
    Convenience function to get Yuehua Pearl related content
    
    Args:
        content_type: Content type (brand, pricing, styles, purchase, other)
        use_cache: Whether to use cache
        
    Returns:
        Content string
    """
    dal = await get_data_access_layer()
    return await dal.get_content(content_type, use_cache)
