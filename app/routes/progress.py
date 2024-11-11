from flask import Blueprint, jsonify, current_app
import logging

progress_bp = Blueprint('progress', __name__)

@progress_bp.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    progress = current_app.task_manager.get_task_progress(task_id)
    if progress:
        return jsonify({
            "task_id": task_id,
            "status": progress.get('status', 'unknown'),
            "progress": progress.get('progress', 0),
            "total_questions": progress.get('num_questions', 0),
            "completed_questions": int(progress.get('progress', 0) * progress.get('num_questions', 0) / 100)
        }), 200
    else:
        return jsonify({"error": "Task not found"}), 404