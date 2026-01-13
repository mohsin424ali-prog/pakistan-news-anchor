import asyncio
import os
import time
import logging
from gtts import gTTS
import edge_tts
from config import Config
from async_processor import async_processor

logger = logging.getLogger(__name__)

# --- UI INTERFACE ---
async def generate_audio(text, gender, language):
    """
    Submits a request to the background queue.
    Returns a Task ID immediately.
    """
    if not text or len(text) < Config.MIN_ARTICLE_LENGTH:
        return None

    task_id = async_processor.submit_task(
        'tts',
        text=text,
        gender=gender,
        language=language
    )
    return task_id

# --- BACKGROUND EXECUTION ---
async def execute_tts_work(text, gender, language):
    """
    The actual worker logic that performs the TTS and saves the file.
    Returns the absolute path to the generated file.
    """
    timestamp = int(time.time() * 1000)
    audio_dir = os.path.abspath("temp_audio")
    os.makedirs(audio_dir, exist_ok=True)
    
    file_ext = "mp3"
    audio_path = os.path.join(audio_dir, f"tts_{language}_{timestamp}.{file_ext}")
    
    try:
        if language == 'ur':
            return await _gtts_urdu(text, audio_path)
        else:
            return await _edge_tts(text, gender, audio_path)
    except Exception as e:
        logger.error(f"TTS Execution failed: {e}")
        return None

async def _gtts_urdu(text, audio_path):
    tts = gTTS(text=text, lang='ur', tld='com.pk')
    # Run gTTS in a thread to keep the event loop free
    await asyncio.to_thread(tts.save, audio_path)
    return audio_path if os.path.exists(audio_path) else None

async def _edge_tts(text, gender, audio_path):
    # Select voice based on Config and Gender
    voice = Config.TTS_CONFIG['en']['voice']
    if gender == "Female":
        voice = "en-GB-LibbyNeural"
        
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(audio_path)
    return audio_path if os.path.exists(audio_path) else None