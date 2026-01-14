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
    This runs BEFORE any SSML processing.
    """
    if not text:
        return ""
    
    # Step 1: Decode HTML entities first (critical for RSS feeds)
    text = html.unescape(text)
    
    # Step 2: Replace all types of dashes with simple hyphen or space
    # Em dash (—), en dash (–), minus (−), figure dash, horizontal bar → space
    text = re.sub(r'[—–−‒―⁻]', ' ', text)
    
    # Step 3: Normalize all types of quotes to straight quotes
    text = re.sub(r'[""„‟❝❞]', '"', text)  # Double quotes
    text = re.sub(r'[''‚‛❛❜]', "'", text)  # Single quotes
    
    # Step 4: Remove ellipsis and multiple dots
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'…', '.', text)
    
    # Step 5: Remove special bullets and list markers
    text = re.sub(r'[•·●○■□▪▫➤➢►▶]', '', text)
    
    # Step 6: Remove or replace symbols that TTS might speak
    text = re.sub(r'[©®™℗]', '', text)  # Copyright symbols
    text = re.sub(r'[°º]', ' degrees ', text)  # Degree symbol
    text = re.sub(r'%', ' percent ', text)  # Percent
    text = re.sub(r'&', ' and ', text)  # Ampersand
    
    # Step 7: Clean mathematical/technical symbols
    text = re.sub(r'[×÷±≈≠≤≥]', ' ', text)
    
    # Step 8: Remove brackets/parentheses content that might be citations
    # (optional - comment out if you want to keep parenthetical content)
    # text = re.sub(r'\([^)]*\)', '', text)
    # text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Step 9: Normalize whitespace around punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)  # Remove space before punctuation
    text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)  # Add space after punctuation
    
    # Step 10: Clean multiple spaces
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
        
        return text
    except Exception as e:
        logger.error(f"HTML sanitization failed: {e}")
        return text

def normalize_numbers(text):
    """
    Convert numbers and currency to words SELECTIVELY.
    Keep years and dates as-is to avoid robotic speech.
    """
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
        
        # Convert small numbers (1-99) to words, but SKIP years (1900-2099)
        def convert_number(match):
            num = int(match.group())
            # Skip years
            if 1900 <= num <= 2099:
                return str(num)
            # Skip large numbers (let TTS handle them naturally)
            if num > 999:
                return str(num)
            # Convert small numbers
            return num2words(num)
        
        text = re.sub(r'\b\d+\b', convert_number, text)
        
    except Exception as e:
        logger.error(f"Number normalization failed: {e}")
        pass
    return text

def prepare_for_tts(text, language='en', max_length=None):
    """
    FIXED VERSION: Clean text FIRST, then add SSML for engines that support it.
    This prevents punctuation names from being spoken.
    """
    if not text:
        return ""

    if max_length is None:
        max_length = Config.MAX_TTS_LENGTH

    try:
        # STEP 1: AGGRESSIVE CLEANUP FIRST (before any SSML)
        text = text.replace('\n', ' ').strip()
        text = sanitize_html(text)  # Remove HTML tags
        text = aggressive_punctuation_cleanup(text)  # Clean special punctuation
        text = normalize_numbers(text)  # Convert numbers to words

        # STEP 2: Basic validation
        if len(text) < 10:
            logger.warning("Text too short for TTS")
            return ""

        # STEP 3: Language-specific character filtering
        if language == 'ur':
            # Keep Urdu characters, basic punctuation, and spaces only
            text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\s.,!?]', '', text)
        elif language == 'en':
            # Keep English alphanumeric, basic punctuation, and spaces only
            text = re.sub(r'[^a-zA-Z0-9\s.,!?\-]', '', text)

        # STEP 4: Final cleanup
        text = re.sub(r'\s{2,}', ' ', text)
        text = text.strip()

        # STEP 5: Truncate if needed
        if len(text) > max_length:
            text = smart_truncate(text, max_length)

        # STEP 6: Engine-specific formatting (AFTER all cleanup)
        if language == 'en':
            # Edge TTS supports SSML - add natural pauses
            text_with_pauses = add_natural_pauses(text)
            return f"<speak>{text_with_pauses}</speak>"
        else:
            # gTTS does NOT support SSML - return clean plain text only
            return text

    except Exception as e:
        logger.error(f"TTS preparation failed: {e}")
        return ""

def add_natural_pauses(text):
    """
    Add SSML breaks only for Edge TTS (English).
    Works on CLEAN text without special punctuation.
    """
    # Short pause after commas
    text = re.sub(r',\s*', ', <break time="300ms"/>', text)
    
    # Medium pause after sentence-ending punctuation
    text = re.sub(r'([.!?])\s*', r'\1 <break time="500ms"/>', text)
    
    # Emphasize important words (cities example)
    cities = ['Karachi', 'Lahore', 'Islamabad', 'Pakistan', 'Chitral', 'Peshawar']
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