# app.py
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
    <h4 style="margin-top:0;">🤗 Hugging Face Spaces Deployment</h4>
    <ul style="margin-bottom:0;">
    <li><strong>Wav2Lip:</strong> Model downloads automatically on first run (~430MB).</li>
    <li><strong>Memory:</strong> Processing requires ~1GB RAM.</li>
    <li><strong>Limit:</strong> Keep summaries under 4000 chars for stable generation.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

def show_debug_panel(article, language):
    """Show what text is actually being sent to TTS + LLM processing steps"""
    tts_text = article.get('tts_text', '')
    
    with st.expander("🔍 DEBUG: Text Processing Pipeline", expanded=False):
        # Step 1: Original RSS text
        st.write("### Step 1️⃣: Original RSS Feed Text")
        raw_desc = article.get('raw_description', 'N/A')
        st.text_area("Raw from RSS:", raw_desc[:300], height=100)
        
        # Step 2: After LLM cleaning
        st.write("### Step 2️⃣: After LLM Cleaning + Summarization")
        cleaned_desc = article.get('description', 'N/A')
        st.text_area("LLM cleaned:", cleaned_desc[:300], height=100)
        
        # Step 3: Final TTS text
        st.write("### Step 3️⃣: Final TTS Text (with SSML)")
        st.text_area("Sent to TTS engine:", tts_text[:500], height=150)
        
        st.divider()
        
        # Analysis
        st.write("**Text Length:**", len(tts_text), "characters")
        
        # Show raw text with hidden characters visible
        st.write("**Raw Representation (first 300 chars):**")
        st.code(repr(tts_text[:300]), language="python")
        
        # Character analysis
        st.write("**Character Analysis:**")
        special_chars = {}
        for char in tts_text:
            if ord(char) > 127 or char in '—–""''…':
                special_chars[char] = special_chars.get(char, 0) + 1
        
        if special_chars:
            st.warning(f"⚠️ Found {len(special_chars)} types of special characters:")
            for char, count in list(special_chars.items())[:10]:
                st.write(f"  • `{char}` (U+{ord(char):04X}) - appears {count} times")
        else:
            st.success("✅ No problematic special characters found!")
        
        # Check for SSML tags
        if '<' in tts_text or '>' in tts_text:
            if language == 'en':
                st.success("✅ SSML tags present (correct for English/Edge TTS)")
            else:
                st.error("❌ SSML tags found in Urdu text (will cause gTTS to fail!)")
            
            tags = [tag for tag in tts_text.split('<') if '>' in tag]
            st.write(f"**SSML Tags Found:** {len(tags)} tags")
            if st.checkbox("Show SSML tag details", key="ssml_details"):
                st.json(tags)
        else:
            if language == 'ur':
                st.success("✅ No SSML tags (correct for Urdu/gTTS)")
            else:
                st.warning("⚠️ No SSML tags in English text")
        
        # Punctuation check
        punct_count = sum(1 for c in tts_text if c in '—–""''…•·●')
        if punct_count > 0:
            st.error(f"❌ Found {punct_count} special punctuation marks that might be spoken!")
        else:
            st.success("✅ No problematic punctuation found")

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

        # DEBUG MODE TOGGLE
        debug_mode = st.checkbox("🔧 Debug Mode (Show TTS text analysis)", value=False)
        
        # LLM CLEANING TOGGLE
        use_llm = st.checkbox("🤖 Use LLM Text Cleaning (slower but better quality)", value=True)
        if use_llm:
            st.caption("⏱️ Adds ~2-3 seconds per article for better quality")
        
        # Store in session state for access in processing functions
        st.session_state['use_llm_cleaning'] = use_llm

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
            
            # --- Video Generation Section ---
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
                
                # SHOW DEBUG PANEL IF ENABLED
                if debug_mode:
                    show_debug_panel(selected_article, lang_code)
                
                # =================================================================
                # IMPROVED VIDEO GENERATION LOGIC WITH DEBUGGING
                # =================================================================
                if st.button("🎥 Generate Video", type="primary", use_container_width=True):
                    try:
                        print("\n" + "="*80)
                        print("🎬 VIDEO GENERATION STARTED")
                        print("="*80)
                        
                        # Check if model exists, download if necessary
                        if not os.path.exists("Wav2Lip/checkpoints/wav2lip_gan.pth"):
                            st.info("📥 Downloading Wav2Lip model... This may take several minutes")
                            with st.spinner("Downloading model..."):
                                if not ensure_wav2lip_model():
                                    st.error("Failed to download required model. Please try again later.")
                                    st.stop()

                        # Validate other requirements
                        if not validate_video_requirements():
                            st.error("Please check video requirements in the sidebar")
                            st.stop()

                        # Check text content
                        tts_text = selected_article.get('tts_text', '')
                        print(f"📝 Article text length: {len(tts_text)} chars")
                        print(f"📝 Text preview: {tts_text[:200]}...")
                        
                        if not tts_text or len(tts_text) < Config.MIN_ARTICLE_LENGTH:
                            st.error(f"Article text too short ({len(tts_text)} chars, min {Config.MIN_ARTICLE_LENGTH})")
                            print(f"❌ Text validation failed: {len(tts_text)} < {Config.MIN_ARTICLE_LENGTH}")
                            st.stop()

                        # Create progress containers
                        audio_progress = st.empty()
                        audio_status = st.empty()
                        video_progress = st.empty()
                        video_status = st.empty()

                        # Step 1: Generate audio
                        print("\n" + "-"*80)
                        print("STEP 1: AUDIO GENERATION")
                        print("-"*80)
                        
                        audio_status.info("🎙️ Step 1/2: Generating audio...")
                        audio_bar = audio_progress.progress(0)
                        
                        # Submit audio generation task
                        print(f"📤 Submitting TTS task: lang={lang_code}, text_len={len(tts_text)}")
                        task_id = generate_audio(tts_text, "Male", lang_code)

                        if not task_id:
                            error_msg = "Failed to submit audio generation task"
                            print(f"❌ {error_msg}")
                            audio_status.error(f"❌ {error_msg}")
                            st.stop()
                        
                        print(f"✅ Task submitted: {task_id}")

                        # Wait for audio with progress updates
                        audio_path = None
                        start_time = time.time()
                        timeout = 60
                        check_count = 0
                        
                        while time.time() - start_time < timeout:
                            check_count += 1
                            elapsed = time.time() - start_time
                            status = async_processor.get_task_status(task_id)
                            
                            # Update progress bar
                            progress = min(int((elapsed / timeout) * 90), 90)
                            audio_bar.progress(progress)
                            
                            # Log periodic status
                            if check_count % 10 == 0:  # Every 5 seconds
                                print(f"⏳ [{elapsed:.1f}s] Audio status: {status.get('status')} (check #{check_count})")
                            
                            if status['status'] == 'completed':
                                result = status.get('result', {})
                                print(f"✅ Task completed. Result: {result}")
                                
                                if result.get('success'):
                                    audio_path = result.get('result')
                                    print(f"📁 Audio path: {audio_path}")
                                    
                                    if audio_path and os.path.exists(audio_path):
                                        file_size = os.path.getsize(audio_path)
                                        print(f"✅ Audio file verified: {audio_path} ({file_size} bytes)")
                                        audio_bar.progress(100)
                                        audio_status.success(f"✅ Audio generated: {os.path.basename(audio_path)} ({file_size} bytes)")
                                        break
                                    else:
                                        error_msg = f"Audio file not found: {audio_path}"
                                        print(f"❌ {error_msg}")
                                        audio_status.error(f"❌ {error_msg}")
                                        
                                        # Debug: List files in output directory
                                        output_dir = Config().OUTPUT_DIR / "audio"
                                        if output_dir.exists():
                                            files = list(output_dir.iterdir())
                                            print(f"📂 Files in {output_dir}: {files}")
                                            st.code(f"Files in audio directory: {files}")
                                        
                                        st.stop()
                                else:
                                    error = result.get('error', 'Unknown error')
                                    print(f"❌ Audio generation failed: {error}")
                                    audio_status.error(f"❌ Audio generation failed: {error}")
                                    st.stop()
                                    
                            elif status['status'] == 'failed':
                                error = status.get('result', {}).get('error', 'Unknown error')
                                print(f"❌ Task failed: {error}")
                                audio_status.error(f"❌ Audio generation failed: {error}")
                                
                                # Show full error details
                                st.code(f"Error details: {status.get('result', {})}")
                                st.stop()
                            
                            elif status['status'] == 'not_found':
                                print(f"❌ Task not found: {task_id}")
                                audio_status.error(f"❌ Audio task not found: {task_id}")
                                
                                # Debug: Show all tasks
                                stats = async_processor.get_queue_stats()
                                print(f"📊 Queue stats: {stats}")
                                st.code(f"Queue stats: {stats}")
                                st.stop()
                            
                            elif status['status'] in ('queued', 'processing'):
                                # Task is still running, just wait
                                pass
                            else:
                                print(f"⚠️ Unknown status: {status}")
                                
                            time.sleep(0.5)
                        
                        if not audio_path:
                            elapsed = time.time() - start_time
                            error_msg = f"Audio generation timed out after {elapsed:.1f}s"
                            print(f"⏰ {error_msg}")
                            audio_status.error(f"⏰ {error_msg}")
                            
                            # Show final status
                            final_status = async_processor.get_task_status(task_id)
                            print(f"📊 Final status: {final_status}")
                            st.code(f"Final task status: {final_status}")
                            st.stop()

                        # Step 2: Generate video
                        print("\n" + "-"*80)
                        print("STEP 2: VIDEO GENERATION")
                        print("-"*80)
                        print(f"🎥 Input audio: {audio_path}")
                        print(f"🎥 Avatar mode: {'auto' if auto_avatar else 'custom'}")
                        
                        video_status.info("🎥 Step 2/2: Generating video... This may take several minutes")
                        video_bar = video_progress.progress(0)
                        
                        avatar_input = Config().AUTO_AVATARS.get(lang_code) if auto_avatar else custom_avatar
                        print(f"👤 Avatar input: {avatar_input}")
                        
                        if not avatar_input:
                            error_msg = "No avatar available"
                            print(f"❌ {error_msg}")
                            video_status.error(f"❌ {error_msg}")
                            st.stop()
                        
                        # Verify avatar exists (for auto-generated)
                        if auto_avatar and isinstance(avatar_input, str):
                            if not os.path.exists(avatar_input):
                                error_msg = f"Avatar file not found: {avatar_input}"
                                print(f"❌ {error_msg}")
                                video_status.error(f"❌ {error_msg}")
                                st.stop()
                            print(f"✅ Avatar file verified: {avatar_input}")
                        
                        video_start = time.time()
                        video_path = generate_video(audio_path, avatar_input, lang_code, auto_avatar)
                        video_elapsed = time.time() - video_start
                        
                        print(f"⏱️ Video generation took {video_elapsed:.1f}s")
                        
                        if video_path and os.path.exists(video_path):
                            video_size = os.path.getsize(video_path)
                            print(f"✅ Video generated: {video_path} ({video_size} bytes)")
                            
                            video_bar.progress(100)
                            video_status.success(f"🎉 Video generated successfully! ({video_size} bytes)")
                            
                            # Display the video
                            st.video(video_path)
                            
                            # Offer download
                            with open(video_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Video",
                                    data=f,
                                    file_name=os.path.basename(video_path),
                                    mime="video/mp4"
                                )
                        else:
                            error_msg = f"Video generation failed - output: {video_path}"
                            print(f"❌ {error_msg}")
                            video_status.error(f"❌ {error_msg}")
                            
                            # Debug: Check outputs directory
                            output_dir = Config().OUTPUT_DIR
                            if output_dir.exists():
                                files = list(output_dir.rglob("*"))
                                print(f"📂 Files in outputs: {files}")
                                st.code(f"Files in outputs directory: {files}")

                    except Exception as e:
                        print(f"\n{'='*80}")
                        print(f"💥 VIDEO GENERATION ERROR")
                        print(f"{'='*80}")
                        print(f"Error: {e}")
                        
                        import traceback
                        tb = traceback.format_exc()
                        print(tb)
                        
                        st.error(f"❌ Video generation error: {str(e)}")
                        
                        # Show full traceback in expander
                        with st.expander("🔍 Show detailed error"):
                            st.code(tb)

        else:
            st.info(f"No {language} articles found for {category}. Try another category.")

    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.info("Check your API keys in Space Secrets and internet connectivity.")
        with st.expander("Technical Details"):
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()

# Cleanup
st.cache_data.clear()