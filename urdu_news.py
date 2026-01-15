# urdu_news.py - LLM-Enhanced with Groq Integration
import feedparser
from datetime import datetime, timedelta
import hashlib
from newspaper import Article
from config import Config
from utils import sanitize_html, prepare_for_tts, smart_truncate, format_headline, format_description

# Urdu keywords for filtering Pakistani news
PAKISTANI_KEYWORDS_URDU = [
    'پاکستان', 'اسلام آباد', 'کراچی', 'لاہور',
    'پنجاب', 'سندھ', 'خیبر', 'وفاق', 'حکومت',
    'وزیراعظم', 'صدر', 'قومی اسمبلی'
]

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
                print("✅ Using Groq LLM for Urdu news processing")
                _llm_processor = LLMProcessor(api_key=Config.GROQ_API_KEY)
                return _llm_processor
            else:
                print("⚠️ No Groq API key found for Urdu processing")
                _llm_processor = False  # Mark as unavailable
                return None
        except ImportError:
            print("⚠️ llm_processor.py not found, using fallback")
            _llm_processor = False
            return None
        except Exception as e:
            print(f"❌ Failed to initialize Groq LLM for Urdu: {e}")
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
        print(f"⚠️ Failed to extract Urdu article from {url}: {e}")
        return ""


def enhance_urdu_content_with_groq(text):
    """
    NEW FUNCTION - Enhanced Urdu content processing with Groq
    Returns structured result with all fields needed for TTS
    
    Note: No SSML for Urdu as gTTS doesn't support it
    """
    if not text or len(text) < Config.MIN_ARTICLE_LENGTH:
        return None
    
    llm = get_llm_processor()
    if not llm:
        return None
    
    try:
        print(f"🤖 Processing Urdu text with Groq LLM: {len(text)} chars")
        
        result = llm.summarize_and_clean(
            text=text,
            language='ur',
            max_length=Config.LLM_CONFIG.get('summary_max_words', 150),
            add_ssml=False  # IMPORTANT: No SSML for Urdu
        )
        
        print(f"✅ Groq processing complete for Urdu")
        return result
        
    except Exception as e:
        print(f"❌ Groq processing failed for Urdu: {e}")
        return None


def unified_article_processing(raw_title, raw_description, article_url=None, category="general"):
    """
    UPDATED - Enhanced Urdu processing pipeline with Groq integration:
    1. Extract full article if URL available
    2. Sanitize HTML
    3. Try Groq LLM processing (NEW)
    4. Fall back to basic processing if Groq fails
    5. Prepare for TTS (no SSML for Urdu)
    """
    # Get raw content
    if article_url:
        full_text = extract_full_article(article_url)
        raw_content = full_text if full_text else raw_description
    else:
        raw_content = raw_description
    
    # Step 1: Basic HTML sanitization
    processed_title = sanitize_html(raw_title)
    sanitized_content = sanitize_html(raw_content)
    
    # Step 2: Try Groq LLM processing (NEW)
    groq_result = None
    if len(sanitized_content) >= Config.MIN_ARTICLE_LENGTH:
        groq_result = enhance_urdu_content_with_groq(sanitized_content)
    
    if groq_result:
        # Use Groq results
        print("✅ Using Groq LLM results for Urdu")
        return {
            'raw_title': raw_title,
            'raw_description': raw_description,
            'title': format_headline(groq_result.get('headline', processed_title), 'ur'),
            'description': format_description(groq_result['summary'], 'ur'),
            'source': 'نامعلوم',
            'publishedAt': 'N/A',
            'category': category,
            'tts_text': groq_result['tts_text']  # No SSML for Urdu
        }
    else:
        # Fall back to basic processing
        print("⚠️ Using basic processing for Urdu (no Groq)")
        enhanced_content = sanitized_content
        
        return {
            'raw_title': raw_title,
            'raw_description': raw_description,
            'title': format_headline(processed_title, 'ur'),
            'description': format_description(enhanced_content, 'ur'),
            'source': 'نامعلوم',
            'publishedAt': 'N/A',
            'category': category,
            'tts_text': prepare_for_tts(f"{processed_title}. {enhanced_content}", 'ur', Config.MAX_DESCRIPTION_LENGTH)
        }


