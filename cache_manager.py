# cache_manager.py
import json
import hashlib
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import streamlit as st
from config import Config, logger

class CacheManager:
    """Manages caching for RSS feeds and processed content"""

    def __init__(self):
        # Get TEMP_DIR as a Path object and ensure it exists
        temp_dir = Config().TEMP_DIR
        temp_dir.mkdir(exist_ok=True)  # Ensure temp directory exists first
        self.cache_dir = temp_dir / 'cache'
        self.cache_dir.mkdir(exist_ok=True)  # Then create cache subdirectory
        self.cache_metadata = self._load_cache_metadata()

    def _load_cache_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load cache metadata from file"""
        metadata_file = self.cache_dir / 'metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {}

    def _save_cache_metadata(self) -> None:
        """Save cache metadata to file"""
        metadata_file = self.cache_dir / 'metadata.json'
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")

    def _get_cache_key(self, category: str, lang: str = 'en') -> str:
        """Generate cache key for category and language"""
        key_string = f"{category}_{lang}_{Config.NEWS_API_KEY or 'no_key'}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is valid based on timestamp"""
        if cache_key not in self.cache_metadata:
            return False

        cache_info = self.cache_metadata[cache_key]
        cache_time = datetime.fromisoformat(cache_info['timestamp'])
        now = datetime.now()

        # Check if cache is older than configured cache time
        if (now - cache_time).total_seconds() > Config.CACHE_TIME:
            return False

        # Check if any cached files are missing
        for file_path in cache_info.get('files', []):
            if not Path(file_path).exists():
                return False

        return True

    def get_cached_articles(self, category: str, lang: str = 'en') -> Optional[List[Dict]]:
        """Retrieve cached articles if valid"""
        cache_key = self._get_cache_key(category, lang)

        if not self._is_cache_valid(cache_key):
            return None

        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cached articles: {e}")
                return None

        return None

    def cache_articles(self, articles: List[Dict], category: str, lang: str = 'en') -> None:
        """Cache articles with metadata"""
        cache_key = self._get_cache_key(category, lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            # Save articles
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)

            # Update metadata
            self.cache_metadata[cache_key] = {
                'timestamp': datetime.now().isoformat(),
                'category': category,
                'language': lang,
                'article_count': len(articles),
                'files': [str(cache_file)]
            }

            self._save_cache_metadata()
            logger.info(f"Cached {len(articles)} articles for {category}/{lang}")

        except Exception as e:
            logger.error(f"Failed to cache articles: {e}")

    def clear_expired_cache(self) -> None:
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = []

        for cache_key, cache_info in self.cache_metadata.items():
            cache_time = datetime.fromisoformat(cache_info['timestamp'])
            if (now - cache_time).total_seconds() > Config.CACHE_TIME:
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            # Remove cache file
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()

            # Remove metadata
            del self.cache_metadata[cache_key]

        if expired_keys:
            self._save_cache_metadata()
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_count = 0
        total_size = 0

        for cache_key, cache_info in self.cache_metadata.items():
            if self._is_cache_valid(cache_key):
                valid_count += 1
                for file_path in cache_info.get('files', []):
                    if Path(file_path).exists():
                        total_size += Path(file_path).stat().st_size

        return {
            'total_entries': len(self.cache_metadata),
            'valid_entries': valid_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

# Global cache manager instance
cache_manager = CacheManager()

def cache_news_data(func):
    """Decorator to cache news processing functions"""
    def wrapper(category, lang='en', *args, **kwargs):
        # Check if we have valid cache
        cached_data = cache_manager.get_cached_articles(category, lang)
        if cached_data is not None:
            logger.info(f"Using cached data for {category}/{lang}")
            return cached_data

        # Process and cache the data
        result = func(category, lang, *args, **kwargs)

        if result:
            cache_manager.cache_articles(result, category, lang)

        return result

    return wrapper

def clear_cache(category: str = None, lang: str = None) -> None:
    """Clear cache for specific category/language or all cache"""
    if category and lang:
        cache_key = cache_manager._get_cache_key(category, lang)
        cache_file = cache_manager.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            cache_file.unlink()
        if cache_key in cache_manager.cache_metadata:
            del cache_manager.cache_metadata[cache_key]
            cache_manager._save_cache_metadata()
        st.success(f"Cleared cache for {category}/{lang}")
    else:
        # Clear all cache
        import shutil
        shutil.rmtree(cache_manager.cache_dir, ignore_errors=True)
        cache_manager.cache_dir.mkdir(exist_ok=True)
        cache_manager.cache_metadata = {}
        st.success("Cleared all cached data")

def get_cache_status() -> Dict[str, Any]:
    """Get current cache status"""
    cache_manager.clear_expired_cache()
    return cache_manager.get_cache_stats()