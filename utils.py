import re
import streamlit as st
import textwrap
import logging
import validators
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from num2words import num2words
from typing import Tuple, List, Optional, Dict, Union
from config import Config

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

@st.cache_data(ttl=3600)
def format_headline(text, language='en'):
    """Enforce headline constraints with language-specific rules"""
    constraints = Config.TEXT_CONSTRAINTS['headline'][language]
    clean_text = ' '.join(text.strip().split())
    truncated = smart_truncate(clean_text, constraints['max_chars'])
    return truncated.replace('\n', ' ').strip()

@st.cache_data(ttl=3600)  
def format_description(text, language='en'):
    """Format description into line-constrained paragraphs"""
    constraints = Config.TEXT_CONSTRAINTS['description'][language]
    clean_text = ' '.join(text.strip().split())
    max_chars = constraints['max_lines'] * constraints['chars_per_line']
    truncated = smart_truncate(clean_text, max_chars)
    lines = textwrap.wrap(truncated, width=constraints['chars_per_line'])
    if len(lines) < constraints['min_lines']:
        lines += [''] * (constraints['min_lines'] - len(lines))
    elif len(lines) > constraints['max_lines']:
        lines = lines[:constraints['max_lines']]
    return '\n'.join(lines)

def sanitize_html(text):
    """Remove HTML tags while preserving SSML structure"""
    if not text:
        return ""

    try:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.find_all(True):
            if tag.name not in ['speak', 'break', 'emphasis']:
                tag.unwrap()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.error(f"HTML sanitization failed: {e}")
        return text

def normalize_numbers(text):
    """Convert numbers and currency to words with SSML compatibility"""
    if not text:
        return text

    try:
        text = re.sub(
            r'\b(\d+)(?:st|nd|rd|th)\b',
            lambda m: num2words(int(m.group(1))),
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r'Rs\.?\s*(\d[\d,\.]*)',
            lambda m: f"{num2words(int(m.group(1).replace(',', '').split('.')[0]))} rupees",
            text
        )
        text = re.sub(
            r'\b\d+\b',
            lambda m: num2words(int(m.group())),
            text
        )
    except Exception as e:
        logger.error(f"Number normalization failed: {e}")
        pass
    return text

def prepare_for_tts(text, language='en', max_length=None):
    """
    BEST APPROACH: Process text for TTS using Config limits rather than hardcoded ones.
    """
    if not text:
        return ""

    # Use max length from Config if not explicitly provided
    if max_length is None:
        max_length = Config.MAX_TTS_LENGTH

    try:
        # Step 1: Clean basic whitespace
        text = text.replace('\n', ' ').strip()

        # Step 2: Validate using the smart logic in Config
        # We allow a buffer for SSML tags by passing max_length * 1.5 to the validator
        if not Config.validate_text_length(text, min_length=10, max_length=max_length):
            logger.warning("Text length validation failed for TTS")
            return ""

        # Step 3: Processing
        processed = sanitize_html(text)
        processed = normalize_numbers(processed)

        # Step 4: Language Specific Cleaning
        if language == 'ur':
            processed = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\s.,!?\-–—()\'"‘’”“:؛،]', '', processed)
        elif language == 'en':
            processed = re.sub(r'[^a-zA-Z0-9\s.,!?\-–—()\'"‘’”“:;]', '', processed)
        else:
            logger.warning(f"Unknown language for TTS: {language}")
            return ""

        # Step 5: SSML Enhancements
        processed = re.sub(r'([.!?])', r'\1<break time="500ms"/>', processed)
        
        cities = ['Karachi', 'Lahore', 'Islamabad', 'کراچی', 'لاہور', 'اسلام آباد']
        city_pattern = '|'.join(re.escape(city) for city in cities)
        processed = re.sub(
            rf'\b({city_pattern})\b',
            r'<emphasis>\1</emphasis>',
            processed,
            flags=re.IGNORECASE
        )

        # Step 6: Final Truncate to ensure it fits the engine limit
        truncated = smart_truncate(processed, max_length)
        
        return f"<speak>{validate_ssml(truncated)}</speak>"
    except Exception as e:
        logger.error(f"TTS preparation failed: {e}")
        return ""

def validate_ssml(ssml_content):
    """Ensure valid SSML structure"""
    if not ssml_content:
        return ""

    try:
        wrapped = f"<root>{ssml_content}</root>"
        root = ElementTree.fromstring(wrapped)
        cleaned = []
        for element in root.iter():
            if element.tag == 'root':
                if element.text:
                    cleaned.append(element.text)
                continue
            cleaned.append(ElementTree.tostring(element, 'unicode').strip())
        return ''.join(cleaned)
    except ElementTree.ParseError as e:
        logger.error(f"SSML validation failed: {e}")
        return re.sub(r'<\/?[a-z]+[^>]*>', '', ssml_content)

def smart_truncate(text, max_length):
    """Enhanced truncation with SSML awareness"""
    if not text or len(text) <= max_length:
        return text

    try:
        # Try to find last punctuation within limits
        last_punct = -1
        for char in ['.', '!', '?']:
            pos = text.rfind(char, 0, max_length)
            if pos > last_punct:
                last_punct = pos
        
        if last_punct != -1 and last_punct >= max_length * 0.8:
            return text[:last_punct + 1]

        # Ensure we don't cut in the middle of an SSML tag
        last_tag_start = text.rfind('<', 0, max_length)
        last_tag_end = text.rfind('>', 0, max_length)
        if last_tag_start > last_tag_end:
            # We are inside a tag, cut before the tag starts
            return text[:last_tag_start].strip() + '...'

        # Standard word-based cut
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '...'
    except Exception as e:
        logger.error(f"Text truncation failed: {e}")
        return text[:max_length] if text else ""

def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        if not url:
            return False
        if not validators.url(url):
            return False
        
        malicious_patterns = [r'javascript:', r'data:', r'vbscript:', r'file://']
        for pattern in malicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        return True
    except Exception:
        return False

def validate_file_upload(file_obj, allowed_types: List[str] = None, max_size_mb: int = 5) -> Tuple[bool, str]:
    """Validate uploaded files"""
    if allowed_types is None:
        allowed_types = ['png', 'jpg', 'jpeg', 'gif']
    try:
        if not file_obj:
            return False, "No file uploaded"
        file_size_mb = len(file_obj.getvalue()) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"File too large. Max: {max_size_mb}MB"
        file_extension = file_obj.name.split('.')[-1].lower()
        if file_extension not in allowed_types:
            return False, f"Invalid type. Allowed: {allowed_types}"
        return True, "Valid"
    except Exception as e:
        return False, str(e)

def validate_article_data(article: dict) -> Tuple[bool, str]:
    """Validate article data"""
    required_fields = ['title', 'description', 'source', 'category']
    try:
        for field in required_fields:
            if field not in article or not article[field]:
                return False, f"Missing {field}"
        if not Config.is_content_safe(article['title']) or not Config.is_content_safe(article['description']):
            return False, "Unsafe content"
        return True, "Valid"
    except Exception as e:
        return False, str(e)

def rate_limit_handler(func):
    """Decorator to handle rate limiting"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "rate limit" in str(e).lower():
                import time
                time.sleep(5)
                return func(*args, **kwargs)
            raise
    return wrapper