from pymongo import MongoClient
from datetime import datetime
from config import Config

# Use the MongoDB URI from the Config class
client = MongoClient(Config.MONGODB_URI)
db = client[Config.MONGO_DB_NAME]  # Changed from MONGODB_NAME to MONGO_DB_NAME
prompts_collection = db['prompts']
configurations_collection = db['configurations']

def create_prompt(prompt_name, prompt_text, variables, description):
    prompt = {
        "prompt_name": prompt_name,
        "prompt_text": prompt_text,
        "variables": variables,
        "metadata": {
            "description": description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
    prompts_collection.insert_one(prompt)

def update_prompt(prompt_name, prompt_text=None, variables=None, description=None):
    update_fields = {}
    if prompt_text:
        update_fields["prompt_text"] = prompt_text
    if variables:
        update_fields["variables"] = variables
    if description:
        update_fields["metadata.description"] = description
    update_fields["metadata.updated_at"] = datetime.utcnow()
    
    prompts_collection.update_one({"prompt_name": prompt_name}, {"$set": update_fields})

def get_prompt(prompt_name):
    prompt = db.prompts.find_one({"prompt_name": prompt_name})
    if prompt:
        return prompt
    else:
        return None

def delete_prompt(prompt_name):
    prompts_collection.delete_one({"prompt_name": prompt_name})

def create_configuration(config_name, config_values, description):
    configuration = {
        "config_name": config_name,
        "config_values": config_values,
        "metadata": {
            "description": description,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    }
    configurations_collection.insert_one(configuration)

def update_configuration(config_name, config_values=None, description=None):
    update_fields = {}
    if config_values:
        update_fields["config_values"] = config_values
    if description:
        update_fields["metadata.description"] = description
    update_fields["metadata.updated_at"] = datetime.utcnow()
    
    configurations_collection.update_one({"config_name": config_name}, {"$set": update_fields})

def get_configuration(config_name):
    config = db.configurations.find_one({"config_name": config_name})
    if config:
        return config
    else:
        return None

def delete_configuration(config_name):
    configurations_collection.delete_one({"config_name": config_name})

def get_rubric(rubric_name):
    rubric = db.question_rubrics.find_one({"rubric_name": rubric_name})
    if rubric:
        return rubric
    else:
        return None
