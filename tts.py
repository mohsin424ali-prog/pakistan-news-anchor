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
import re
import html

def _strip_ssml(text: str) -> str:
    """Remove SSML tags from text, leaving only the content"""
    # Remove all XML/SSML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def _validate_and_clean_ssml(text: str) -> str:
    """Validate and clean SSML to ensure it's properly formatted"""
    try:
        # Ensure text starts and ends with speak tags
        if not text.strip().startswith('<speak>'):
            text = '<speak>' + text
        if not text.strip().endswith('</speak>'):
            text = text + '</speak>'
        
        # Fix common SSML issues
        # 1. Ensure all quotes are straight quotes (U+0022), not curly
        text = text.replace('"', '"').replace('"', '"')  # curly to straight
        text = text.replace(''', "'").replace(''', "'")  # curly to straight
        
        # 2. Ensure break tags are self-closing
        text = re.sub(r'<break([^/>]+)>', r'<break\1/>', text)
        
        # 3. Remove any invalid characters
        # Keep only printable ASCII and common punctuation
        text = ''.join(char for char in text if ord(char) < 127 or char in 'áéíóúÁÉÍÓÚñÑ')
        
        # 4. Validate time attributes
        text = re.sub(r'time="(\d+)(ms|s)"', lambda m: f'time="{m.group(1)}{m.group(2)}"', text)
        
        return text
    except Exception as e:
        print(f"⚠️ SSML validation error: {e}")
        # If validation fails, strip SSML entirely
        return _strip_ssml(text)

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
    """Generate English audio using Edge TTS with proper SSML handling"""
    try:
        # Get voice from config
        voice = Config.TTS_CONFIG['en']['voice']
        if gender.lower() == "female":
            voice = "en-GB-LibbyNeural"
        
        print(f"🎙️ Using Edge TTS voice: {voice}")
        print(f"📝 Text length: {len(text)} chars")
        print(f"📝 First 100 chars: {text[:100]}")
        
        # Check if text contains SSML
        is_ssml = text.strip().startswith('<speak>')
        print(f"🏷️ SSML detected: {is_ssml}")
        
        if is_ssml:
            # Validate and clean SSML
            text = _validate_and_clean_ssml(text)
            print(f"✅ SSML validated and cleaned")
        
        # Edge TTS automatically detects SSML if text starts with <speak>
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)
        
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            file_size = os.path.getsize(audio_path)
            print(f"✅ English audio generated: {audio_path} ({file_size} bytes)")
            
            # Validate the audio file is actually playable
            if file_size < 1000:
                print(f"⚠️ Audio file suspiciously small ({file_size} bytes)")
            
            return audio_path
        else:
            raise RuntimeError("Edge TTS generated empty file")
            
    except Exception as e:
        print(f"❌ English TTS failed: {e}")
        print(f"   Text causing error: {text[:200]}...")
        
        # If SSML fails, try stripping it and using plain text
        if '<speak>' in text:
            print("🔄 Retrying with plain text (SSML stripped)...")
            plain_text = _strip_ssml(text)
            print(f"   Plain text length: {len(plain_text)}")
            
            try:
                communicate = edge_tts.Communicate(plain_text, voice)
                await communicate.save(audio_path)
                
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    print(f"✅ Fallback successful with plain text")
                    return audio_path
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
        
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
    
    # Additional validation: Check if file is actually audio
    if file_size < 1000:
        print(f"⚠️ Warning: Audio file is suspiciously small ({file_size} bytes)")
        print(f"   This might indicate an error in TTS generation")
        print(f"   Text that was converted: {text[:100]}...")
    
    # Try to verify it's a valid audio file by checking magic bytes
    try:
        with open(result, 'rb') as f:
            header = f.read(12)
            # MP3 files start with ID3 or 0xFF 0xFB
            # AAC/M4A files start with 0x00 0x00 or 'ftyp'
            if not (header.startswith(b'ID3') or 
                    header.startswith(b'\xff\xfb') or
                    b'ftyp' in header):
                print(f"⚠️ Warning: File may not be valid audio (unexpected header)")
                print(f"   Header bytes: {header[:8].hex()}")
    except Exception as e:
        print(f"⚠️ Could not validate audio file format: {e}")
    
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