import time
from app.routes.generate import generate_mcqs, parse_mcqs
from utils.azure_config import call_azure_api
import logging
import threading
from flask import current_app
from utils.rate_limiter import AdaptiveRateLimiter

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

WEBHOOK_URL = "https://webhook.site/71b35bad-c81e-4e4f-8652-d2ef16f20a8b"

class InMemoryTaskManager:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()

    def create_task(self, task_id, total_questions):
        with self.lock:
            self.tasks[task_id] = {
                'total_questions': total_questions,
                'completed_sets': 0,
                'total_sets': (total_questions + 9) // 10,  # Round up to nearest 10
                'status': 'in_progress',
                'result': None
            }

    def update_task_progress(self, task_id, completed_sets):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['completed_sets'] = completed_sets

    def complete_task(self, task_id, result):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['result'] = result

    def get_task_status(self, task_id):
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    'status': task['status'],
                    'progress': f"{task['completed_sets']}/{task['total_sets']} sets completed",
                    'result': task['result'] if task['status'] == 'completed' else None
                }
            return None

def generate_mcqs_task(task_id, text, num_questions, question_style, config):
    with current_app.app_context():
        task_manager = current_app.task_manager
        try:
            logging.info(f"Initializing MCQ generation for task {task_id}...")
            
            chunks = [text]  # For simplicity, we're not chunking the text here
            questions_per_chunk = [num_questions]

            all_mcqs = {
                "task_id": task_id,
                "total_questions": num_questions
            }
            questions_generated = 0

            for i, (chunk, chunk_questions) in enumerate(zip(chunks, questions_per_chunk)):
                logging.info(f"Generating {chunk_questions} MCQs for chunk {i+1} in task {task_id}...")
                chunk_config = config.copy()
                chunk_config['task_id'] = task_id
                chunk_config['chunk_number'] = i + 1
                
                for attempt in range(MAX_RETRIES):
                    try:
                        mcqs = generate_mcqs(chunk, chunk_questions, question_style, chunk_config)
                        logging.debug(f"Generated MCQs: {mcqs}")
                        break
                    except Exception as e:
                        if attempt < MAX_RETRIES - 1:
                            logging.warning(f"Attempt {attempt + 1} failed for chunk {i+1} in task {task_id}. Retrying...")
                            time.sleep(RETRY_DELAY)
                        else:
                            raise Exception(f"Failed to generate MCQs for chunk {i+1} after {MAX_RETRIES} attempts")

                all_mcqs[f"chunk_{i+1}"] = mcqs
                
                questions_generated += chunk_questions
                task_manager.update_task_progress(task_id, questions_generated)

            task_manager.complete_task(task_id, all_mcqs)
            return {'status': 'Task completed', 'result': all_mcqs}
        except Exception as e:
            logging.error(f"Error in generate_mcqs_task: {str(e)}")
            task_manager.complete_task(task_id, {'error': str(e)})
            return {'status': 'Task failed', 'error': str(e)}

def start_mcq_generation_task(task_id, text, num_questions, question_style, config):
    thread = threading.Thread(
        target=generate_mcqs_task,
        args=(task_id, text, num_questions, question_style, config)
    )
    thread.start()