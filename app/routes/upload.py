from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import logging
import uuid
from config import Config
from PyPDF2 import PdfReader
import io
from utils.azure_config import call_azure_api
import json
from utils.rate_limiter import AdaptiveRateLimiter
import tiktoken
import base64
from utils.text_processing import chunk_text, extract_statements, extract_text_from_pdf
from models import get_prompt


upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            # Read PDF content
            pdf_bytes = file.read()
            text = extract_text_from_pdf(pdf_bytes)

            if not text:
                return jsonify({"error": "Failed to extract text from PDF"}), 500

            # Chunk the text
            text_chunks = chunk_text(text)

            # Extract statements of information
            config = {
                'AZURE_OPENAI_KEY': current_app.config['AZURE_OPENAI_KEY'],
                'AZURE_OPENAI_ENDPOINT': current_app.config['AZURE_OPENAI_ENDPOINT'],
                'AZURE_OPENAI_VERSION': current_app.config['AZURE_OPENAI_VERSION'],
                'AZURE_OPENAI_DEPLOYMENT': current_app.config['AZURE_OPENAI_DEPLOYMENT']
            }
            statements = extract_statements(text_chunks, config)
            
            if not statements:
                logging.warning("No statements extracted. Attempting to generate statements from full text.")
                full_text_prompt = get_prompt("extract_statements")["prompt_text"]
                try:
                    full_text_prompt = full_text_prompt.format(chunk=text)
                    response = call_azure_api(full_text_prompt, "statement_extraction", config)
                    content = response['choices'][0]['message']['content']
                    statements_data = json.loads(content)
                    statements = statements_data.get("Statements of information", [])
                except Exception as e:
                    logging.error(f"Failed to extract statements from full text: {str(e)}")
                    statements = []

            logging.debug(f"Extracted statements: {statements}")
            num_statements = len(statements)

            result = {
                "Transcript": text,
                "Statements of information": statements,
                "Number of statements of information": num_statements
            }

            return jsonify(result), 200
        else:
            return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        logging.error(f"Error in upload endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


def generate_question_summary(content, config, rate_limiter):
    prompt_data = get_prompt("generate_question_summary")
    if not prompt_data:
        raise ValueError("Prompt not found")
    
    prompt_text = prompt_data["regular_prompt"]
    variables = prompt_data["variables"]

    summary_prompt = prompt_text.format(content=content)

    rate_limiter.add_request('summary', summary_prompt)
    response = call_azure_api(summary_prompt, "summary", config)
    
    if response and 'choices' in response and response['choices']:
        summary_content = response['choices'][0]['message']['content']
        return json.loads(summary_content)
    else:
        raise ValueError("Failed to generate summary")
