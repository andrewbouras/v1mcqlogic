from flask import Blueprint, request, jsonify, current_app
import logging
import json
import requests
import re
from json import JSONEncoder
from utils.azure_config import call_azure_api
from models import get_prompt, get_configuration, get_rubric

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)

generate_bp = Blueprint('generate', __name__)

def generate_intro_questions(statements, question_style, use_bolding, config):
    prompt_data = get_prompt("generate_mcqs")
    style_config = get_configuration("question_styles")
    bolding_config = get_configuration("bolding_options")

    style_details = style_config["config_values"][question_style]
    bolding_details = bolding_config["config_values"][str(use_bolding).lower()]

    intro_prompt = prompt_data["intro_prompt"].format(
        statements=json.dumps(statements, indent=2),
        style_example=json.dumps(style_details['example'], indent=2),
        bolding_example=json.dumps(bolding_details['example'], indent=2)
    )

    logging.debug(f"Generated intro prompt: {intro_prompt[:500]}...")
    logging.info(f"Full intro prompt being sent to Azure OpenAI: {intro_prompt}")

    response = call_azure_api(intro_prompt, "question_generation", config)
    raw_questions = process_api_response(response)

    # Process the raw questions to ensure correct formatting
    formatted_questions = []
    for q in raw_questions:
        # Ensure answer choices are in alphabetical order
        answer_choices = sorted(q['answerChoices'], key=lambda x: x['value'].lower())
        
        formatted_question = {
            "question": q['question'],
            "answerChoices": answer_choices,
            "explanation": q['explanation'],
            "concept": q['concept'],
            "is_intro_question": True
        }
        formatted_questions.append(formatted_question)

    return formatted_questions

def generate_mcqs(
    text,
    statements,
    num_questions,
    question_style,
    use_bolding,
    config,
    intro_questions=False
):
    logging.debug(f"Entering generate_mcqs with parameters: intro_questions={intro_questions}")

    all_questions = []
    prompt_data = get_prompt("generate_mcqs")
    style_config = get_configuration("question_styles")
    bolding_config = get_configuration("bolding_options")

    if question_style not in style_config["config_values"]:
        raise ValueError(f"Invalid question style: {question_style}")

    style_details = style_config["config_values"][question_style]
    bolding_details = bolding_config["config_values"][str(use_bolding).lower()]

    prompt_text = prompt_data["regular_prompt"]

    # Generate questions in batches of 5
    for i in range(0, num_questions, 5):
        batch_size = min(5, num_questions - i)
        
        prompt = prompt_text.format(
            num_questions=batch_size,
            question_style=f"{question_style} (complexity level: {style_details['complexity_level']})",
            style_example=json.dumps(style_details['example'], indent=2),
            bolding_format=bolding_details['formatting'],
            bolding_example=json.dumps(bolding_details['example'], indent=2),
            text=text,
            statements=json.dumps(statements, indent=2),
            num_answer_choices=5
        )

        logging.debug(f"Generated prompt for batch {i//5 + 1}: {prompt[:500]}...")
        logging.info(f"Full prompt being sent to Azure OpenAI for batch {i//5 + 1}: {prompt}")

        response = call_azure_api(prompt, "question_generation", config)
        batch_questions = process_api_response(response)
        
        # Ensure we have the correct number of questions for this batch
        while len(batch_questions) < batch_size:
            logging.warning(f"Batch {i//5 + 1} returned {len(batch_questions)} questions instead of {batch_size}. Regenerating missing questions.")
            additional_prompt = prompt_text.format(
                num_questions=batch_size - len(batch_questions),
                question_style=f"{question_style} (complexity level: {style_details['complexity_level']})",
                style_example=json.dumps(style_details['example'], indent=2),
                bolding_format=bolding_details['formatting'],
                bolding_example=json.dumps(bolding_details['example'], indent=2),
                text=text,
                statements=json.dumps(statements, indent=2),
                num_answer_choices=5
            )
            additional_response = call_azure_api(additional_prompt, "question_generation", config)
            additional_questions = process_api_response(additional_response)
            batch_questions.extend(additional_questions)
        
        all_questions.extend(batch_questions[:batch_size])  # Ensure we don't add more than needed

    # Improve questions
    improved_questions = improve_questions(all_questions, config)

    final_result = {
        "ID": config["ID"],
        "questions": improved_questions
    }

    return final_result

def process_api_response(response):
    content = response['choices'][0]['message']['content']
    try:
        # Remove code block markers if present
        content = content.replace('```json\n', '').replace('\n```', '')
        
        # Try to parse the entire content as a JSON array
        try:
            questions_data = json.loads(content)
            if isinstance(questions_data, list):
                return questions_data
        except json.JSONDecodeError:
            pass  # If this fails, we'll try individual parsing
        
        # If parsing as an array fails, try to extract individual JSON objects
        json_objects = re.findall(r'\{[^{}]*\}', content)
        
        questions_data = []
        for json_obj in json_objects:
            try:
                question_data = json.loads(json_obj)
                questions_data.append(question_data)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse individual JSON object: {json_obj}")
                logging.error(f"JSON decode error: {str(e)}")
        
        if not questions_data:
            logging.error(f"No valid JSON objects found in the response")
        
        return questions_data
    except Exception as e:
        logging.error(f"Failed to process API response: {content}")
        logging.error(f"Error: {str(e)}")
        return []

