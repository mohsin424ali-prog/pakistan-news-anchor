# english_news.py - LLM-Enhanced Version
import streamlit as st
import feedparser
from datetime import datetime, timedelta
import json
import hashlib
from newsapi import NewsApiClient
from newspaper import Article
from config import Config
from utils import sanitize_html, prepare_for_tts, smart_truncate, format_headline, format_description, aggressive_punctuation_cleanup

def extract_full_article(url):
    try:
        from newspaper import Config as NewspaperConfig
        newspaper_config = NewspaperConfig()
        newspaper_config.request_timeout = 15
        article = Article(url, config=newspaper_config)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return ""

def llm_clean_for_news_anchor(text, max_retries=2):
    """
    Use LLM to clean and polish text specifically for TTS/news anchor delivery.
    This fixes issues that regex can't handle:
    - Spacing in names (BhuttoZardari → Bhutto Zardari)
    - Typos (Tharparker → Tharparkar)
    - Awkward phrasing from RSS feeds
    - Natural number formatting
    """
    if not text or len(text) < 20:
        return text
    
    try:
        import requests
        
        # Construct a prompt that instructs the model to clean for TTS
        prompt = f"""Rewrite this news text for a TV news anchor to read aloud. Fix spacing, punctuation, and make it natural for speech. Keep the same facts and meaning. Do not add commentary.

Text: {text}

Cleaned version for news anchor:"""

        headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"}
        
        # Using FLAN-T5 (faster than BART, better at instruction following)
        api_url = "https://api-inference.huggingface.co/models/google/flan-t5-base"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.3,  # Low temperature for consistent output
                "do_sample": False,
                "repetition_penalty": 1.2
            }
        }
        
        for attempt in range(max_retries):
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    cleaned_text = result[0].get('generated_text', text)
                elif isinstance(result, dict):
                    cleaned_text = result.get('generated_text', text)
                else:
                    cleaned_text = str(result)
                
                # Validation: ensure we got reasonable output
                if cleaned_text and len(cleaned_text) > 10 and len(cleaned_text) < len(text) * 3:
                    return cleaned_text.strip()
                
            elif response.status_code == 503:  # Model loading
                import time
                time.sleep(2)
                continue
            
            # If anything fails, return original
            break
        
        return text
        
    except Exception as e:
        # Fallback to original text if LLM fails
        return text

