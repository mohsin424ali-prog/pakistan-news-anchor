import asyncio
import queue
import threading
import time
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class AsyncProcessor:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.results = {}
        self.processing = {}
        self.worker_thread = None
        self.running = False
        self.max_concurrent_tasks = 1 # Keep low for CPU/RAM stability

    def start(self):
        if self.running: return
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                self._process_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue

    def _process_task(self, task):
        task_id = task['task_id']
        self.processing[task_id] = {'status': 'processing', 'started_at': time.time()}
        
        try:
            if task['type'] == 'tts':
                # IMPORTANT: Import here to avoid circular imports at top of file
                from tts import execute_tts_work
                result = asyncio.run(execute_tts_work(
                    task['text'], task['gender'], task['language']
                ))
            
            self.results[task_id] = {'success': True, 'result': result}
            self.processing[task_id]['status'] = 'completed'
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.results[task_id] = {'success': False, 'error': str(e)}
            self.processing[task_id]['status'] = 'failed'

    def submit_task(self, task_type: str, **kwargs) -> str:
        task_id = f"{task_type}_{int(time.time() * 1000)}"
        self.task_queue.put({'task_id': task_id, 'type': task_type, **kwargs})
        return task_id

    def get_task_status(self, task_id: str):
        if task_id not in self.processing: return {'status': 'not_found'}
        status = self.processing[task_id].copy()
        if task_id in self.results: status['result'] = self.results[task_id]
        return status

async_processor = AsyncProcessor()