# async_processor.py
import asyncio
import queue
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable
import streamlit as st
from config import Config

logger = logging.getLogger(__name__)

class AsyncProcessor:
    """Manages asynchronous processing of TTS and video generation"""

    def __init__(self):
        self.task_queue = queue.Queue()
        self.results = {}
        self.processing = {}
        self.worker_thread = None
        self.running = False
        self.max_concurrent_tasks = 2  # Limit concurrent video generation

    def start(self):
        """Start the async processor"""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Async processor started")

    def stop(self):
        """Stop the async processor"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Async processor stopped")

    def _worker(self):
        """Background worker thread"""
        while self.running:
            try:
                # Check for completed tasks to clean up
                self._cleanup_completed_tasks()

                # Process new tasks if under limit
                if self._get_active_count() < self.max_concurrent_tasks:
                    try:
                        task = self.task_queue.get(timeout=1)
                        self._process_task(task)
                        self.task_queue.task_done()
                    except queue.Empty:
                        continue
                else:
                    time.sleep(0.5)  # Wait if at limit

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(1)

    def _get_active_count(self) -> int:
        """Get count of active tasks"""
        return sum(1 for status in self.processing.values() if status['status'] == 'processing')

    def _cleanup_completed_tasks(self):
        """Remove completed tasks from memory"""
        current_time = time.time()
        to_remove = []

        for task_id, status in self.processing.items():
            if status['status'] == 'completed' and current_time - status['completed_at'] > 300:  # 5 minutes
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.processing[task_id]
            if task_id in self.results:
                del self.results[task_id]

    def _process_task(self, task: Dict[str, Any]):
        """Process a single task"""
        task_id = task['task_id']
        self.processing[task_id] = {
            'status': 'processing',
            'started_at': time.time(),
            'task_type': task['type']
        }

        try:
            if task['type'] == 'tts':
                result = self._process_tts_task(task)
            elif task['type'] == 'video':
                result = self._process_video_task(task)
            else:
                raise ValueError(f"Unknown task type: {task['type']}")

            self.results[task_id] = {'success': True, 'result': result}
            self.processing[task_id]['status'] = 'completed'
            self.processing[task_id]['completed_at'] = time.time()
            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.results[task_id] = {'success': False, 'error': str(e)}
            self.processing[task_id]['status'] = 'failed'
            self.processing[task_id]['error'] = str(e)

    def _process_tts_task(self, task: Dict[str, Any]) -> str:
        """Process TTS task"""
        from tts import generate_audio

        text = task['text']
        gender = task['gender']
        language = task['language']

        logger.info(f"Processing TTS task: {task['task_id']}")
        return asyncio.run(generate_audio(text, gender, language))

    def _process_video_task(self, task: Dict[str, Any]) -> str:
        """Process video generation task"""
        from video import generate_video

        audio_path = task['audio_path']
        avatar_input = task['avatar_input']
        lang = task['language']
        is_auto_generated = task['is_auto_generated']

        logger.info(f"Processing video task: {task['task_id']}")
        return generate_video(audio_path, avatar_input, lang, is_auto_generated)

    def submit_task(self, task_type: str, **kwargs) -> str:
        """Submit a new task for processing"""
        task_id = f"{task_type}_{int(time.time() * 1000)}_{id(kwargs)}"

        task = {
            'task_id': task_id,
            'type': task_type,
            **kwargs
        }

        self.task_queue.put(task)
        logger.info(f"Submitted {task_type} task: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        if task_id not in self.processing:
            return {'status': 'not_found'}

        status = self.processing[task_id].copy()

        # Add result if completed
        if task_id in self.results:
            status['result'] = self.results[task_id]

        return status

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queue_size': self.task_queue.qsize(),
            'active_tasks': self._get_active_count(),
            'total_tasks': len(self.processing),
            'max_concurrent': self.max_concurrent_tasks
        }

# Global async processor instance
async_processor = AsyncProcessor()

def init_async_processor():
    """Initialize the async processor"""
    if not async_processor.running:
        async_processor.start()

def cleanup_async_processor():
    """Clean up the async processor"""
    async_processor.stop()

class ProgressTracker:
    """Track progress of long-running operations"""

    @staticmethod
    def show_tts_progress(task_id: str, placeholder):
        """Show TTS generation progress"""
        progress_bar = placeholder.progress(0)
        status_text = placeholder.text("🎙️ Generating audio...")

        for i in range(100):
            status = async_processor.get_task_status(task_id)

            if status['status'] == 'completed':
                progress_bar.progress(100)
                status_text.text("✅ Audio generated successfully!")
                return status.get('result', {}).get('result')

            elif status['status'] == 'failed':
                progress_bar.progress(0)
                status_text.text(f"❌ Audio generation failed: {status.get('result', {}).get('error')}")
                return None

            elif status['status'] == 'processing':
                progress_bar.progress(min(i + 1, 90))  # Cap at 90% until completion

            time.sleep(0.1)

        # Timeout
        progress_bar.progress(0)
        status_text.text("⏰ Audio generation timed out")
        return None

    @staticmethod
    def show_video_progress(task_id: str, placeholder):
        """Show video generation progress"""
        progress_bar = placeholder.progress(0)
        status_text = placeholder.text("🎥 Generating video... This may take a few minutes")

        start_time = time.time()
        timeout = 300  # 5 minutes timeout

        while time.time() - start_time < timeout:
            status = async_processor.get_task_status(task_id)

            if status['status'] == 'completed':
                progress_bar.progress(100)
                status_text.text("✅ Video generated successfully!")
                return status.get('result', {}).get('result')

            elif status['status'] == 'failed':
                progress_bar.progress(0)
                status_text.text(f"❌ Video generation failed: {status.get('result', {}).get('error')}")
                return None

            elif status['status'] == 'processing':
                # Estimate progress based on time elapsed
                elapsed = time.time() - start_time
                estimated_progress = min(int(elapsed / timeout * 80), 80)  # Cap at 80%
                progress_bar.progress(estimated_progress)

            time.sleep(1)

        # Timeout
        progress_bar.progress(0)
        status_text.text("⏰ Video generation timed out")
        return None

def retry_with_backoff(func: Callable, max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator to retry functions with exponential backoff"""
    async def wrapper(*args, **kwargs):
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e

                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

    return wrapper