def enhance_content(text, use_llm_cleaning=None):
    """
    Two-stage enhancement:
    1. Summarize if too long (existing BART-CNN)
    2. Clean for TTS using LLM (new)
    """
    if not text or len(text) < 50:
        return text
    
    # Check session state if parameter not provided
    if use_llm_cleaning is None:
        try:
            use_llm_cleaning = st.session_state.get('use_llm_cleaning', True)
        except:
            use_llm_cleaning = True
    
    original_text = text
    
    try:
        import requests
        headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"}
        
        # Stage 1: Summarization (if text is long)
        if len(text) > 300:
            payload = {
                "inputs": text, 
                "parameters": {
                    "max_length": 150, 
                    "min_length": 30, 
                    "do_sample": False
                }
            }
            response = requests.post(Config.SUMMARIZATION_API, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                summary = json.loads(response.content.decode("utf-8"))
                if isinstance(summary, list) and "summary_text" in summary[0]:
                    text = summary[0]["summary_text"]
        
        # Stage 2: LLM cleaning for TTS (new step)
        if use_llm_cleaning and len(text) > 20:
            text = llm_clean_for_news_anchor(text)
        
        return text if text else original_text
        
    except Exception as e:
        return original_text

def unified_article_processing(raw_title, raw_description, article_url=None, category="general"):
    """
    Enhanced processing pipeline:
    1. Extract full article if URL available
    2. Sanitize HTML
    3. Enhance/clean with LLM
    4. Apply regex cleanup
    5. Prepare for TTS
    """
    # Check if LLM cleaning is enabled from session state
    try:
        use_llm = st.session_state.get('use_llm_cleaning', True)
    except:
        use_llm = True
    
    if article_url:
        full_text = extract_full_article(article_url)
        raw_content = full_text if full_text else raw_description
    else:
        raw_content = raw_description
    
    # Step 1: Basic HTML sanitization
    processed_title = sanitize_html(raw_title)
    sanitized_content = sanitize_html(raw_content)
    
    # Step 2: LLM enhancement (summarize + clean for TTS)
    enhanced_content = enhance_content(sanitized_content, use_llm_cleaning=use_llm) if len(sanitized_content) > 50 else sanitized_content
    enhanced_content = " ".join(enhanced_content.split())
    
    # Step 3: Additional regex cleanup (belt and suspenders approach)
    enhanced_content = aggressive_punctuation_cleanup(enhanced_content)
    
    return {
        'raw_title': raw_title,
        'raw_description': raw_description,  # Keep for debugging
        'title': format_headline(processed_title, 'en'),
        'description': format_description(enhanced_content, 'en'),
        'source': 'Unknown',
        'publishedAt': 'N/A',
        'category': category,
        'tts_text': prepare_for_tts(f"{processed_title}. {enhanced_content}", 'en', Config.MAX_DESCRIPTION_LENGTH)
    }

def process_newsapi(api_articles, category):
    processed = []
    cutoff = datetime.now() - timedelta(hours=Config.ARTICLE_AGE_LIMIT)
    
    for a in api_articles[:Config.MAX_ARTICLES_PER_CATEGORY * 2]:
        pub_date = datetime.fromisoformat(a['publishedAt'].rstrip('Z'))
        if pub_date < cutoff:
            continue
            
        article_url = a.get('url', None)
        processed_article = unified_article_processing(
            a.get('title', ''), a.get('description', ''), article_url, category
        )
        
        if len(processed_article['title']) < Config.MIN_ARTICLE_LENGTH:
            continue
            
        processed.append({
            'title': processed_article['title'],
            'description': processed_article['description'],
            'source': a.get('source', {}).get('name', 'Unknown'),
            'publishedAt': pub_date.strftime('%b %d, %H:%M'),
            'category': category,
            'tts_text': processed_article['tts_text'],
            'raw_description': processed_article.get('raw_description', '')  # For debugging
        })
    
    return processed[:Config.MAX_ARTICLES_PER_CATEGORY]

def harvest_rss_feeds(category):
    articles = []
    cutoff = datetime.now() - timedelta(hours=Config.ARTICLE_AGE_LIMIT)
    
    for feed_url in Config.RSS_FEEDS.get(category, []):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                if not entry.title:
                    continue
                
                pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                if pub_date < cutoff:
                    continue
                
                article_url = entry.get('link', None)
                processed_article = unified_article_processing(
                    entry.title, entry.get('description', ''), article_url, category
                )
                
                if len(processed_article['title']) < Config.MIN_ARTICLE_LENGTH:
                    continue
                
                articles.append({
                    'title': processed_article['title'],
                    'description': processed_article['description'],
                    'source': feed.feed.get('title', 'RSS Feed'),
                    'publishedAt': pub_date.strftime('%b %d, %H:%M'),
                    'category': category,
                    'tts_text': processed_article['tts_text'],
                    'raw_description': processed_article.get('raw_description', '')  # For debugging
                })
        except Exception as e:
            continue
    
    return sorted(articles, key=lambda x: x['publishedAt'], reverse=True)[:Config.MAX_ARTICLES_PER_CATEGORY]

def process_english_news(category):
    articles = []
    
    # Process NewsAPI
    if Config.NEWS_API_KEY:
        try:
            newsapi = NewsApiClient(api_key=Config.NEWS_API_KEY)
            api_response = newsapi.get_top_headlines(
                q=category if category != 'general' else 'pakistan',
                sources='the-news-international,geo-news,dawn-news',
                page_size=30,
                language='en'
            )
            articles += process_newsapi(api_response.get('articles', []), category)
        except Exception as e:
            pass
    
    # Process RSS Feeds
    articles += harvest_rss_feeds(category)
    
    # Deduplicate and final truncation
    seen = set()
    final_articles = []
    for article in articles:
        if article['title'] not in seen:
            seen.add(article['title'])
            final_articles.append(article)
    
    return final_articles[:Config.MAX_ARTICLES_PER_CATEGORY]