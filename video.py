import subprocess
import tempfile
import os
import shutil
import time
import logging
import streamlit as st
from pydub import AudioSegment
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_audio_duration(audio_path):
    try:
        return len(AudioSegment.from_file(audio_path)) / 1000
    except Exception as e:
        logger.error(f"Audio validation failed: {str(e)}")
        return 0

def convert_audio_for_wav2lip(input_path, output_path):
    """
    CRITICAL FIX: Wav2Lip often crashes with MP3s or wrong sample rates.
    This forces the audio to be a standard 16kHz WAV file.
    """
    try:
        audio = AudioSegment.from_file(input_path)
        # Convert to 16kHz mono WAV (Wav2Lip's preferred format)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format="wav")
        return True
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        return False

def generate_video(audio_path, avatar_input, lang, is_auto_generated=False):
    """Generate video with enhanced error handling and audio conversion"""
    try:
        # Validate inputs
        if not audio_path or not os.path.exists(audio_path):
            st.error("Invalid audio file provided")
            return None

        if not avatar_input:
            st.error("No avatar provided")
            return None

        # Language-specific temporary directory
        with tempfile.TemporaryDirectory(prefix=f"video_{lang}_") as tmpdir:
            # Unique filenames with timestamp
            timestamp = str(int(time.time()))
            face_path = os.path.join(tmpdir, f"anchor_{lang}_{timestamp}.png")
            
            # We create a specific path for the CLEANED audio
            clean_audio_path = os.path.join(tmpdir, "clean_audio_16k.wav")
            
            output_path = os.path.join(tmpdir, f"output_{lang}_{timestamp}.mp4")
            final_output = os.path.abspath(
                os.path.join("outputs", f"{lang}_broadcast_{timestamp}.mp4")
            )

            # 1. Prepare Avatar
            if isinstance(avatar_input, str):  # Auto-generated path from Config
                if not os.path.exists(avatar_input):
                    st.error(f"Avatar file not found: {avatar_input}")
                    return None
                shutil.copy(avatar_input, face_path)
            else:  # User upload (Streamlit file object)
                try:
                    with open(face_path, "wb") as f:
                        f.write(avatar_input.getbuffer())
                except Exception as e:
                    st.error(f"Failed to save avatar: {str(e)}")
                    return None

            # 2. Prepare Audio (CRITICAL FIX APPLIED HERE)
            # Convert the input MP3 (from gTTS/EdgeTTS) to 16kHz WAV
            logger.info(f"Converting audio {audio_path} to WAV format...")
            if not convert_audio_for_wav2lip(audio_path, clean_audio_path):
                st.error("Failed to process audio file for Wav2Lip.")
                return None

            # 3. Validate Wav2Lip Requirements
            wav2lip_root = os.path.abspath("Wav2Lip")
            checkpoint_path = os.path.join(wav2lip_root, "checkpoints", "wav2lip_gan.pth")

            if not os.path.exists(checkpoint_path):
                st.error(f"Missing Wav2Lip checkpoint: {checkpoint_path}")
                return None

            # Check audio duration using the CLEAN file
            duration = get_audio_duration(clean_audio_path)
            if duration == 0:
                st.error("Invalid audio file - unable to determine duration")
                return None

            if duration > Config.VIDEO_TIMEOUT:
                st.warning(f"Audio too long ({duration:.1f}s). Video generation may timeout.")

            # 4. Build Wav2Lip Command
            # Note: We now use 'clean_audio_path' instead of the original 'audio_path'
            cmd = [
                "python", os.path.join(wav2lip_root, "inference.py"),
                "--checkpoint_path", checkpoint_path,
                "--face", face_path,
                "--audio", clean_audio_path,
                "--outfile", output_path,
                "--pads", "0", "20", "0", "0",
                "--resize_factor", "1" 
            ]

            # 5. Execute
            logger.info(f"Running Wav2Lip for {lang}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=os.environ.copy(),
                timeout=Config.VIDEO_TIMEOUT * 3  # Generous timeout
            )

            # Check for subprocess failure
            if result.returncode != 0:
                logger.error(f"Wav2Lip stderr: {result.stderr}")
                st.error(f"Wav2Lip Error: {result.stderr}")
                return None

            # 6. Finalize
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                os.makedirs(os.path.dirname(final_output), exist_ok=True)
                shutil.copy(output_path, final_output)
                st.success(f"Video generated successfully: {final_output}")
                return final_output
            else:
                st.error("Video generation completed but output file is invalid/empty")
                # Log stderr again to see what happened if file is missing
                logger.error(f"Wav2Lip Output missing. Stderr: {result.stderr}")
                return None

    except subprocess.TimeoutExpired:
        st.error(f"Video generation timed out after {Config.VIDEO_TIMEOUT * 3} seconds")
        return None
    except Exception as e:
        st.error(f"Video generation error: {str(e)}")
        logger.exception("Video generation fatal error")
        return None

def validate_video_requirements():
    """Check if all video generation requirements are met"""
    try:
        # Check Wav2Lip checkpoint
        checkpoint_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"
        if not os.path.exists(checkpoint_path):
            st.warning(f"Missing Wav2Lip checkpoint: {checkpoint_path}")
            st.info("The model will be downloaded automatically on first use (~436MB)")
            return False

        # Check avatar files
        for lang, avatar_path in Config.AUTO_AVATARS.items():
            if not os.path.exists(avatar_path):
                st.error(f"Missing avatar for {lang}: {avatar_path}")
                return False

        # Check output directory
        Config.OUTPUT_DIR.mkdir(exist_ok=True)

        return True
    except Exception as e:
        st.error(f"Video requirements check failed: {str(e)}")
        return False

def ensure_wav2lip_model():
    """Ensure Wav2Lip model is available, download if necessary"""
    checkpoint_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"

    if os.path.exists(checkpoint_path):
        return True

    try:
        import requests
        st.info("📥 Downloading Wav2Lip model (~436MB)...")

        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

        # Primary and backup URLs
        download_urls = [
            "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth",
            "https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EuqU-7p6CpdDvAuqzX2yS9YBziX0mO6EN6x1sD4NsG_2TQ"
        ]

        for url in download_urls:
            try:
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    with open(checkpoint_path, 'wb') as f:
                        shutil.copyfileobj(response.raw, f)
                    
                    if os.path.exists(checkpoint_path) and os.path.getsize(checkpoint_path) > 1000000:
                        st.success("✅ Model downloaded successfully!")
                        return True
            except Exception as e:
                continue

        st.error("❌ Failed to download Wav2Lip model. Please download manually.")
        return False

    except Exception as e:
        st.error(f"❌ Model download failed: {e}")
        return False