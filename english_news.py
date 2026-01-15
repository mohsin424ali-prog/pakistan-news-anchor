# english_news.py - LLM-Enhanced with Groq Integration
import streamlit as st
import feedparser
from datetime import datetime, timedelta
import json
import hashlib
from newsapi import NewsApiClient
from newspaper import Article
from config import Config
from utils import sanitize_html, prepare_for_tts, smart_truncate, format_headline, format_description, aggressive_punctuation_cleanup

# Initialize LLM processor (singleton)
_llm_processor = None

def get_llm_processor():
    """Get or create LLM processor instance with fallback"""
    global _llm_processor
    
    if _llm_processor is None:
        try:
            # Try Groq first (best option)
            if Config.GROQ_API_KEY:
                from llm_processor import LLMProcessor
                print("✅ Using Groq LLM for English news processing")
                _llm_processor = LLMProcessor(api_key=Config.GROQ_API_KEY)
                return _llm_processor
            else:
                print("⚠️ No Groq API key found, using fallback processing")
                _llm_processor = False  # Mark as unavailable
                return None
        except ImportError:
            print("⚠️ llm_processor.py not found, using fallback")
            _llm_processor = False
            return None
        except Exception as e:
            print(f"❌ Failed to initialize Groq LLM: {e}")
            _llm_processor = False
            return None
    
    # Return None if previously failed
    return _llm_processor if _llm_processor is not False else None


def extract_full_article(url):
    """Extract full article text from URL"""
    try:
        from newspaper import Config as NewspaperConfig
        newspaper_config = NewspaperConfig()
        newspaper_config.request_timeout = 15
        article = Article(url, config=newspaper_config)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"⚠️ Failed to extract article from {url}: {e}")
        return ""


def llm_clean_for_news_anchor(text, max_retries=2):
    """
    LEGACY FUNCTION - Kept for backward compatibility
    Use LLM to clean and polish text for TTS/news anchor delivery.
    
    Now uses Groq if available, falls back to FLAN-T5.
    """
    if not text or len(text) < 20:
        return text
    
    # Try Groq first
    llm = get_llm_processor()
    if llm:
        try:
            result = llm.summarize_and_clean(
                text=text,
                language='en',
                max_length=150,
                add_ssml=False  # No SSML in this legacy function
            )
            return result['cleaned']
        except Exception as e:
            print(f"⚠️ Groq LLM failed, trying fallback: {e}")
    
    # Fallback to FLAN-T5 (your original code)
    try:
        import requests
        
        prompt = f"""Rewrite this news text for a TV news anchor to read aloud. Fix spacing, punctuation, and make it natural for speech. Keep the same facts and meaning. Do not add commentary.

Text: {text}

Cleaned version for news anchor:"""

        headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"}
        api_url = "https://api-inference.huggingface.co/models/google/flan-t5-base"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.3,
                "do_sample": False,
                "repetition_penalty": 1.2
            }
        }
        
        for attempt in range(max_retries):
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if isinstance(result, list) and len(result) > 0:
                    cleaned_text = result[0].get('generated_text', text)
                elif isinstance(result, dict):
                    cleaned_text = result.get('generated_text', text)
                else:
                    cleaned_text = str(result)
                
                if cleaned_text and len(cleaned_text) > 10 and len(cleaned_text) < len(text) * 3:
                    return cleaned_text.strip()
                
            elif response.status_code == 503:
                import time
                time.sleep(2)
                continue
            
            break
        
        return text
        
    except Exception as e:
        print(f"⚠️ Fallback LLM also failed: {e}")
        return text


