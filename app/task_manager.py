import threading
import logging

class InMemoryTaskManager:
    def __init__(self):
        self.tasks = {}

    def create_task(self, task_id, num_questions):
        self.tasks[task_id] = {
            'status': 'pending',
            'progress': 0,
            'num_questions': num_questions,
            'result': None
        }

    def update_task_progress(self, task_id, progress):
        if task_id in self.tasks:
            self.tasks[task_id]['progress'] = progress

    def complete_task(self, task_id, result):
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'completed'
            self.tasks[task_id]['progress'] = 100
            self.tasks[task_id]['result'] = result

    def get_task_progress(self, task_id):
        return self.tasks.get(task_id)