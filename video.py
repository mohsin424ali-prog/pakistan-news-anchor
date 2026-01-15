import subprocess
import tempfile
import os
import shutil
import time
import streamlit as st
from pydub import AudioSegment
from config import Config

def get_audio_duration(audio_path):
    """Get audio duration with detailed error reporting"""
    try:
        print(f"🔍 Validating audio file: {audio_path}")
        
        # Check file exists
        if not os.path.exists(audio_path):
            print(f"❌ Audio file does not exist: {audio_path}")
            st.error(f"Audio file not found: {audio_path}")
            return 0
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        print(f"   File size: {file_size} bytes")
        
        if file_size == 0:
            print(f"❌ Audio file is empty")
            st.error("Audio file is empty (0 bytes)")
            return 0
        
        if file_size < 1000:
            print(f"⚠️ Audio file is suspiciously small ({file_size} bytes)")
            st.warning(f"Audio file is very small ({file_size} bytes) - may be invalid")
        
        # Check file header/magic bytes
        try:
            with open(audio_path, 'rb') as f:
                header = f.read(12)
                print(f"   File header: {header[:8].hex()}")
                
                # MP3 files start with ID3 or 0xFF 0xFB
                # AAC/M4A files start with ftyp
                is_valid = (header.startswith(b'ID3') or 
                           header.startswith(b'\xff\xfb') or
                           b'ftyp' in header)
                
                if not is_valid:
                    print(f"⚠️ File may not be valid audio (unexpected header)")
                    st.warning("Audio file format may be invalid")
        except Exception as e:
            print(f"⚠️ Could not read file header: {e}")
        
        # Try to load with pydub
        print(f"   Loading audio with pydub...")
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000
        
        print(f"✅ Audio validated: {duration:.2f}s duration")
        print(f"   Channels: {audio.channels}")
        print(f"   Frame rate: {audio.frame_rate}Hz")
        print(f"   Sample width: {audio.sample_width} bytes")
        
        return duration
        
    except FileNotFoundError as e:
        print(f"❌ Audio file not found: {e}")
        st.error(f"Audio file not found: {audio_path}")
        return 0
    except Exception as e:
        print(f"❌ Audio validation failed: {e}")
        st.error(f"Audio validation failed: {str(e)}")
        
        # Try to provide more specific error info
        if "does not appear to be" in str(e).lower():
            st.error("The file exists but is not a valid audio format")
        elif "codec" in str(e).lower():
            st.error("Audio codec not supported - file may be corrupted")
        
        return 0

