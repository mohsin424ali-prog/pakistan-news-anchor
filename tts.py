# tts.py - IMPROVED VERSION (keeps TTS logic here)
import hashlib
import asyncio
import os
import time
import streamlit as st
from gtts import gTTS
import edge_tts
from config import Config
from async_processor import async_processor

async def _generate_urdu_audio(text: str, audio_path: str) -> str:
    """Generate Urdu audio using gTTS"""
    try:
        tts = gTTS(text=text, lang='ur', tld='com.pk', slow=False)
        # Run in thread pool since gTTS save is blocking
        await asyncio.to_thread(tts.save, audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print(f"✅ Urdu audio generated: {audio_path} ({os.path.getsize(audio_path)} bytes)")
            return audio_path
        else:
            raise RuntimeError("gTTS generated empty file")
    except Exception as e:
        print(f"❌ Urdu TTS failed: {e}")
        raise

async def _generate_english_audio(text: str, gender: str, audio_path: str) -> str:
    """Generate English audio using Edge TTS"""
    try:
        # Get voice from config
        voice = Config.TTS_CONFIG['en']['voice']
        if gender.lower() == "female":
            voice = "en-GB-LibbyNeural"
        
        print(f"🎙️ Using Edge TTS voice: {voice}")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print(f"✅ English audio generated: {audio_path} ({os.path.getsize(audio_path)} bytes)")
            return audio_path
        else:
            raise RuntimeError("Edge TTS generated empty file")
    except Exception as e:
        print(f"❌ English TTS failed: {e}")
        raise

async def generate_tts_audio(text: str, gender: str, language: str) -> str:
    """
    ACTUAL TTS GENERATION - Called by async_processor worker thread.
    This is the function that does the real work.
    
    Returns: Path to generated audio file
    """
    # Validate input
    if not text or len(text.strip()) == 0:
        raise ValueError("Cannot generate audio from empty text")
    
    if len(text) < Config.MIN_ARTICLE_LENGTH:
        raise ValueError(f"Text too short for audio generation (min {Config.MIN_ARTICLE_LENGTH} chars, got {len(text)})")
    
    if len(text) > Config.MAX_TTS_LENGTH:
        print(f"⚠️ Text truncated from {len(text)} to {Config.MAX_TTS_LENGTH} chars")
        text = text[:Config.MAX_TTS_LENGTH]
    
    # Generate output path
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    
    # Use Config.OUTPUT_DIR instead of hardcoded path
    config = Config()
    output_dir = config.OUTPUT_DIR / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    audio_path = str(output_dir / f"audio_{language}_{text_hash}_{int(time.time())}.mp3")
    
    print(f"🎙️ Generating audio: lang={language}, len={len(text)}, output={audio_path}")
    
    # Generate audio based on language
    if language == 'ur':
        result = await _generate_urdu_audio(text, audio_path)
    elif language == 'en':
        result = await _generate_english_audio(text, gender, audio_path)
    else:
        raise ValueError(f"Unsupported language: {language}")
    
    # Final validation
    if not result or not os.path.exists(result):
        raise RuntimeError(f"Audio generation failed - file not created at {audio_path}")
    
    file_size = os.path.getsize(result)
    if file_size == 0:
        raise RuntimeError(f"Audio file is empty: {audio_path}")
    
    print(f"✅ Audio generation complete: {result} ({file_size} bytes)")
    return result

def generate_audio(text: str, gender: str, language: str) -> str:
    """
    Submit TTS task to async processor - returns task_id immediately.
    Use get_audio_result(task_id) to wait for completion.
    """
    # Validate input before submitting
    if not text or len(text.strip()) == 0:
        st.error("Cannot generate audio from empty text")
        print("❌ Empty text provided to generate_audio()")
        return None
    
    if len(text) < Config.MIN_ARTICLE_LENGTH:
        st.error(f"Text too short for audio generation (min {Config.MIN_ARTICLE_LENGTH} chars)")
        print(f"❌ Text too short: {len(text)} chars")
        return None
    
    print(f"📤 Submitting TTS task: lang={language}, gender={gender}, text_len={len(text)}")

    # Submit to async processor
    task_id = async_processor.submit_task(
        'tts',
        text=text,
        gender=gender,
        language=language
    )
    
    print(f"✅ TTS task submitted: {task_id}")
    return task_id

def generate_summary_audio(headlines, language):
    """Generate audio summary from headlines - returns task_id"""
    summary_text = "\n".join([
        f"{h['category']} news: {h['text']}"
        for h in headlines
    ])
    
    return generate_audio(summary_text, "Male", language)

def get_audio_result(task_id: str, timeout: int = 60) -> str:
    """
    Wait for audio generation to complete and return the audio file path.
    
    Args:
        task_id: Task ID from generate_audio()
        timeout: Maximum seconds to wait
        
    Returns:
        str: Path to generated audio file, or None if failed
    """
    if not task_id:
        print("❌ No task_id provided to get_audio_result()")
        return None
    
    start_time = time.time()
    last_status = None
    check_count = 0

    print(f"⏳ Waiting for audio task {task_id} (timeout={timeout}s)")

    while time.time() - start_time < timeout:
        check_count += 1
        status = async_processor.get_task_status(task_id)
        
        # Only log status changes to avoid spam
        current_status = status.get('status')
        if current_status != last_status:
            print(f"📊 Audio task {task_id} status change: {last_status} -> {current_status}")
            last_status = current_status

        if status['status'] == 'completed':
            result = status.get('result', {})
            if result.get('success'):
                audio_path = result.get('result')
                if audio_path and os.path.exists(audio_path):
                    file_size = os.path.getsize(audio_path)
                    print(f"✅ Audio ready: {audio_path} ({file_size} bytes)")
                    return audio_path
                else:
                    error_msg = f"Audio task completed but file missing: {audio_path}"
                    print(f"❌ {error_msg}")
                    st.error(error_msg)
                    return None
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Audio generation failed: {error}")
                st.error(f"Audio generation failed: {error}")
                return None
                
        elif status['status'] == 'failed':
            error = status.get('result', {}).get('error', 'Unknown error')
            print(f"❌ Audio task failed: {error}")
            st.error(f"Audio generation failed: {error}")
            return None
        
        elif status['status'] == 'not_found':
            print(f"❌ Audio task not found: {task_id}")
            st.error(f"Audio task not found: {task_id}")
            return None

        # Still processing, wait a bit
        time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f"⏰ Audio generation timed out after {elapsed:.1f}s ({check_count} checks)")
    st.warning(f"Audio generation timed out after {timeout}s")
    return None