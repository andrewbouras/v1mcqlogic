import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import Config
from app.routes.index import index_bp
from app.routes.upload import upload_bp
from app.routes.task_status import task_status_bp
from app.routes.generate import generate_bp
from app.routes.progress import progress_bp
from utils.rate_limiter import AdaptiveRateLimiter
from utils.task_queue import TaskQueue
from app.task_manager import InMemoryTaskManager
from app.routes.similar import similar_bp
from app.routes.prompts import prompts_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.config.from_object(config_class)
    app.task_manager = InMemoryTaskManager()

    # Initialize TaskQueue
    app.task_queue = TaskQueue()

    # Initialize limiter
    app.limiter = AdaptiveRateLimiter(app.config['TOTAL_TOKENS_PER_MINUTE'])

    # Set up temporary image storage
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'temp_images')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Register blueprints
    from app.routes.index import index_bp
    app.register_blueprint(index_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(task_status_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(similar_bp)
    app.register_blueprint(prompts_bp)  # Register the new prompts blueprint

    @app.route('/temp_images/<filename>')
    def serve_image(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({"error": "rate limit exceeded"}), 429

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app