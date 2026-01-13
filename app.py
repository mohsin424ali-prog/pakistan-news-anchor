import streamlit as st
import sys
import os
import time
import asyncio
import traceback
import tempfile
from pathlib import Path

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from ui import setup_ui, display_category_section, display_article_card, display_urdu_article_card
from english_news import process_english_news
from urdu_news import process_urdu_news
from config import Config
from video import generate_video, validate_video_requirements, ensure_wav2lip_model
from tts import generate_audio
from cache_manager import get_cache_status
from async_processor import async_processor 

def show_hugging_face_info():
    """Show Hugging Face specific information"""
    st.markdown("""
    <div style="background: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;">
    <h4 style="margin-top:0;">🤖 Hugging Face Spaces Deployment</h4>
    <ul style="margin-bottom:0;">
    <li><strong>Wav2Lip:</strong> Model downloads automatically on first run (~430MB).</li>
    <li><strong>Memory:</strong> Processing requires ~1GB RAM.</li>
    <li><strong>Limit:</strong> Keep summaries under 4000 chars for stable generation.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    # Initialize async processor
    async_processor.start()

    setup_ui()
    show_hugging_face_info()

    # Sidebar configuration
    with st.sidebar:
        st.title("📰 News Anchor Settings")

        language = st.selectbox("Language", ["English", "Urdu"], key="lang_select")
        category = st.selectbox(
            "News Category",
            ["general", "business", "sports", "technology"],
            key="category_select"
        )

        st.divider()

        # Cache information
        cache_status = get_cache_status()
        st.metric("Cache Status", f"{cache_status['valid_entries']} items")
        st.metric("Storage Used", f"{cache_status['total_size_mb']} MB")

        st.divider()

        st.subheader("🎬 Video Options")
        auto_avatar = st.checkbox("Use Auto-Generated Avatar", value=True, key="auto_avatar")

        custom_avatar = None
        if not auto_avatar:
            custom_avatar = st.file_uploader(
                "Upload Custom Avatar",
                type=["png", "jpg", "jpeg"]
            )

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("🧹 Clear", type="secondary", use_container_width=True):
                from cache_manager import clear_cache
                clear_cache()
                st.rerun()

    # Main logic
    lang_code = "en" if language == "English" else "ur"

    try:
        with st.spinner(f"📡 Loading {language} {category} news..."):
            if lang_code == "en":
                articles = process_english_news(category)
            else:
                articles = process_urdu_news(category)

        if articles:
            # Displaying cards (UI likely uses expanders here)
            display_category_section(category, articles)

            st.divider()
            
            # --- FIXED SECTION: Container instead of nested expander ---
            st.subheader("🎥 Create Video Broadcast")
            with st.container(border=True):
                col_sel, col_btn = st.columns([3, 1])
                
                article_titles = [f"{i+1}. {a['title'][:60]}..." for i, a in enumerate(articles)]
                
                with col_sel:
                    selected_article_idx = st.selectbox(
                        "Select an article to turn into video:",
                        range(len(articles)),
                        format_func=lambda x: article_titles[x]
                    )
                
                selected_article = articles[selected_article_idx]
                
                if st.button("🚀 Generate Video", type="primary", use_container_width=True):
                    try:
                        # 1. Validation
                        if not os.path.exists("Wav2Lip/checkpoints/wav2lip_gan.pth"):
                            with st.status("📥 First-time setup: Downloading Wav2Lip model..."):
                                if not ensure_wav2lip_model():
                                    st.error("Model download failed. Check internet.")
                                    st.stop()

                        tts_text = selected_article.get('tts_text', '')
                        if not tts_text or len(tts_text) < 10:
                            st.error("Article content too short for processing.")
                            st.stop()

                        # 2. Status UI
                        status_box = st.empty()
                        prog_bar = st.progress(5)

                        # 3. Step 1: Audio Generation (Async Polling)
                        status_box.info("🎙️ Step 1/2: Generating AI Voice...")
                        
                        # Fix: Calling generate_audio directly (returns string task_id)
                        task_id = generate_audio(tts_text, "Male", lang_code)
                        
                        audio_path = None
                        start_wait = time.time()
                        
                        # Wait for async processor to finish TTS
                        while time.time() - start_wait < 90:
                            status = async_processor.get_task_status(task_id)
                            
                            if status['status'] == 'completed':
                                result_data = status.get('result', {})
                                if result_data.get('success'):
                                    audio_path = result_data.get('result')
                                    break
                            elif status['status'] == 'failed':
                                st.error(f"Audio Error: {status.get('result', {}).get('error')}")
                                st.stop()
                            
                            time.sleep(1)
                            prog_bar.progress(min(30, int((time.time() - start_wait))))

                        if not audio_path or not os.path.exists(audio_path):
                            st.error("Audio generation timed out.")
                            st.stop()

                        # 4. Step 2: Video Generation
                        status_box.info("🎬 Step 2/2: Lip-Syncing Video (This takes 1-2 minutes)...")
                        prog_bar.progress(40)
                        
                        avatar_source = Config().AUTO_AVATARS.get(lang_code) if auto_avatar else custom_avatar
                        
                        # generate_video is a blocking call (subprocess)
                        final_video_path = generate_video(audio_path, avatar_source, lang_code, auto_avatar)
                        
                        if final_video_path and os.path.exists(final_video_path):
                            prog_bar.progress(100)
                            status_box.success("✅ Broadcast Video Generated Successfully!")
                            st.video(final_video_path)
                            
                            with open(final_video_path, 'rb') as f:
                                st.download_button(
                                    "📥 Download News Broadcast",
                                    f,
                                    file_name=f"news_{lang_code}_{int(time.time())}.mp4",
                                    mime="video/mp4"
                                )
                        else:
                            st.error("Video rendering failed. Check logs for subprocess errors.")

                    except Exception as ve:
                        st.error(f"Video Generation Error: {str(ve)}")
                        with st.expander("Technical Traceback"):
                            st.code(traceback.format_exc())

        else:
            st.info(f"No {language} articles found for {category}. Try another category.")

    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.info("Check your API keys in Space Secrets and internet connectivity.")

if __name__ == "__main__":
    main()

# Cleanup
st.cache_data.clear()