def enhance_content_with_groq(text):
    """
    NEW FUNCTION - Enhanced content processing with Groq
    Returns structured result with all fields needed for TTS
    """
    if not text or len(text) < Config.MIN_ARTICLE_LENGTH:
        return None
    
    llm = get_llm_processor()
    if not llm:
        return None
    
    try:
        print(f"🤖 Processing with Groq LLM: {len(text)} chars")
        
        result = llm.summarize_and_clean(
            text=text,
            language='en',
            max_length=Config.LLM_CONFIG.get('summary_max_words', 150),
            add_ssml=Config.LLM_CONFIG.get('add_ssml_english', True)
        )
        
        print(f"✅ Groq processing complete")
        return result
        
    except Exception as e:
        print(f"❌ Groq processing failed: {e}")
        return None


def enhance_content(text, use_llm_cleaning=None):
    """
    UPDATED - Two-stage enhancement with Groq priority:
    1. Try Groq first (best quality, fast)
    2. Fall back to legacy BART/FLAN-T5
    3. Fall back to original text
    """
    if not text or len(text) < 50:
        return text
    
    # Check session state if parameter not provided
    if use_llm_cleaning is None:
        try:
            use_llm_cleaning = st.session_state.get('use_llm_cleaning', True)
        except:
            use_llm_cleaning = True
    
    if not use_llm_cleaning:
        return text
    
    original_text = text
    
    # Try Groq first (NEW)
    groq_result = enhance_content_with_groq(text)
    if groq_result:
        return groq_result['cleaned']  # Return cleaned text
    
    # Fallback to legacy method (BART + FLAN-T5)
    try:
        import requests
        headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"}
        
        # Stage 1: Summarization if text is long
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
        
        # Stage 2: LLM cleaning for TTS
        if len(text) > 20:
            text = llm_clean_for_news_anchor(text)
        
        return text if text else original_text
        
    except Exception as e:
        print(f"⚠️ All LLM processing failed: {e}")
        return original_text


def unified_article_processing(raw_title, raw_description, article_url=None, category="general"):
    """
    UPDATED - Enhanced processing pipeline with Groq integration:
    1. Extract full article if URL available
    2. Sanitize HTML
    3. Try Groq LLM processing (NEW - gets everything in one call)
    4. Fall back to legacy processing if Groq fails
    5. Apply final cleanup and prepare for TTS
    """
    # Check if LLM cleaning is enabled
    try:
        use_llm = st.session_state.get('use_llm_cleaning', True)
    except:
        use_llm = True
    
    # Get raw content
    if article_url:
        full_text = extract_full_article(article_url)
        raw_content = full_text if full_text else raw_description
    else:
        raw_content = raw_description
    
    # Step 1: Basic HTML sanitization
    processed_title = sanitize_html(raw_title)
    sanitized_content = sanitize_html(raw_content)
    
    # Step 2: Try Groq LLM processing (NEW - one call gets everything)
    groq_result = None
    if use_llm and len(sanitized_content) >= Config.MIN_ARTICLE_LENGTH:
        groq_result = enhance_content_with_groq(sanitized_content)
    
    if groq_result:
        # Use Groq results
        print("✅ Using Groq LLM results")
        return {
            'raw_title': raw_title,
            'raw_description': raw_description,
            'title': format_headline(groq_result.get('headline', processed_title), 'en'),
            'description': format_description(groq_result['summary'], 'en'),
            'source': 'Unknown',
            'publishedAt': 'N/A',
            'category': category,
            'tts_text': groq_result['tts_text']  # Already has SSML if enabled
        }
    else:
        # Fall back to legacy processing
        print("⚠️ Using legacy processing (no Groq)")
        enhanced_content = enhance_content(sanitized_content, use_llm_cleaning=use_llm) if len(sanitized_content) > 50 else sanitized_content
        enhanced_content = " ".join(enhanced_content.split())
        enhanced_content = aggressive_punctuation_cleanup(enhanced_content)
        
        return {
            'raw_title': raw_title,
            'raw_description': raw_description,
            'title': format_headline(processed_title, 'en'),
            'description': format_description(enhanced_content, 'en'),
            'source': 'Unknown',
            'publishedAt': 'N/A',
            'category': category,
            'tts_text': prepare_for_tts(f"{processed_title}. {enhanced_content}", 'en', Config.MAX_DESCRIPTION_LENGTH)
        }


