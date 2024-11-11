from flask import Blueprint, jsonify, current_app
from models import get_prompt

index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    return jsonify({"message": "Welcome to the MCQ Generator API"})

@index_bp.route('/test_mongodb')
def test_mongodb():
    print("Accessing /test_mongodb route")  # Add this line
    try:
        print("Attempting to connect to MongoDB...")
        prompt = get_prompt("generate_mcqs")
        print(f"Prompt retrieved: {prompt}")
        if prompt:
            return jsonify({"message": "Successfully connected to MongoDB Atlas!", "prompt": prompt}), 200
        else:
            print("No prompt found in MongoDB")
            return jsonify({"message": "Connected to MongoDB Atlas, but no data found."}), 200
    except Exception as e:
        print(f"Error in test_mongodb: {str(e)}")
        return jsonify({"error": str(e)}), 500

@index_bp.route('/test')
def test():
    print("Accessing /test route")
    return jsonify({"message": "Test route working"}), 200