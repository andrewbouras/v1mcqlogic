from flask import Blueprint, request, jsonify
from models import create_prompt, update_prompt, get_prompt, delete_prompt, create_configuration, update_configuration, get_configuration, delete_configuration

prompts_bp = Blueprint('prompts', __name__)

@prompts_bp.route('/prompts', methods=['POST'])
def add_or_update_prompt():
    data = request.json
    prompt_name = data['prompt_name']
    existing_prompt = get_prompt(prompt_name)
    
    if existing_prompt:
        update_prompt(prompt_name, data.get('prompt_text'), data.get('variables'), data.get('description'))
        return jsonify({"message": "Prompt updated successfully"}), 200
    else:
        create_prompt(prompt_name, data['prompt_text'], data['variables'], data['description'])
        return jsonify({"message": "Prompt added successfully"}), 201

@prompts_bp.route('/prompts/<prompt_name>', methods=['GET'])
def fetch_prompt(prompt_name):
    prompt = get_prompt(prompt_name)
    if prompt:
        return jsonify(prompt), 200
    else:
        return jsonify({"error": "Prompt not found"}), 404

@prompts_bp.route('/prompts/<prompt_name>', methods=['DELETE'])
def remove_prompt(prompt_name):
    delete_prompt(prompt_name)
    return jsonify({"message": "Prompt deleted successfully"}), 200

@prompts_bp.route('/configurations', methods=['POST'])
def add_configuration():
    data = request.json
    create_configuration(data['config_name'], data['config_values'], data['description'])
    return jsonify({"message": "Configuration added successfully"}), 201

@prompts_bp.route('/configurations/<config_name>', methods=['PUT'])
def edit_configuration(config_name):
    data = request.json
    update_configuration(config_name, data.get('config_values'), data.get('description'))
    return jsonify({"message": "Configuration updated successfully"}), 200

@prompts_bp.route('/configurations/<config_name>', methods=['GET'])
def fetch_configuration(config_name):
    config = get_configuration(config_name)
    if config:
        return jsonify(config), 200
    else:
        return jsonify({"error": "Configuration not found"}), 404

@prompts_bp.route('/configurations/<config_name>', methods=['DELETE'])
def remove_configuration(config_name):
    delete_configuration(config_name)
    return jsonify({"message": "Configuration deleted successfully"}), 200