def process_newsapi(api_articles, category):
    """Process NewsAPI articles with LLM enhancement"""
    processed = []
    cutoff = datetime.now() - timedelta(hours=Config.ARTICLE_AGE_LIMIT)
    
    for idx, a in enumerate(api_articles[:Config.MAX_ARTICLES_PER_CATEGORY * 2]):
        try:
            pub_date = datetime.fromisoformat(a['publishedAt'].rstrip('Z'))
            if pub_date < cutoff:
                continue
            
            print(f"Processing NewsAPI article {idx + 1}: {a.get('title', '')[:50]}...")
            
            article_url = a.get('url', None)
            processed_article = unified_article_processing(
                a.get('title', ''), 
                a.get('description', ''), 
                article_url, 
                category
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
                'raw_description': processed_article.get('raw_description', '')
            })
            
        except Exception as e:
            print(f"⚠️ Failed to process NewsAPI article: {e}")
            continue
    
    return processed[:Config.MAX_ARTICLES_PER_CATEGORY]


def harvest_rss_feeds(category):
    """Harvest and process RSS feed articles with LLM enhancement"""
    articles = []
    cutoff = datetime.now() - timedelta(hours=Config.ARTICLE_AGE_LIMIT)
    
    for feed_url in Config.RSS_FEEDS.get(category, []):
        try:
            print(f"📡 Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for idx, entry in enumerate(feed.entries[:10]):
                if not entry.title:
                    continue
                
                pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now()
                if pub_date < cutoff:
                    continue
                
                print(f"Processing RSS article {idx + 1}: {entry.title[:50]}...")
                
                article_url = entry.get('link', None)
                processed_article = unified_article_processing(
                    entry.title, 
                    entry.get('description', ''), 
                    article_url, 
                    category
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
                    'raw_description': processed_article.get('raw_description', '')
                })
                
        except Exception as e:
            print(f"⚠️ Failed to process RSS feed {feed_url}: {e}")
            continue
    
    return sorted(articles, key=lambda x: x['publishedAt'], reverse=True)[:Config.MAX_ARTICLES_PER_CATEGORY]


def process_english_news(category):
    """
    UPDATED - Main function to process English news with Groq LLM integration
    """
    print(f"\n{'='*80}")
    print(f"📰 PROCESSING ENGLISH NEWS - Category: {category}")
    print(f"{'='*80}")
    
    # Check LLM availability
    llm = get_llm_processor()
    if llm:
        print("✅ Groq LLM available - high quality processing enabled")
    else:
        print("⚠️ Groq LLM not available - using fallback processing")
    
    articles = []
    
    # Process NewsAPI
    if Config.NEWS_API_KEY:
        try:
            print("\n📡 Fetching from NewsAPI...")
            newsapi = NewsApiClient(api_key=Config.NEWS_API_KEY)
            api_response = newsapi.get_top_headlines(
                q=category if category != 'general' else 'pakistan',
                sources='the-news-international,geo-news,dawn-news',
                page_size=30,
                language='en'
            )
            articles += process_newsapi(api_response.get('articles', []), category)
            print(f"✅ NewsAPI: {len(articles)} articles processed")
        except Exception as e:
            print(f"⚠️ NewsAPI failed: {e}")
    else:
        print("⚠️ No NewsAPI key available")
    
    # Process RSS Feeds
    print("\n📡 Fetching from RSS feeds...")
    rss_articles = harvest_rss_feeds(category)
    articles += rss_articles
    print(f"✅ RSS: {len(rss_articles)} articles processed")
    
    # Deduplicate and final truncation
    seen = set()
    final_articles = []
    for article in articles:
        if article['title'] not in seen:
            seen.add(article['title'])
            final_articles.append(article)
    
    print(f"\n✅ Final: {len(final_articles)} unique articles ready")
    print(f"{'='*80}\n")
    
    return final_articles[:Config.MAX_ARTICLES_PER_CATEGORY]