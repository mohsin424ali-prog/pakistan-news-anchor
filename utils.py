import re
import streamlit as st
import textwrap
import logging
import validators
import html
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from num2words import num2words
from typing import Tuple, List, Optional, Dict, Union
from config import Config

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def aggressive_punctuation_cleanup(text):
    """
    CRITICAL FIX: Remove/normalize ALL punctuation that TTS engines might speak aloud.
    This is the KEY to preventing 'comma', 'hyphen', 'dash' from being spoken.
    """
    if not text:
        return ""
    
    # Step 1: Decode HTML entities first (critical for RSS feeds)
    text = html.unescape(text)
    
    # Step 2: Replace all types of dashes with regular space or hyphen
    # Em dash, en dash, horizontal bar, minus sign → space
    text = re.sub(r'[—–−‒―⁻]', ' ', text)
    
    # Step 3: Normalize all types of quotes to straight quotes
    text = re.sub(r'[""„‟❝❞]', '"', text)  # Double quotes
    text = re.sub(r'[''‚‛❛❜]', "'", text)  # Single quotes
    
    # Step 4: Remove ellipsis and multiple dots (keeps sentence flow)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'…', '.', text)
    
    # Step 5: Remove special bullets and list markers that get spoken
    text = re.sub(r'[•·●○■□▪▫]', '', text)
    
    # Step 6: Normalize whitespace around punctuation
    # Remove space before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    # Add single space after punctuation if missing
    text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
    
    # Step 7: Remove parentheses content that might disrupt flow (optional - be careful)
    # text = re.sub(r'\([^)]*\)', '', text)
    
    # Step 8: Clean multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    
    return text.strip()

@st.cache_data(ttl=3600)
def format_headline(text, language='en'):
    """Enforce headline constraints with language-specific rules"""
    constraints = Config.TEXT_CONSTRAINTS['headline'][language]
    clean_text = ' '.join(text.strip().split())
    clean_text = aggressive_punctuation_cleanup(clean_text)
    truncated = smart_truncate(clean_text, constraints['max_chars'])
    return truncated.replace('\n', ' ').strip()

@st.cache_data(ttl=3600)  
def format_description(text, language='en'):
    """Format description into line-constrained paragraphs"""
    constraints = Config.TEXT_CONSTRAINTS['description'][language]
    clean_text = ' '.join(text.strip().split())
    clean_text = aggressive_punctuation_cleanup(clean_text)
    max_chars = constraints['max_lines'] * constraints['chars_per_line']
    truncated = smart_truncate(clean_text, max_chars)
    lines = textwrap.wrap(truncated, width=constraints['chars_per_line'])
    if len(lines) < constraints['min_lines']:
        lines += [''] * (constraints['min_lines'] - len(lines))
    elif len(lines) > constraints['max_lines']:
        lines = lines[:constraints['max_lines']]
    return '\n'.join(lines)

def sanitize_html(text):
    """Remove HTML tags while preserving text content"""
    if not text:
        return ""

    try:
        # Decode HTML entities first
        text = html.unescape(text)
        
        soup = BeautifulSoup(text, "html.parser")
        # Remove all tags, keep only text
        text = soup.get_text(separator=' ', strip=True)
        
        # Additional cleanup
        text = aggressive_punctuation_cleanup(text)
        return text
    except Exception as e:
        logger.error(f"HTML sanitization failed: {e}")
        return text

def normalize_numbers(text):
    """Convert numbers and currency to words"""
    if not text:
        return text

    try:
        # Ordinal numbers (1st, 2nd, 3rd, etc.)
        text = re.sub(
            r'\b(\d+)(?:st|nd|rd|th)\b',
            lambda m: num2words(int(m.group(1)), to='ordinal'),
            text,
            flags=re.IGNORECASE
        )
        
        # Currency (Rs. 1000 → one thousand rupees)
        text = re.sub(
            r'Rs\.?\s*(\d[\d,\.]*)',
            lambda m: f"{num2words(int(m.group(1).replace(',', '').split('.')[0]))} rupees",
            text
        )
        
        # Regular numbers
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
    BEST APPROACH: Separate processing for SSML-supporting (Edge) vs non-SSML (gTTS) engines
    """
    if not text:
        return ""

    if max_length is None:
        max_length = Config.MAX_TTS_LENGTH

    try:
        # Step 1: Aggressive cleanup FIRST
        text = aggressive_punctuation_cleanup(text)
        text = text.replace('\n', ' ').strip()

        # Step 2: Basic validation
        if len(text) < 10:
            logger.warning("Text too short for TTS")
            return ""

        # Step 3: Sanitize and normalize
        processed = sanitize_html(text)
        processed = normalize_numbers(processed)

        # Step 4: Language-specific character filtering
        if language == 'ur':
            # Keep Urdu characters, basic punctuation, and spaces only
            processed = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\s.,!?]', '', processed)
        elif language == 'en':
            # Keep English alphanumeric, basic punctuation, and spaces only
            processed = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', processed)

        # Step 5: Final cleanup
        processed = re.sub(r'\s{2,}', ' ', processed)
        processed = processed.strip()

        # Step 6: Truncate if needed
        if len(processed) > max_length:
            processed = smart_truncate(processed, max_length)

        # Step 7: Engine-specific formatting
        if language == 'en':
            # Edge TTS supports SSML - use it for natural pauses
            processed = add_natural_pauses(processed)
            return f"<speak>{processed}</speak>"
        else:
            # gTTS does NOT support SSML - return plain text with natural punctuation
            # The punctuation itself will create pauses
            return processed

    except Exception as e:
        logger.error(f"TTS preparation failed: {e}")
        return ""

def add_natural_pauses(text):
    """
    Add SSML breaks only for Edge TTS (English).
    This creates natural-sounding pauses without speaking punctuation.
    """
    # Short pause after commas
    text = re.sub(r',\s*', ', <break time="300ms"/>', text)
    
    # Medium pause after sentence-ending punctuation
    text = re.sub(r'([.!?])\s*', r'\1 <break time="500ms"/>', text)
    
    # Emphasize important words (optional - cities example)
    cities = ['Karachi', 'Lahore', 'Islamabad', 'Pakistan']
    for city in cities:
        text = re.sub(
            rf'\b({city})\b',
            r'<emphasis level="moderate">\1</emphasis>',
            text,
            flags=re.IGNORECASE
        )
    
    return text

def validate_ssml(ssml_content):
    """Ensure valid SSML structure (for Edge TTS only)"""
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
        # Strip all tags and return plain text as fallback
        return re.sub(r'<[^>]+>', '', ssml_content)

def smart_truncate(text, max_length):
    """Enhanced truncation that preserves sentence structure"""
    if not text or len(text) <= max_length:
        return text

    try:
        # Try to find last sentence-ending punctuation within limits
        last_punct = -1
        for char in ['.', '!', '?']:
            pos = text.rfind(char, 0, max_length)
            if pos > last_punct:
                last_punct = pos
        
        # If we found punctuation in the last 20% of allowed length, cut there
        if last_punct != -1 and last_punct >= max_length * 0.8:
            return text[:last_punct + 1]

        # Otherwise, cut at last complete word
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '.'
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