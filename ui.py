# ui.py
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Force CPU mode
import streamlit as st
from config import Config

def setup_ui():
    """Initialize Streamlit UI configuration"""
    # Set page config with proper theme
    st.set_page_config(
        page_title="Pakistan News Anchor",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Set theme to use standard fonts that are always available
    st.markdown("""
    <style>
    /* Use standard system fonts that are always available */
    :root {
        --primary-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        --secondary-font: Georgia, "Times New Roman", serif;
    }

    body {
        font-family: var(--primary-font);
        background: #f8f9fa;
        margin: 0;
        color: #333;
    }

    .header-banner {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a237e;
        text-align: center;
        padding: 1.5rem 0;
        border-bottom: 2px solid #eee;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .category-header {
        font-size: 1.4rem;
        color: #2c3e50;
        border-left: 4px solid #3498db;
        padding-left: 1rem;
        margin: 2rem 0 1rem;
        font-weight: 600;
        background: white;
        padding: 10px 20px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .news-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 1.2rem;
        padding: 1rem 0;
    }

    .news-card {
        background: white;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.2s, box-shadow 0.2s;
        border: 1px solid #f0f0f0;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
    }

    .news-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .source-tag {
        font-size: 0.8rem;
        background: #f0f0f0;
        padding: 4px 12px;
        border-radius: 15px;
        display: inline-block;
        font-weight: 500;
        color: #666;
        border: 1px solid #ddd;
    }

    .category-chip {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 12px;
        text-transform: uppercase;
        color: white;
        font-family: var(--primary-font);
    }

    .urdu-card {
        direction: rtl;
        font-family: "Noto Naskh Urdu", Arial, sans-serif;
        font-size: 1.1rem;
        line-height: 1.8;
        text-align: right;
    }

    /* Category colors */
    .category-general { background-color: #4CAF50; }
    .category-business { background-color: #2196F3; }
    .category-sports { background-color: #FF5722; }
    .category-technology { background-color: #9C27B0; }

    @media (max-width: 768px) {
        .news-grid { grid-template-columns: 1fr; }
        .header-banner { font-size: 2rem; padding: 1rem 0; }
        .news-card { margin: 0 10px; }
        .header-banner { font-size: 1.8rem; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header-banner">📰 Pakistan News Anchor</div>', unsafe_allow_html=True)

def display_category_section(category, articles):
    """Render a category section"""
    if articles:
        st.markdown(f'<div class="category-header">{category.capitalize()} News</div>', unsafe_allow_html=True)
        st.markdown('<div class="news-grid">', unsafe_allow_html=True)
        for article in articles:
            display_article_card(article, category)
        st.markdown('</div>', unsafe_allow_html=True)

def display_article_card(article: dict, category: str = "general"):
    category_colors = {
        'general': '#4CAF50',
        'business': '#2196F3',
        'sports': '#FF5722',
        'technology': '#9C27B0'
    }
    formatted_desc = article['description'].replace('\n', '<br>')
    card_html = f"""
    <div class="news-card">
        <div class="category-chip" style="background:{category_colors[category]};color:white">
            {category.upper()}
        </div>
        <h4 style="margin:0 0 10px 0; font-size:1.1rem; line-height:1.3">{article['title']}</h4>
        <p style="color:#555; font-size:0.95rem; margin-bottom:12px; line-height:1.4">{formatted_desc}</p>
        <div style="display:flex; justify-content:space-between; align-items:center">
            <span class="source-tag">{article['source']}</span>
            <span style="color:#888; font-size:0.85rem">{article['publishedAt']}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def display_urdu_article_card(article: dict, category: str = "general"):
    category_colors = {
        'general': '#4CAF50',
        'business': '#2196F3',
        'sports': '#FF5722',
        'technology': '#9C27B0'
    }
    formatted_desc = article['description'].replace('\n', '<br>')
    card_html = f"""
    <div class="news-card urdu-card">
        <div class="category-chip" style="background:{category_colors[category]};color:white">
            {category.upper()}
        </div>
        <h4 style="margin:0 0 10px 0; line-height:1.4">{article['title']}</h4>
        <p style="color:#555; line-height:1.6">{formatted_desc}</p>
        <div style="display:flex; justify-content:space-between; font-size:0.9rem;">
            <span class="source-tag">{article.get('source','ماخذ نامعلوم')}</span>
            <span style="color:#888;">{article['publishedAt']}</span>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)