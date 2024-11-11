import sys
import traceback
from flask import Blueprint, request, jsonify, current_app
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from utils.azure_config import call_azure_api
from utils.rate_limiter import AdaptiveRateLimiter
import json
import json5
import requests  # Import requests library
from app.utils import get_configuration, get_prompt
from utils.azure_config import call_azure_api  # Ensure these imports are correct based on your project structure

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

similar_bp = Blueprint('similar', __name__)

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

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
    num_questions = data.get('num_questions')
    style = data.get('style')
    question = data.get('question')
    text = data.get('text')
    bold = data.get('bold')

    prompt_data = get_prompt("generate_similar_questions")
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
    
    prompt = prompt_data["prompt_text"].format(
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

    final_result = {"ID": response_id, "questions": questions_data['questions']}
    logging.debug(f"Final result before formatting: {final_result}")

    # Send generated questions to the specified endpoint
    webhook_url = "https://webhook.site/08537c49-227d-4c6f-bf13-de1fad2c353f"
    webhook_response = requests.post(webhook_url, json=final_result)
    
    if webhook_response.status_code == 200:
        logging.info("Successfully sent the content to the webhook endpoint.")
    else:
        logging.error(f"Failed to send the content to the webhook endpoint. Status code: {webhook_response.status_code}")

    return jsonify(final_result)