def generate_video(audio_path, avatar_input, lang, is_auto_generated=False):
    """Generate video with enhanced error handling and validation"""
    try:
        print(f"\n{'='*80}")
        print(f"🎥 VIDEO GENERATION STARTED")
        print(f"{'='*80}")
        print(f"   Audio: {audio_path}")
        print(f"   Language: {lang}")
        print(f"   Auto-generated avatar: {is_auto_generated}")
        
        # Validate inputs
        if not audio_path:
            error_msg = "No audio file path provided"
            print(f"❌ {error_msg}")
            st.error(error_msg)
            return None
        
        if not os.path.exists(audio_path):
            error_msg = f"Audio file does not exist: {audio_path}"
            print(f"❌ {error_msg}")
            st.error(error_msg)
            
            # List files in the directory to help debug
            audio_dir = os.path.dirname(audio_path)
            if os.path.exists(audio_dir):
                files = os.listdir(audio_dir)
                print(f"   Files in {audio_dir}: {files}")
                st.code(f"Files in audio directory: {files}")
            
            return None

        if not avatar_input:
            error_msg = "No avatar provided"
            print(f"❌ {error_msg}")
            st.error(error_msg)
            return None

        # Language-specific temporary directory
        with tempfile.TemporaryDirectory(prefix=f"video_{lang}_") as tmpdir:
            print(f"   Temp directory: {tmpdir}")
            
            # Unique filenames with timestamp
            timestamp = str(int(time.time()))
            face_path = os.path.join(tmpdir, f"anchor_{lang}_{timestamp}.png")
            output_path = os.path.join(tmpdir, f"output_{lang}_{timestamp}.mp4")
            final_output = os.path.abspath(
                os.path.join("outputs", f"{lang}_broadcast_{timestamp}.mp4")
            )

            # Handle different avatar sources
            print(f"   Processing avatar...")
            if isinstance(avatar_input, str):  # Auto-generated
                if not os.path.exists(avatar_input):
                    error_msg = f"Avatar file not found: {avatar_input}"
                    print(f"❌ {error_msg}")
                    st.error(error_msg)
                    return None
                shutil.copy(avatar_input, face_path)
                print(f"   ✅ Avatar copied from: {avatar_input}")
            else:  # User upload
                try:
                    with open(face_path, "wb") as f:
                        f.write(avatar_input.getbuffer())
                    print(f"   ✅ Avatar saved from upload")
                except Exception as e:
                    error_msg = f"Failed to save avatar: {str(e)}"
                    print(f"❌ {error_msg}")
                    st.error(error_msg)
                    return None

            # Validate critical paths
            wav2lip_root = os.path.abspath("Wav2Lip")
            checkpoint_path = os.path.join(wav2lip_root, "checkpoints", "wav2lip_gan.pth")

            if not os.path.exists(checkpoint_path):
                error_msg = f"Missing Wav2Lip checkpoint: {checkpoint_path}"
                print(f"❌ {error_msg}")
                st.error(error_msg)
                return None

            # Check audio duration with detailed validation
            print(f"\n   Validating audio file...")
            duration = get_audio_duration(audio_path)
            if duration == 0:
                error_msg = "Invalid audio file - unable to determine duration"
                print(f"❌ {error_msg}")
                st.error(error_msg)
                
                # Try to show what went wrong
                st.code(f"Audio path: {audio_path}\nFile exists: {os.path.exists(audio_path)}")
                return None

            if duration > Config.VIDEO_TIMEOUT:
                warning_msg = f"Audio too long ({duration:.1f}s). Video generation may timeout."
                print(f"⚠️ {warning_msg}")
                st.warning(warning_msg)

            # Build Wav2Lip command with better error handling
            print(f"\n   Building Wav2Lip command...")
            cmd = [
                "python", os.path.join(wav2lip_root, "inference.py"),
                "--checkpoint_path", checkpoint_path,
                "--face", face_path,
                "--audio", os.path.abspath(audio_path),
                "--outfile", output_path,
                "--pads", "0", "20", "0", "0"
            ]
            print(f"   Command: {' '.join(cmd)}")

            # Execute with timeout and full environment
            print(f"\n   Running Wav2Lip (timeout: {Config.VIDEO_TIMEOUT * 2}s)...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
                timeout=Config.VIDEO_TIMEOUT * 2
            )

            if result.stdout:
                print(f"   Wav2Lip stdout: {result.stdout[:500]}")
            if result.stderr:
                print(f"   Wav2Lip stderr: {result.stderr[:500]}")

            # Final output handling
            if os.path.exists(output_path):
                os.makedirs(os.path.dirname(final_output), exist_ok=True)
                shutil.copy(output_path, final_output)

                # Verify output
                if os.path.exists(final_output) and os.path.getsize(final_output) > 0:
                    video_size = os.path.getsize(final_output)
                    print(f"✅ Video generated successfully: {final_output} ({video_size} bytes)")
                    st.success(f"Video generated successfully: {final_output}")
                    return final_output
                else:
                    error_msg = "Video generation completed but output file is invalid"
                    print(f"❌ {error_msg}")
                    st.error(error_msg)
                    return None
            else:
                error_msg = f"Video file was not created at {output_path}"
                print(f"❌ {error_msg}")
                st.error(error_msg)
                return None

    except subprocess.TimeoutExpired:
        error_msg = f"Video generation timed out after {Config.VIDEO_TIMEOUT * 2} seconds"
        print(f"⏰ {error_msg}")
        st.error(error_msg)
        return None
    except subprocess.CalledProcessError as e:
        error_msg = f"Video processing failed: {e.stderr}"
        print(f"❌ {error_msg}")
        st.error(error_msg)
        
        # Show more details
        if e.stdout:
            st.code(f"Stdout: {e.stdout}")
        if e.stderr:
            st.code(f"Stderr: {e.stderr}")
        
        return None
    except Exception as e:
        error_msg = f"Video generation error: {str(e)}"
        print(f"❌ {error_msg}")
        st.error(error_msg)
        
        import traceback
        traceback.print_exc()
        
        return None

