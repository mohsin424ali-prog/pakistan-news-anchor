# async_processor.py - IMPROVED VERSION (cleaner architecture)
import asyncio
import queue
import threading
import time
import logging
import os
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class AsyncProcessor:
    """Manages asynchronous processing of TTS and video generation"""

    def __init__(self):
        self.task_queue = queue.Queue()
        self.results = {}
        self.processing = {}
        self.worker_thread = None
        self.running = False
        self.max_concurrent_tasks = 2
        self.event_loop = None

    def start(self):
        """Start the async processor"""
        if self.running:
            logger.info("Async processor already running")
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("✅ Async processor started")

    def stop(self):
        """Stop the async processor"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("🛑 Async processor stopped")

    def _worker(self):
        """Background worker thread - runs event loop for async tasks"""
        # Create new event loop for this thread
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)
        logger.info("🔄 Worker thread event loop created")
        
        while self.running:
            try:
                self._cleanup_completed_tasks()

                if self._get_active_count() < self.max_concurrent_tasks:
                    try:
                        task = self.task_queue.get(timeout=1)
                        logger.info(f"📥 Processing task from queue: {task['task_id']}")
                        # Process task in event loop
                        self.event_loop.run_until_complete(self._process_task_async(task))
                        self.task_queue.task_done()
                    except queue.Empty:
                        continue
                else:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Worker error: {e}", exc_info=True)
                time.sleep(1)
        
        self.event_loop.close()
        logger.info("🔄 Worker thread event loop closed")

    def _get_active_count(self) -> int:
        """Get count of active tasks"""
        count = sum(1 for status in self.processing.values() if status['status'] == 'processing')
        return count

    def _cleanup_completed_tasks(self):
        """Remove old completed tasks from memory"""
        current_time = time.time()
        to_remove = [
            task_id for task_id, status in self.processing.items()
            if status['status'] in ('completed', 'failed') 
            and current_time - status.get('completed_at', current_time) > 300  # 5 minutes
        ]

        for task_id in to_remove:
            self.processing.pop(task_id, None)
            self.results.pop(task_id, None)
            logger.debug(f"🧹 Cleaned up old task: {task_id}")

    async def _process_task_async(self, task: Dict[str, Any]):
        """Process a single task asynchronously"""
        task_id = task['task_id']
        self.processing[task_id] = {
            'status': 'processing',
            'started_at': time.time(),
            'task_type': task['type']
        }
        logger.info(f"▶️ Starting task {task_id} ({task['type']})")

        try:
            if task['type'] == 'tts':
                result = await self._process_tts_task_async(task)
            elif task['type'] == 'video':
                result = await self._process_video_task_async(task)
            else:
                raise ValueError(f"Unknown task type: {task['type']}")

            self.results[task_id] = {'success': True, 'result': result}
            self.processing[task_id]['status'] = 'completed'
            self.processing[task_id]['completed_at'] = time.time()
            
            elapsed = time.time() - self.processing[task_id]['started_at']
            logger.info(f"✅ Task {task_id} completed in {elapsed:.1f}s")

        except Exception as e:
            logger.error(f"❌ Task {task_id} failed: {e}", exc_info=True)
            self.results[task_id] = {'success': False, 'error': str(e)}
            self.processing[task_id]['status'] = 'failed'
            self.processing[task_id]['error'] = str(e)
            self.processing[task_id]['completed_at'] = time.time()

    async def _process_tts_task_async(self, task: Dict[str, Any]) -> str:
        """
        Process TTS task - Calls the actual TTS generation function from tts.py
        FIXED: No longer creates circular dependency
        """
        text = task['text']
        gender = task.get('gender', 'Male')
        language = task['language']
        
        logger.info(f"🎙️ TTS task: lang={language}, gender={gender}, text_len={len(text)}")
        
        # Import here to avoid circular imports at module level
        from tts import generate_tts_audio
        
        # Call the ACTUAL TTS generation function (not the task submission function)
        result = await generate_tts_audio(text, gender, language)
        
        if result and os.path.exists(result):
            logger.info(f"✅ Audio file created: {result}")
            return result
        else:
            raise RuntimeError(f"TTS generation failed - no file created")

    async def _process_video_task_async(self, task: Dict[str, Any]) -> str:
        """Process video generation task"""
        from video import generate_video

        audio_path = task['audio_path']
        avatar_input = task['avatar_input']
        lang = task['language']
        is_auto_generated = task.get('is_auto_generated', False)

        logger.info(f"🎥 Video task: lang={lang}, audio={audio_path}")
        
        # Verify audio exists before starting
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Run blocking video generation in thread pool
        result = await asyncio.to_thread(
            generate_video, 
            audio_path, 
            avatar_input, 
            lang, 
            is_auto_generated
        )
        
        if result and os.path.exists(result):
            logger.info(f"✅ Video file created: {result}")
            return result
        else:
            raise RuntimeError("Video generation failed - no file created")

    def submit_task(self, task_type: str, **kwargs) -> str:
        """Submit a new task for processing"""
        task_id = f"{task_type}_{int(time.time() * 1000)}_{id(kwargs)}"

        task = {
            'task_id': task_id,
            'type': task_type,
            **kwargs
        }

        self.task_queue.put(task)
        self.processing[task_id] = {
            'status': 'queued',
            'queued_at': time.time(),
            'task_type': task_type
        }
        logger.info(f"📤 Submitted {task_type} task: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        if task_id not in self.processing:
            return {'status': 'not_found'}

        status = self.processing[task_id].copy()

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


def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0):
    """Decorator to retry async functions with exponential backoff"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise e

                    logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2
            
            raise last_exception
        
        return wrapper
    return decorator