import hashlib
import asyncio
import os
import time
import streamlit as st
from gtts import gTTS
import edge_tts
from config import Config
from async_processor import async_processor, retry_with_backoff

@retry_with_backoff
async def generate_summary_audio(headlines, language):
    summary_text = "\n".join([
        f"{h['category']} news: {h['text']}"
        for h in headlines
    ])

    # Submit to async processor
    task_id = async_processor.submit_task(
        'tts',
        text=summary_text,
        gender="Male",
        language=language
    )

    return task_id

@retry_with_backoff
async def generate_audio(text, gender, language):
    if not text or len(text) < Config.MIN_ARTICLE_LENGTH:
        st.error("Insufficient text for audio generation")
        return None

    # Submit to async processor
    task_id = async_processor.submit_task(
        'tts',
        text=text,
        gender=gender,
        language=language
    )

    return task_id

async def _gtts_urdu(text, audio_path):
    try:
        tts = gTTS(text=text, lang='ur', tld='com.pk', slow=False)
        await asyncio.to_thread(tts.save, audio_path)
        return audio_path if os.path.exists(audio_path) else None
    except Exception as e:
        st.error(f"Urdu TTS Error: {str(e)}")
        return None

async def _edge_tts(text, gender, audio_path):
    try:
        voice = Config.TTS_CONFIG['en']['voice']
        if gender == "Female":
            voice = "en-GB-LibbyNeural"

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(audio_path)
        return audio_path if os.path.exists(audio_path) else None
    except Exception as e:
        st.error(f"English TTS Error: {str(e)}")
        return None

def get_audio_result(task_id: str, timeout: int = 60):
    """Get the result of an audio generation task"""
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = async_processor.get_task_status(task_id)

        if status['status'] == 'completed':
            return status.get('result', {}).get('result')
        elif status['status'] == 'failed':
            st.error(f"Audio generation failed: {status.get('result', {}).get('error')}")
            return None

        time.sleep(0.5)

    st.warning("Audio generation timed out")
    return None