@generate_bp.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        logging.debug(f"Received data: {data}")

        # Validate and extract parameters
        required_fields = ['ID', 'text', 'num_questions', 'question_style', 'use_bolding']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        task_id = data['ID']
        text = data['text']
        num_questions = data['num_questions']
        question_style = data['question_style']
        use_bolding = data['use_bolding']
        intro_questions = data.get('intro_questions', False)

        # Validate input types
        style_config = get_configuration("question_styles")
        if question_style not in style_config["config_values"]:
            return jsonify({"error": f"Invalid question style: {question_style}"}), 400
        if not isinstance(use_bolding, bool):
            return jsonify({"error": "Invalid bolding option"}), 400
        if not isinstance(num_questions, int) or num_questions <= 0:
            return jsonify({"error": "Invalid number of questions"}), 400

        config = {
            'AZURE_OPENAI_KEY': current_app.config['AZURE_OPENAI_KEY'],
            'AZURE_OPENAI_ENDPOINT': current_app.config['AZURE_OPENAI_ENDPOINT'],
            'AZURE_OPENAI_VERSION': current_app.config['AZURE_OPENAI_VERSION'],
            'AZURE_OPENAI_DEPLOYMENT': current_app.config['AZURE_OPENAI_DEPLOYMENT'],
            'ID': task_id  # Add this line
        }

        # Condense statements if necessary
        statements = data.get('Statements of information', [])
        condensed_statements = condense_statements(statements, num_questions)

        questions_data = generate_mcqs(
            text,
            condensed_statements,
            num_questions,
            question_style,
            use_bolding,
            config,
            intro_questions=intro_questions
        )

        logging.info(f"Generated questions data: {questions_data}")

        # Ensure we have the correct number of questions
        if len(questions_data['questions']) != num_questions:
            logging.error(f"Generated {len(questions_data['questions'])} questions instead of {num_questions}. Adjusting...")
            if len(questions_data['questions']) > num_questions:
                questions_data['questions'] = questions_data['questions'][:num_questions]
            else:
                while len(questions_data['questions']) < num_questions:
                    additional_questions = generate_mcqs(
                        text,
                        condensed_statements,
                        num_questions - len(questions_data['questions']),
                        question_style,
                        use_bolding,
                        config,
                        intro_questions=False
                    )
                    questions_data['questions'].extend(additional_questions['questions'])
                questions_data['questions'] = questions_data['questions'][:num_questions]

        final_result = questions_data  # Use the result directly

        logging.info(f"Final result before sending to webhook: {final_result}")

        # Send generated questions to the webhook
        webhook_url = "https://webhook.site/681b6610-35d6-4604-8461-ce1812d4bc3e"
        json_safe_result = {
            "ID": final_result["ID"],
            "questions": [
                {
                    "question": q.get("question", ""),
                    "answerChoices": sorted(
                        [
                            {
                                "value": choice["value"] if isinstance(choice, dict) else str(choice),
                                "correct": choice.get("correct", False) if isinstance(choice, dict) else False
                            }
                            for choice in q.get("answerChoices", [])
                        ],
                        key=lambda x: x['value'].lower()
                    ),
                    "explanation": q.get("explanation", ""),
                    "concept": q.get("concept", "")
                }
                for q in final_result["questions"]
            ]
        }
        
        response = requests.post(webhook_url, json=json_safe_result)
        if response.status_code == 200:
            logging.info(f"Successfully sent questions for task {task_id} to webhook")
        else:
            logging.error(f"Failed to send questions for task {task_id} to webhook. Status code: {response.status_code}")

        return jsonify({"message": "Questions generated and sent successfully"}), 200

    except Exception as e:
        logging.error(f"Error in generate function: {str(e)}", exc_info=True)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    
    
def condense_statements(statements, num_questions):
    if len(statements) <= num_questions:
        return statements
    
    statements_per_question = len(statements) // num_questions
    remainder = len(statements) % num_questions
    
    condensed = []
    start = 0
    for i in range(num_questions):
        end = start + statements_per_question + (1 if i < remainder else 0)
        condensed.append(" ".join(statements[start:end]))
        start = end
    
    return condensed

def improve_questions(questions, config):
    improved_questions = []
    rubric = get_rubric("mcq_improvement_rubric")
    
    if not rubric:
        logging.error("Failed to retrieve rubric for question improvement")
        return questions  # Return original questions if rubric is not found
    
    logging.debug(f"Retrieved rubric: {rubric}")
    
    for i in range(0, len(questions), 5):
        batch = questions[i:i+5]
        prompt_data = get_prompt("improve_mcqs")
        
        if not prompt_data:
            logging.error("Failed to retrieve prompt for question improvement")
            return questions  # Return original questions if prompt is not found
        
        prompt = prompt_data["prompt_text"].format(
            rubric=rubric["rubric_text"],
            questions=json.dumps(batch, indent=2)
        )
        
        logging.debug(f"Sending improvement prompt for batch {i//5 + 1}: {prompt[:500]}...")
        
        response = call_azure_api(prompt, "question_improvement", config)
        logging.debug(f"Received response for batch {i//5 + 1}: {response}")
        
        improved_batch = process_api_response(response)
        logging.debug(f"Processed improved batch {i//5 + 1}: {improved_batch}")
        
        # Ensure we don't lose any questions during improvement
        while len(improved_batch) < len(batch):
            logging.warning(f"Improvement reduced number of questions in batch {i//5 + 1}. Regenerating missing questions.")
            missing_count = len(batch) - len(improved_batch)
            additional_prompt = prompt_data["prompt_text"].format(
                rubric=rubric["rubric_text"],
                questions=json.dumps(batch[-missing_count:], indent=2)
            )
            additional_response = call_azure_api(additional_prompt, "question_improvement", config)
            additional_improved = process_api_response(additional_response)
            improved_batch.extend(additional_improved)
        
        improved_questions.extend(improved_batch[:len(batch)])  # Ensure we don't add more than the original batch size
    
    logging.info(f"Total improved questions: {len(improved_questions)}")
    return improved_questions
