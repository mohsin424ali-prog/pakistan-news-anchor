#!/usr/bin/env python3
"""
Diagnostic script to test TTS and async processor components.
Run this BEFORE the main app to identify issues.

Usage: python test_components.py
"""

import sys
import os
import asyncio
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*80)
print("🔍 NEWS ANCHOR COMPONENTS DIAGNOSTIC TEST")
print("="*80)

# Test 1: Import all modules
print("\n📦 Test 1: Importing modules...")
try:
    from config import Config
    print("✅ Config imported")
    
    from async_processor import async_processor
    print("✅ AsyncProcessor imported")
    
    from tts import generate_tts_audio, generate_audio, get_audio_result
    print("✅ TTS module imported")
    
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check configuration
print("\n⚙️ Test 2: Checking configuration...")
try:
    print(f"   MIN_ARTICLE_LENGTH: {Config.MIN_ARTICLE_LENGTH}")
    print(f"   MAX_TTS_LENGTH: {Config.MAX_TTS_LENGTH}")
    print(f"   OUTPUT_DIR: {Config().OUTPUT_DIR}")
    print(f"   AUTO_AVATARS: {Config.AUTO_AVATARS}")
    
    # Check output directory
    output_dir = Config().OUTPUT_DIR / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory created: {output_dir}")
    
    # Test write permissions
    test_file = output_dir / "test.txt"
    test_file.write_text("test")
    if test_file.exists():
        test_file.unlink()
        print("✅ Write permissions OK")
    else:
        print("❌ Cannot write to output directory")
        
except Exception as e:
    print(f"❌ Configuration check failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Test async processor initialization
print("\n🔄 Test 3: Testing AsyncProcessor...")
try:
    async_processor.start()
    time.sleep(1)  # Give it time to start
    
    if async_processor.running:
        print("✅ AsyncProcessor started")
        
        stats = async_processor.get_queue_stats()
        print(f"   Queue stats: {stats}")
    else:
        print("❌ AsyncProcessor failed to start")
        
except Exception as e:
    print(f"❌ AsyncProcessor test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test direct TTS generation (bypassing task queue)
print("\n🎙️ Test 4: Testing direct TTS generation...")

async def test_direct_tts():
    try:
        test_text = "This is a test of the text to speech system. Hello world!"
        output_dir = Config().OUTPUT_DIR / "audio"
        test_audio_path = str(output_dir / "test_direct_tts.mp3")
        
        print(f"   Generating audio to: {test_audio_path}")
        
        # Test English TTS
        result = await generate_tts_audio(test_text, "Male", "en")
        
        if result and os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"✅ Direct TTS successful: {result} ({file_size} bytes)")
            
            # Clean up
            os.remove(result)
            return True
        else:
            print(f"❌ Direct TTS failed - no file created")
            return False
            
    except Exception as e:
        print(f"❌ Direct TTS failed: {e}")
        import traceback
        traceback.print_exc()
        return False

try:
    success = asyncio.run(test_direct_tts())
    if not success:
        print("⚠️ Direct TTS test failed")
except Exception as e:
    print(f"❌ Direct TTS test error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Test full task queue flow
print("\n📤 Test 5: Testing task queue flow...")
try:
    test_text = "This is a complete test of the async task processing system."
    
    print("   Submitting task...")
    task_id = generate_audio(test_text, "Male", "en")
    
    if not task_id:
        print("❌ Failed to submit task")
    else:
        print(f"✅ Task submitted: {task_id}")
        
        # Wait for result
        print("   Waiting for result (max 30s)...")
        audio_path = get_audio_result(task_id, timeout=30)
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            print(f"✅ Full flow successful: {audio_path} ({file_size} bytes)")
            
            # Clean up
            os.remove(audio_path)
        else:
            print(f"❌ Full flow failed - audio_path: {audio_path}")
            
            # Show task status
            status = async_processor.get_task_status(task_id)
            print(f"   Task status: {status}")
            
except Exception as e:
    print(f"❌ Task queue test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Test with Urdu
print("\n🕌 Test 6: Testing Urdu TTS...")

async def test_urdu_tts():
    try:
        test_text = "یہ ایک ٹیسٹ ہے"  # "This is a test"
        output_dir = Config().OUTPUT_DIR / "audio"
        test_audio_path = str(output_dir / "test_urdu_tts.mp3")
        
        print(f"   Generating Urdu audio...")
        
        result = await generate_tts_audio(test_text, "Male", "ur")
        
        if result and os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"✅ Urdu TTS successful: {result} ({file_size} bytes)")
            
            # Clean up
            os.remove(result)
            return True
        else:
            print(f"❌ Urdu TTS failed")
            return False
            
    except Exception as e:
        print(f"❌ Urdu TTS failed: {e}")
        import traceback
        traceback.print_exc()
        return False

try:
    success = asyncio.run(test_urdu_tts())
except Exception as e:
    print(f"❌ Urdu TTS test error: {e}")

# Cleanup
print("\n🧹 Cleaning up...")
try:
    async_processor.stop()
    time.sleep(1)
    print("✅ AsyncProcessor stopped")
except Exception as e:
    print(f"⚠️ Cleanup warning: {e}")

# Summary
print("\n" + "="*80)
print("📊 TEST SUMMARY")
print("="*80)
print("If all tests passed, your components are working correctly.")
print("If any tests failed, check the error messages above.")
print("\nNext steps:")
print("1. If TTS tests passed, the issue is likely in video generation")
print("2. If TTS tests failed, check:")
print("   - Internet connectivity (for Edge TTS)")
print("   - File permissions in output directory")
print("   - Dependencies (gtts, edge-tts, pydub)")
print("="*80)