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

def prepare_for_tts(text, language='en', max_length=500):
    """Process text for TTS with line break removal and validation"""
    if not text:
        return ""

    try:
        # First, truncate the text to a reasonable length for TTS processing
        # Most TTS services have limits around 500-1000 characters
        if len(text) > 1000:
            text = text[:1000].rstrip()
            if text and text[-1] not in '.!?':
                text += '...'
            logger.warning(f"Text truncated from {len(text)} to 1000 characters for TTS")

        # Validate text length
        if not Config.validate_text_length(text, min_length=10, max_length=max_length * 2):
            logger.warning("Text length validation failed for TTS")
            return ""

        text = text.replace('\n', ' ')
        processed = sanitize_html(text)
        processed = normalize_numbers(processed)

        if language == 'ur':
            processed = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\s.,!?\-–—()\'"‘’”“:؛،]', '', processed)
        elif language == 'en':
            processed = re.sub(r'[^a-zA-Z0-9\s.,!?\-–—()\'"‘’”“:;]', '', processed)
        else:
            logger.warning(f"Unknown language for TTS: {language}")
            return ""

        processed = re.sub(r'([.!?])', r'\1<break time="500ms"/>', processed)
        cities = ['Karachi', 'Lahore', 'Islamabad', 'کراچی', 'لاہور', 'اسلام آباد']
        city_pattern = '|'.join(re.escape(city) for city in cities)
        processed = re.sub(
            rf'\b({city_pattern})\b',
            r'<emphasis>\1</emphasis>',
            processed,
            flags=re.IGNORECASE
        )
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
                cleaned.extend(element.text or '')
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
        last_punct = max(text.rfind('.', 0, max_length),
                        text.rfind('!', 0, max_length),
                        text.rfind('?', 0, max_length))
        if last_punct != -1 and last_punct >= max_length * 0.8:
            return text[:last_punct + 1]

        last_tag_start = text.rfind('<', 0, max_length)
        last_tag_end = text.rfind('>', 0, max_length)
        if last_tag_start > last_tag_end:
            truncated = text[:last_tag_start]
            if len(truncated) >= max_length * 0.7:
                return truncated + '...'
            return text[:max_length]

        truncated = text[:max_length].rsplit(' ', 1)[0]
        if len(truncated) >= max_length * 0.7:
            return truncated + '...'
        return text[:max_length]
    except Exception as e:
        logger.error(f"Text truncation failed: {e}")
        return text[:max_length] if text else ""

def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        if not url:
            return False

        # Check if URL is valid
        if not validators.url(url):
            logger.warning(f"Invalid URL format: {url}")
            return False

        # Check for malicious patterns
        malicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file://'
        ]

        for pattern in malicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                logger.warning(f"Potentially malicious URL detected: {url}")
                return False

        return True
    except Exception as e:
        logger.error(f"URL validation failed: {e}")
        return False

def validate_file_upload(file_obj, allowed_types: List[str] = None, max_size_mb: int = 5) -> Tuple[bool, str]:
    """Validate uploaded files"""
    if allowed_types is None:
        allowed_types = ['png', 'jpg', 'jpeg', 'gif']

    try:
        if not file_obj:
            return False, "No file uploaded"

        # Check file size
        file_size_mb = len(file_obj.getvalue()) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, f"File too large ({file_size_mb:.1f}MB). Maximum allowed: {max_size_mb}MB"

        # Check file extension
        file_extension = file_obj.name.split('.')[-1].lower()
        if file_extension not in allowed_types:
            return False, f"Invalid file type. Allowed types: {', '.join(allowed_types)}"

        # Check for suspicious filename patterns
        if re.search(r'[<>:"/\\|?*]', file_obj.name):
            return False, "Invalid characters in filename"

        return True, "Valid"
    except Exception as e:
        logger.error(f"File validation failed: {e}")
        return False, f"Validation error: {str(e)}"

def validate_article_data(article: dict) -> Tuple[bool, str]:
    """Validate article data with comprehensive checks"""
    required_fields = ['title', 'description', 'source', 'category']

    try:
        # Check required fields
        for field in required_fields:
            if field not in article or not article[field]:
                return False, f"Missing required field: {field}"

        # Check content safety
        if not Config.is_content_safe(article['title']) or not Config.is_content_safe(article['description']):
            return False, "Content contains prohibited material"

        # Check content length
        if len(article['title']) < 10:
            return False, "Title too short (minimum 10 characters)"

        if len(article['description']) < 30:
            return False, "Description too short (minimum 30 characters)"

        # Validate category
        if not Config.validate_category(article['category']):
            return False, f"Invalid category: {article['category']}"

        # Validate source
        if not article['source'] or len(article['source']) < 2:
            return False, "Invalid source name"

        # Check for duplicate content (basic check)
        if 'title' in article and 'description' in article:
            if article['title'].lower() in article['description'].lower():
                logger.warning("Potential content duplication detected")

        return True, "Valid"
    except Exception as e:
        logger.error(f"Article validation failed: {e}")
        return False, f"Validation error: {str(e)}"

def rate_limit_handler(func):
    """Decorator to handle rate limiting"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                logger.warning("Rate limit exceeded, implementing backoff")
                import time
                time.sleep(5)  # Wait 5 seconds before retry
                return func(*args, **kwargs)
            raise
    return wrapper