def harvest_rss_feeds(category):
    """Harvest and process Urdu RSS feed articles with LLM enhancement"""
    articles = []
    feeds = Config.URDU_RSS_FEEDS.get(category, [])
    cutoff = datetime.now() - timedelta(hours=Config.ARTICLE_AGE_LIMIT)
    
    for feed_url in feeds:
        try:
            print(f"📡 Fetching Urdu RSS feed: {feed_url}")
            parsed_feed = feedparser.parse(feed_url)
            
            if not hasattr(parsed_feed, 'entries'):
                print(f"⚠️ No entries found in feed: {feed_url}")
                continue
            
            for idx, entry in enumerate(parsed_feed.entries[:20]):
                if not entry.get('title'):
                    continue
                
                # Handle publication date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()
                
                # Skip old articles
                if pub_date < cutoff:
                    continue
                
                print(f"Processing Urdu article {idx + 1}: {entry.get('title', '')[:50]}...")
                
                # Process article with LLM
                processed_article = unified_article_processing(
                    entry.get('title', ''), 
                    entry.get('description', ''), 
                    entry.get('link'), 
                    category
                )
                
                # Skip if too short
                if len(processed_article['title']) < Config.MIN_ARTICLE_LENGTH:
                    continue
                
                articles.append({
                    'title': processed_article['title'],
                    'description': processed_article['description'],
                    'source': parsed_feed.feed.get('title', 'RSS Feed'),
                    'publishedAt': pub_date.strftime('%Y-%m-%d %H:%M') if pub_date else 'حالیہ',
                    'category': category,
                    'tts_text': processed_article['tts_text'],
                    'raw_description': processed_article.get('raw_description', '')
                })
                
        except Exception as e:
            print(f"⚠️ Failed to process Urdu RSS feed {feed_url}: {e}")
            continue
    
    return articles


def filter_pakistani_news(articles):
    """Filter articles to keep only Pakistani news"""
    filtered = []
    
    for art in articles:
        text = (art.get('title', '') + " " + art.get('description', '')).lower()
        
        # Check if contains Pakistani keywords
        if any(keyword in text for keyword in PAKISTANI_KEYWORDS_URDU):
            filtered.append(art)
        # Also keep if category indicates Pakistani news
        elif art.get('source', '').lower() in ['bbc urdu', 'express news', 'geo news']:
            filtered.append(art)
    
    print(f"📋 Filtered: {len(filtered)}/{len(articles)} Pakistani articles")
    return filtered


def process_urdu_news(category):
    """
    UPDATED - Main function to process Urdu news with Groq LLM integration
    """
    print(f"\n{'='*80}")
    print(f"📰 PROCESSING URDU NEWS - Category: {category}")
    print(f"{'='*80}")
    
    # Check LLM availability
    llm = get_llm_processor()
    if llm:
        print("✅ Groq LLM available for Urdu - high quality processing enabled")
    else:
        print("⚠️ Groq LLM not available for Urdu - using basic processing")
    
    try:
        # Harvest RSS feeds
        print("\n📡 Fetching from Urdu RSS feeds...")
        articles = harvest_rss_feeds(category)
        print(f"✅ RSS: {len(articles)} Urdu articles fetched")
        
        # Filter Pakistani news
        articles = filter_pakistani_news(articles)
        
        # Deduplicate
        seen = set()
        final_articles = []
        for article in articles:
            title_key = article['title']
            if title_key not in seen:
                seen.add(title_key)
                final_articles.append(article)
        
        result = final_articles[:Config.MAX_ARTICLES_PER_CATEGORY]
        
        print(f"\n✅ Final: {len(result)} unique Urdu articles ready")
        print(f"{'='*80}\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Failed to process Urdu news: {e}")
        import traceback
        traceback.print_exc()
        return []