def validate_video_requirements():
    """Check if all video generation requirements are met"""
    try:
        print("\n🔍 Validating video requirements...")
        
        # Check Wav2Lip checkpoint
        checkpoint_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"
        if not os.path.exists(checkpoint_path):
            print(f"⚠️ Missing Wav2Lip checkpoint: {checkpoint_path}")
            st.warning(f"Missing Wav2Lip checkpoint: {checkpoint_path}")
            st.info("The model will be downloaded automatically on first use (~436MB)")
            st.info("This may take several minutes. Please wait and try again.")
            return False
        else:
            print(f"✅ Wav2Lip checkpoint found")

        # Check avatar files
        missing_avatars = []
        for lang, avatar_path in Config.AUTO_AVATARS.items():
            if not os.path.exists(avatar_path):
                print(f"❌ Missing avatar for {lang}: {avatar_path}")
                missing_avatars.append(f"{lang}: {avatar_path}")
            else:
                print(f"✅ Avatar found for {lang}")
        
        if missing_avatars:
            st.error(f"Missing avatars: {', '.join(missing_avatars)}")
            return False

        # Check output directory
        config = Config()
        config.OUTPUT_DIR.mkdir(exist_ok=True)
        print(f"✅ Output directory ready")

        return True
        
    except Exception as e:
        error_msg = f"Video requirements check failed: {str(e)}"
        print(f"❌ {error_msg}")
        st.error(error_msg)
        return False

def ensure_wav2lip_model():
    """Ensure Wav2Lip model is available, download if necessary"""
    checkpoint_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"

    if os.path.exists(checkpoint_path):
        print(f"✅ Wav2Lip model already exists")
        return True

    try:
        import requests
        import tempfile
        import shutil

        st.info("📥 Downloading Wav2Lip model (~436MB). This may take several minutes...")
        print("📥 Starting Wav2Lip model download...")

        # Create directory
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

        # Download URLs (multiple mirrors in case one fails)
        download_urls = [
            "https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EuqU-7p6CpdDvAuqzX2yS9YBziX0mO6EN6x1sD4NsG_2TQ",
            "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
        ]

        for url_idx, url in enumerate(download_urls):
            try:
                print(f"   Trying mirror {url_idx + 1}/{len(download_urls)}...")
                response = requests.get(url, stream=True, timeout=30)
                
                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    print(f"   Total size: {total_size / (1024*1024):.1f} MB")

                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        downloaded = 0
                        last_percent = -1
                        
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                tmp_file.write(chunk)
                                downloaded += len(chunk)

                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    # Only update display every 5%
                                    if int(progress / 5) > int(last_percent / 5):
                                        st.write(f"📥 Download progress: {progress:.1f}%")
                                        print(f"   Downloaded: {progress:.1f}%")
                                        last_percent = progress

                        tmp_path = tmp_file.name

                    # Move to final location
                    shutil.move(tmp_path, checkpoint_path)

                    if os.path.exists(checkpoint_path):
                        size_mb = os.path.getsize(checkpoint_path) / (1024 * 1024)
                        print(f"✅ Model downloaded: {size_mb:.1f} MB")
                        st.success(f"✅ Model downloaded successfully! Size: {size_mb:.1f} MB")
                        return True

            except Exception as e:
                print(f"⚠️ Mirror {url_idx + 1} failed: {e}")
                st.warning(f"Failed to download from mirror {url_idx + 1}: {e}")
                continue

        # All mirrors failed
        print(f"❌ Failed to download from all mirrors")
        st.error("❌ Failed to download Wav2Lip model from all mirrors")
        st.info("Please download the model manually:")
        st.code("wget -O Wav2Lip/checkpoints/wav2lip_gan.pth https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/download.aspx?share=EuqU-7p6CpdDvAuqzX2yS9YBziX0mO6EN6x1sD4NsG_2TQ")
        return False

    except ImportError:
        st.error("❌ Missing requests library for model download")
        return False
    except Exception as e:
        st.error(f"❌ Model download failed: {e}")
        print(f"❌ Model download error: {e}")
        import traceback
        traceback.print_exc()
        return False