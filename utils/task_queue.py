import queue
import threading
import time
import uuid

class TaskQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.tasks = {}
        self.lock = threading.Lock()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def add_task(self, task_func, *args, **kwargs):
        task_id = str(uuid.uuid4())
        with self.lock:
            self.tasks[task_id] = {
                'status': 'queued',
                'result': None,
                'queued_at': time.time()
            }
        self.queue.put((task_id, task_func, args, kwargs))
        return task_id

    def get_task_status(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                wait_time = max(0, int(30 - (time.time() - task['queued_at'])))
                return {
                    'status': task['status'],
                    'result': task['result'],
                    'estimated_wait_time': wait_time if task['status'] == 'queued' else None
                }
        return None

    def _process_queue(self):
        while True:
            task_id, task_func, args, kwargs = self.queue.get()
            with self.lock:
                self.tasks[task_id]['status'] = 'processing'
            try:
                result = task_func(*args, **kwargs)
                with self.lock:
                    self.tasks[task_id]['status'] = 'completed'
                    self.tasks[task_id]['result'] = result
            except Exception as e:
                with self.lock:
                    self.tasks[task_id]['status'] = 'failed'
                    self.tasks[task_id]['result'] = str(e)
            finally:
                self.queue.task_done()