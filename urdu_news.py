import feedparser
from datetime import datetime
import hashlib
from newspaper import Article
from config import Config
from utils import sanitize_html, prepare_for_tts, smart_truncate, format_headline, format_description

# Update PAKISTANI_KEYWORDS_URDU in urdu_news.py
PAKISTANI_KEYWORDS_URDU = [
    'پاکستان', 'اسلام آباد', 'کراچی', 'لاہور',
    'پنجاب', 'سندھ', 'خیبر', 'وفاق', 'حکومت'
]
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

def unified_article_processing(raw_title, raw_description, article_url=None, category="general"):
    if article_url:
        full_text = extract_full_article(article_url)
        raw_content = full_text if full_text else raw_description
    else:
        raw_content = raw_description
    
    processed_title = sanitize_html(raw_title)
    sanitized_content = sanitize_html(raw_content)
    enhanced_content = sanitized_content
    
    return {
        'raw_title': raw_title,
        'title': format_headline(processed_title, 'ur'),
        'description': format_description(enhanced_content, 'ur'),
        'source': 'نامعلوم',
        'publishedAt': 'N/A',
        'category': category,
        'tts_text': prepare_for_tts(f"{processed_title}. {enhanced_content}", 'ur', Config.MAX_DESCRIPTION_LENGTH)
    }

def harvest_rss_feeds(category):
    articles = []
    feeds = Config.URDU_RSS_FEEDS.get(category, [])
    
    for feed_url in feeds:
        try:
            parsed_feed = feedparser.parse(feed_url)
            if not hasattr(parsed_feed, 'entries'):
                continue

            for entry in parsed_feed.entries[:20]:
                if not entry.get('title'):
                    continue

                # Handle publication date
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_date = datetime(*entry.updated_parsed[:6])
                
                processed_article = unified_article_processing(
                    entry.get('title', ''), 
                    entry.get('description', ''), 
                    entry.get('link'), 
                    category
                )

                articles.append({
                    'title': processed_article['title'],
                    'description': processed_article['description'],
                    'source': parsed_feed.feed.get('title', 'RSS Feed'),
                    'publishedAt': pub_date.strftime('%Y-%m-%d %H:%M') if pub_date else 'حالیہ',
                    'category': category,
                    'tts_text': processed_article['tts_text']
                })
        except Exception as e:
            continue
            
    return articles

def filter_pakistani_news(articles):
    filtered = []
    for art in articles:
        text = (art.get('title', '') + " " + art.get('description', '')).lower()
        if any(keyword in text for keyword in PAKISTANI_KEYWORDS_URDU):
            filtered.append(art)
    return filtered

def process_urdu_news(category):
    try:
        articles = harvest_rss_feeds(category)
        articles = filter_pakistani_news(articles)
        return articles[:Config.MAX_ARTICLES_PER_CATEGORY]
    except Exception as e:
        return []