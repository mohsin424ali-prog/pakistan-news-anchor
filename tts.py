import hashlib
import asyncio
import os
import time
import re
import streamlit as st
from gtts import gTTS
import edge_tts
from config import Config
from async_processor import async_processor
from pathlib import Path

def strip_ssml_tags(text):
    """Remove all SSML/XML tags from text (critical for gTTS)"""
    if not text:
        return ""
    # Remove all XML/SSML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

async def _generate_urdu_audio(text: str, audio_path: str) -> str:
    """
    Generate Urdu audio using gTTS (blocking save wrapped in thread)
    CRITICAL: gTTS does NOT support SSML - must use plain text only
    """
    try:
        # CRITICAL FIX: Strip ALL SSML tags before sending to gTTS
        clean_text = strip_ssml_tags(text)
        
        # Remove any remaining special characters that might be spoken
        clean_text = re.sub(r'[<>{}[\]\\|`~]', '', clean_text)
        
        if not clean_text or len(clean_text) < 5:
            raise ValueError("Text too short after cleaning")
        
        print(f"🎤 Urdu gTTS Input (cleaned): {clean_text[:100]}...")
        
        tts = gTTS(text=clean_text, lang='ur', tld='com.pk', slow=False)
        # gTTS .save() is a blocking I/O operation
        await asyncio.to_thread(tts.save, audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print(f"✅ Urdu audio generated: {audio_path}")
            return audio_path
        raise RuntimeError("gTTS generated an empty or invalid file")
    except Exception as e:
        print(f"❌ Urdu TTS Error: {e}")
        raise

async def _generate_english_audio(text: str, gender: str, audio_path: str) -> str:
    """
    Generate English audio using Edge TTS (Native Async)
    Edge TTS supports SSML properly
    """
    try:
        # Edge TTS handles SSML, but let's ensure it's properly formatted
        # If text doesn't start with <speak>, it's treated as plain text
        if not text.startswith('<speak>'):
            # Plain text - Edge TTS will handle it naturally
            clean_text = strip_ssml_tags(text)
            final_text = clean_text
        else:
            # SSML text - use as is
            final_text = text
        
        print(f"🎤 English Edge TTS Input: {final_text[:100]}...")
        
        # Default voice from Config
        voice = Config.TTS_CONFIG['en']['voice']
        if gender.lower() == "female":
            voice = "en-GB-LibbyNeural"  # British Female
        
        communicate = edge_tts.Communicate(final_text, voice)
        await communicate.save(audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            print(f"✅ English audio generated: {audio_path}")
            return audio_path
        raise RuntimeError("Edge TTS generated an empty file")
    except Exception as e:
        print(f"❌ English TTS Error: {e}")
        raise

async def generate_tts_audio(text: str, gender: str, language: str) -> str:
    """
    CORE WORKER FUNCTION: Called by async_processor.
    Processes the actual text-to-speech conversion.
    """
    if not text or len(text.strip()) == 0:
        raise ValueError("Text content is empty")
    
    # Enforce limits
    if len(text) > Config.MAX_TTS_LENGTH:
        text = text[:Config.MAX_TTS_LENGTH]
    
    # File Naming Logic
    text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
    output_dir = Path(Config().OUTPUT_DIR) / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use .mp3 for both engines
    audio_filename = f"{language}_{text_hash}_{int(time.time())}.mp3"
    audio_path = str(output_dir / audio_filename)
    
    print(f"🎙️ TTS Task Started | Lang: {language} | Text length: {len(text)} chars")
    
    if language == 'ur':
        result = await _generate_urdu_audio(text, audio_path)
    elif language == 'en':
        result = await _generate_english_audio(text, gender, audio_path)
    else:
        raise ValueError(f"Language '{language}' not supported")
    
    return result

def generate_audio(text: str, gender: str, language: str) -> str:
    """
    UI ENTRY POINT: Submits task and returns ID.
    Returns: String (task_id) or None
    """
    if not text or len(text.strip()) < 5:
        print("⚠️ TTS Rejected: Text too short.")
        return None

    # Submit the 'tts' task type defined in async_processor
    task_id = async_processor.submit_task(
        'tts',
        text=text,
        gender=gender,
        language=language
    )
    
    print(f"✅ TTS Queued | Task ID: {task_id}")
    return task_id

def get_audio_result(task_id: str, timeout: int = 60) -> str:
    """
    POLLING FUNCTION: Synchronously waits for the async task to finish.
    Useful for the Streamlit UI 'Generate' button.
    """
    if not task_id: return None
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_info = async_processor.get_task_status(task_id)
        status = status_info.get('status')
        
        if status == 'completed':
            res = status_info.get('result', {})
            if res.get('success'):
                path = res.get('result')
                if os.path.exists(path):
                    return path
            break
        elif status == 'failed':
            print(f"❌ Task {task_id} failed.")
            break
            
        time.sleep(1)  # Poll every second
        
    return None