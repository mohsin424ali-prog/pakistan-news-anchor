import streamlit as st
from ui import setup_ui, display_category_section, display_article_card, display_urdu_article_card
from english_news import process_english_news
from urdu_news import process_urdu_news
from config import Config
from video import generate_video, validate_video_requirements
from tts import generate_summary_audio, generate_audio
from cache_manager import get_cache_status
from async_processor import async_processor, ProgressTracker
import asyncio
import tempfile
import os
import time

# Note: async_processor.start() moved to main() function to prevent initialization order issues

def show_hugging_face_info():
    """Show Hugging Face specific information"""
    st.markdown("""
    <div style="background: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
    <h4>🤖 Hugging Face Spaces Deployment</h4>
    <ul>
    <li><strong>Model Downloads:</strong> Wav2Lip model will be downloaded on first use</li>
    <li><strong>API Keys:</strong> Set NEWS_API_KEY and HUGGINGFACE_API_KEY in Space Secrets for enhanced features</li>
    <li><strong>Memory:</strong> Video generation requires ~1GB memory</li>
    <li><strong>Timeouts:</strong> Long videos may timeout - keep audio under 60 seconds</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application entry point"""
    # Initialize async processor
    async_processor.start()

    setup_ui()

    # Show Hugging Face specific info
    show_hugging_face_info()

    # Sidebar configuration
    with st.sidebar:
        st.title("📰 News Anchor Settings")

        # Language and category selection
        language = st.selectbox("Language", ["English", "Urdu"], key="lang_select")
        category = st.selectbox(
            "News Category",
            ["general", "business", "sports", "technology"],
            key="category_select"
        )

        st.divider()

        # Cache information
        cache_status = get_cache_status()
        st.metric("Cache Status", f"{cache_status['valid_entries']} valid entries")
        st.metric("Cache Size", f"{cache_status['total_size_mb']} MB")

        st.divider()

        # Video options
        st.subheader("🎬 Video Options")
        auto_avatar = st.checkbox("Use Auto-Generated Avatar", value=True, key="auto_avatar")

        custom_avatar = None
        if not auto_avatar:
            custom_avatar = st.file_uploader(
                "Upload Custom Avatar",
                type=["png", "jpg", "jpeg"],
                help="Maximum file size: 5MB"
            )

        st.divider()

        # Actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh News", type="primary", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        with col2:
            if st.button("🧹 Clear Cache", type="secondary", use_container_width=True):
                from cache_manager import clear_cache
                clear_cache()
                st.rerun()

    # Main content area
    lang_code = "en" if language == "English" else "ur"

    try:
        with st.spinner("📡 Fetching news content..."):
            if lang_code == "en":
                articles = process_english_news(category)
            else:
                articles = process_urdu_news(category)

        if articles:
            display_category_section(category, articles)

            # Generate audio and video options
            with st.expander("🎬 Generate News Broadcast", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    article_titles = [f"{i+1}. {article['title'][:50]}..." for i, article in enumerate(articles)]
                    selected_article_idx = st.selectbox(
                        "Select Article",
                        range(len(articles)),
                        format_func=lambda x: article_titles[x],
                        key=f"article_select_{lang_code}_{category}"
                    )
                    selected_article = articles[selected_article_idx]

                with col2:
                    # Audio generation
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        audio_btn = st.button("🎙️ Generate Audio", type="primary", use_container_width=True)

                    with col_a2:
                        if st.button("📋 View Script", type="secondary", use_container_width=True):
                            st.text_area("News Script", selected_article['tts_text'], height=150)

                    if audio_btn:
                        with st.spinner("Generating audio..."):
                            try:
                                task_id = asyncio.run(generate_audio(
                                    selected_article['tts_text'],
                                    "Male",
                                    lang_code
                                ))

                                if task_id:
                                    st.success(f"Audio generation started! Task ID: {task_id}")
                                    st.session_state.current_audio_task = task_id
                                else:
                                    st.error("Failed to start audio generation")
                            except Exception as e:
                                st.error(f"Audio generation failed: {str(e)}")

                    # Audio result display
                    if hasattr(st.session_state, 'current_audio_task'):
                        task_id = st.session_state.current_audio_task
                        status = async_processor.get_task_status(task_id)

                        if status['status'] == 'completed':
                            audio_path = status.get('result', {}).get('result')
                            if audio_path and os.path.exists(audio_path):
                                st.audio(audio_path)
                                st.success("Audio generated successfully!")
                            else:
                                st.warning("Audio task completed but file not found")
                        elif status['status'] == 'failed':
                            st.error(f"Audio generation failed: {status.get('result', {}).get('error')}")
                        else:
                            st.info(f"Audio generation in progress... ({status['status']})")

                    st.divider()

                    # Video generation
                    if st.button("🎥 Generate Video", type="secondary", use_container_width=True):
                        # Check if model exists, download if necessary
                        if not os.path.exists("Wav2Lip/checkpoints/wav2lip_gan.pth"):
                            with st.spinner("Downloading Wav2Lip model... This may take several minutes"):
                                if not ensure_wav2lip_model():
                                    st.error("Failed to download required model. Please try again later.")
                                    st.stop()

                        # Validate other requirements
                        if not validate_video_requirements():
                            st.error("Please check video requirements in the sidebar")
                        else:
                            audio_path = None
                            if hasattr(st.session_state, 'current_audio_task'):
                                task_status = async_processor.get_task_status(st.session_state.current_audio_task)
                                if task_status['status'] == 'completed':
                                    audio_path = task_status.get('result', {}).get('result')

                            if not audio_path:
                                st.warning("Please generate audio first")
                            else:
                                with st.spinner("Generating video... This may take a few minutes"):
                                    try:
                                        avatar_input = Config().AUTO_AVATARS.get(lang_code) if auto_avatar else custom_avatar
                                        video_path = generate_video(audio_path, avatar_input, lang_code, auto_avatar)

                                        if video_path:
                                            st.success("Video generated successfully!")
                                            st.video(video_path)
                                        else:
                                            st.error("Failed to generate video")
                                    except Exception as e:
                                        st.error(f"Video generation failed: {str(e)}")

        else:
            st.info(f"📭 No {language} news available for {category} at this time. Try selecting a different category or language.")

    except Exception as e:
        st.error(f"❌ Error loading news: {str(e)}")
        st.info("Please check your internet connection and API keys.")

if __name__ == "__main__":
    main()

# Cleanup on app exit
st.cache_data.clear()