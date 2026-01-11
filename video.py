import subprocess
import tempfile
import os
import shutil
import time
import streamlit as st
from pydub import AudioSegment
from config import Config

def get_audio_duration(audio_path):
    try:
        return len(AudioSegment.from_file(audio_path)) / 1000
    except Exception as e:
        st.error(f"Audio validation failed: {str(e)}")
        return 0

def generate_video(audio_path, avatar_input, lang, is_auto_generated=False):
    """Generate video with enhanced error handling and validation"""
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
            output_path = os.path.join(tmpdir, f"output_{lang}_{timestamp}.mp4")
            final_output = os.path.abspath(
                os.path.join("outputs", f"{lang}_broadcast_{timestamp}.mp4")
            )

            # Handle different avatar sources
            if isinstance(avatar_input, str):  # Auto-generated
                if not os.path.exists(avatar_input):
                    st.error(f"Avatar file not found: {avatar_input}")
                    return None
                shutil.copy(avatar_input, face_path)
            else:  # User upload
                try:
                    with open(face_path, "wb") as f:
                        f.write(avatar_input.getbuffer())
                except Exception as e:
                    st.error(f"Failed to save avatar: {str(e)}")
                    return None

            # Validate critical paths
            wav2lip_root = os.path.abspath("Wav2Lip")
            checkpoint_path = os.path.join(wav2lip_root, "checkpoints", "wav2lip_gan.pth")

            if not os.path.exists(checkpoint_path):
                st.error(f"Missing Wav2Lip checkpoint: {checkpoint_path}")
                return None

            # Check audio duration
            duration = get_audio_duration(audio_path)
            if duration == 0:
                st.error("Invalid audio file - unable to determine duration")
                return None

            if duration > Config.VIDEO_TIMEOUT:
                st.warning(f"Audio too long ({duration:.1f}s). Video generation may timeout.")

            # Build Wav2Lip command with better error handling
            cmd = [
                "python", os.path.join(wav2lip_root, "inference.py"),
                "--checkpoint_path", checkpoint_path,
                "--face", face_path,
                "--audio", os.path.abspath(audio_path),
                "--outfile", output_path,
                "--pads", "0", "20", "0", "0"
            ]

            # Execute with timeout and full environment
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
                timeout=Config.VIDEO_TIMEOUT * 2  # Double the audio duration as timeout
            )

            # Final output handling
            if os.path.exists(output_path):
                os.makedirs(os.path.dirname(final_output), exist_ok=True)
                shutil.copy(output_path, final_output)

                # Verify output
                if os.path.exists(final_output) and os.path.getsize(final_output) > 0:
                    st.success(f"Video generated successfully: {final_output}")
                    return final_output
                else:
                    st.error("Video generation completed but output file is invalid")
                    return None

            return None

    except subprocess.TimeoutExpired:
        st.error(f"Video generation timed out after {Config.VIDEO_TIMEOUT} seconds")
        return None
    except subprocess.CalledProcessError as e:
        st.error(f"Video processing failed: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"Video generation error: {str(e)}")
        return None

def validate_video_requirements():
    """Check if all video generation requirements are met"""
    try:
        # Check Wav2Lip checkpoint
        checkpoint_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"
        if not os.path.exists(checkpoint_path):
            st.warning(f"Missing Wav2Lip checkpoint: {checkpoint_path}")
            st.info("The model will be downloaded automatically on first use (~436MB)")
            st.info("This may take several minutes. Please wait and try again.")
            return False

        # Check avatar files
        for lang, avatar_path in Config.AUTO_AVATARS.items():
            if not os.path.exists(avatar_path):
                st.error(f"Missing avatar for {lang}: {avatar_path}")
                return False

        # Check output directory
        config = Config()
        config.OUTPUT_DIR.mkdir(exist_ok=True)

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
        import tempfile
        import shutil

        st.info("📥 Downloading Wav2Lip model (~436MB). This may take several minutes...")

        # Create directory
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

        # Download URLs (multiple mirrors in case one fails)
        download_urls = [
            "https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EuqU-7p6CpdDvAuqzX2yS9YBziX0mO6EN6x1sD4NsG_2TQ",
            "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
        ]

        for url in download_urls:
            try:
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))

                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)

                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    st.write(f"📥 Download progress: {progress:.1f}%")

                        tmp_path = tmp_file.name

                    # Move to final location
                    shutil.move(tmp_path, checkpoint_path)

                    if os.path.exists(checkpoint_path):
                        size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
                        st.success(f"✅ Model downloaded successfully! Size: {size_mb:.1f} MB")
                        return True

            except Exception as e:
                st.warning(f"Failed to download from {url}: {e}")
                continue

        st.error("❌ Failed to download Wav2Lip model from all mirrors")
        st.info("Please download the model manually:")
        st.code("wget -O Wav2Lip/checkpoints/wav2lip_gan.pth https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EuqU-7p6CpdDvAuqzX2yS9YBziX0mO6EN6x1sD4NsG_2TQ")
        return False

    except ImportError:
        st.error("❌ Missing requests library for model download")
        return False
    except Exception as e:
        st.error(f"❌ Model download failed: {e}")
        return False