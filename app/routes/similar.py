import sys
import traceback
from flask import Blueprint, request, jsonify, current_app
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from utils.azure_config import call_azure_api
import json
import json5
import requests
from app.utils import get_configuration, get_prompt

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

similar_bp = Blueprint('similar', __name__)

# Initialize model as None first - we'll load it when needed
model = None

def get_model():
    global model
    if model is None:
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logging.error(f"Error loading sentence transformer model: {str(e)}")
            return None
    return model

def get_relevant_content(context, question, answers, explanation, num_sentences=5):
    query = f"{question} {' '.join(answers)} {explanation}"
    sentences = context.split('.')
    sentence_embeddings = model.encode(sentences)
    query_embedding = model.encode([query])[0]
    similarities = np.dot(sentence_embeddings, query_embedding) / (np.linalg.norm(sentence_embeddings, axis=1) * np.linalg.norm(query_embedding))
    top_indices = similarities.argsort()[-num_sentences:][::-1]
    relevant_content = '. '.join([sentences[i].strip() for i in top_indices])
    return relevant_content.strip()

@similar_bp.route('/similar', methods=['POST'])
def generate_similar_questions():
    data = request.json
    # Existing fields
    num_questions = data.get('num_questions')
    style = data.get('style')
    question = data.get('question')
    text = data.get('text')
    bold = data.get('bold')
    # New fields
    notebook_ID = data.get('notebook_ID')
    user_ID = data.get('user_ID')
    chapter_ID = data.get('chapter_ID')
    question_ID = data.get('question_ID')
    answerChoices = data.get('answerChoices')
    explanation = data.get('explanation')
    concept = data.get('concept')
    # Validate required fields (as needed)
    # ...

    # Revert to original prompt handling
    prompt_template = get_prompt("generate_similar_questions")
    if not isinstance(prompt_template, dict):
        raise ValueError("Invalid prompt template configuration")

    # Get the prompt text from the template - look for regular_prompt instead of prompt_text
    prompt_text = prompt_template.get('regular_prompt')
    if not prompt_text:
        logging.error(f"Available keys in prompt template: {prompt_template.keys()}")
        raise ValueError("Prompt template is missing required 'regular_prompt' field")

    style_config = get_configuration("question_styles")
    bolding_config = get_configuration("bolding_options")

    bold_str = str(bold).lower()
    if bold_str not in bolding_config:
        raise ValueError(f"Invalid bolding option: {bold}")
    
    style_details = style_config.get(style)
    if not style_details:
        raise ValueError(f"Invalid style option: {style}")
    
    bolding_details = bolding_config.get(bold_str)
    if not bolding_details:
        raise ValueError(f"Invalid bolding option: {bold_str}")
    
    prompt = prompt_text.format(
        num_questions=num_questions,
        style=style,
        question=question,
        relevant_content=text,
        text=text,
        bold=bold_str
    )
    
    logging.debug(f"Generated prompt: {prompt[:500]}...")
    logging.info(f"Full prompt being sent to Azure OpenAI: {prompt}")
    
    config = get_configuration("azure_openai")

    # Ensure all required keys are present in the configuration
    required_keys = ["AZURE_OPENAI_ENDPOINT", "AZURE_API_KEY"]
    missing_keys = [key for key in required_keys if key not in config]

    if missing_keys:
        logging.error(f"Missing configuration keys: {missing_keys}")
        return jsonify({"error": f"Missing configuration keys: {missing_keys}"}), 500

    response = call_azure_api(prompt, "question_generation", config)
    logging.debug(f"Azure API response: {response}")
    
    content = response['choices'][0]['message']['content']
    logging.debug(f"Raw content from API: {content}")

    # Clean and parse the content
    content = content.strip().replace('```json', '').replace('```', '')
    logging.debug(f"Cleaned content: {content}")

    try:
        questions_data = json.loads(content)
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {str(e)}")
        logging.error(f"Content that caused the error: {content}")
        return jsonify({"error": f"Failed to parse API response: {str(e)}"}), 500

    logging.debug(f"Parsed questions_data: {questions_data}")

    # Ensure 'questions' key exists in the returned data
    if 'questions' not in questions_data:
        questions_data['questions'] = [questions_data] if isinstance(questions_data, dict) else []

    # Generate a unique ID for the response
    import uuid
    response_id = str(uuid.uuid4())

    # Update the final result structure to include all necessary fields
    final_result = {
        "notebook_ID": data.get('notebook_ID'),
        "user_ID": data.get('user_ID'),
        "chapter_ID": data.get('chapter_ID'),
        "question_ID": data.get('question_ID'),
        "questions": questions_data.get('questions', [questions_data] if isinstance(questions_data, dict) else [])
    }
    logging.debug(f"Final result before formatting: {final_result}")

    # Update webhook URL and error handling
    webhook_url = current_app.config.get('WEBHOOK_URL', 'https://backend.thenotemachine.com/api')
    try:
        webhook_response = requests.post(webhook_url, json=final_result, timeout=10)
        webhook_response.raise_for_status()
        logging.info("Successfully sent the content to the webhook endpoint.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send content to webhook: {str(e)}")
        # Continue execution to return response to client even if webhook fails
    
    return jsonify(final_result)