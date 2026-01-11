# english_news.py
import streamlit as st
import feedparser
from datetime import datetime, timedelta
import json
import hashlib
from newsapi import NewsApiClient
from newspaper import Article
from config import Config
from utils import sanitize_html, prepare_for_tts, smart_truncate, format_headline, format_description

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

def enhance_content(text):
    if not text or len(text) < 50:
        return text
    try:
        import requests
        headers = {"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"}
        payload = {"inputs": text, "parameters": {"max_length": 100, "min_length": 30, "do_sample": False}}
        response = requests.post(Config.SUMMARIZATION_API, headers=headers, json=payload)
        summary = json.loads(response.content.decode("utf-8"))
        if isinstance(summary, list) and "summary_text" in summary[0]:
            return summary[0]["summary_text"]
        else:
            return text
    except Exception as e:
        return text

def unified_article_processing(raw_title, raw_description, article_url=None, category="general"):
    if article_url:
        full_text = extract_full_article(article_url)
        raw_content = full_text if full_text else raw_description
    else:
        raw_content = raw_description
    
    processed_title = sanitize_html(raw_title)
    sanitized_content = sanitize_html(raw_content)
    enhanced_content = enhance_content(sanitized_content) if len(sanitized_content) > 50 else sanitized_content
    enhanced_content = " ".join(enhanced_content.split())
    
    return {
        'raw_title': raw_title,
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
            'tts_text': processed_article['tts_text']
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
                    'tts_text': processed_article['tts_text']
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