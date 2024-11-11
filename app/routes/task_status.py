from flask import Blueprint, jsonify, current_app
import threading
import logging

task_status_bp = Blueprint('task_status', __name__)

@task_status_bp.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    status = current_app.task_queue.get_task_status(task_id)
    if status:
        return jsonify(status)
    return jsonify({"error": "Task not found"}), 404

class InMemoryTaskManager:
    def __init__(self, task_expiry=3600):  # Default to 1 hour if not specified
        self.tasks = {}
        self.lock = threading.Lock()
        self.task_expiry = task_expiry

    def create_task(self, task_id, total_questions):
        logging.info(f"Creating task with ID: {task_id}, total questions: {total_questions}")
        with self.lock:
            self.tasks[task_id] = {
                'total_questions': total_questions,
                'completed_questions': 0,
                'status': 'in_progress',
                'result': None
            }
        return task_id

    def update_task_progress(self, task_id, completed_questions):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['completed_questions'] = completed_questions
                self.tasks[task_id]['status'] = 'in_progress'

    def complete_task(self, task_id, result):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['result'] = result
                self.tasks[task_id]['completed_questions'] = self.tasks[task_id]['total_questions']

    def get_task_progress(self, task_id):
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    'task_id': task_id,
                    'total_questions': task['total_questions'],
                    'completed_questions': task['completed_questions'],
                    'status': task['status'],
                    'progress': (task['completed_questions'] / task['total_questions']) * 100 if task['total_questions'] > 0 else 0,
                    'result': task['result']
                }
            return None