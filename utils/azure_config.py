import requests
import logging
import openai
from config import Config

def get_azure_credentials():
    return Config.AZURE_OPENAI_KEY

openai.api_type = "azure"
openai.api_base = Config.AZURE_OPENAI_ENDPOINT
openai.api_version = Config.AZURE_OPENAI_VERSION
openai.api_key = get_azure_credentials()

def call_azure_api(prompt, deployment_id, config):
    azure_openai_endpoint = config['AZURE_OPENAI_ENDPOINT']
    azure_openai_key = config['AZURE_OPENAI_KEY']
    deployment_name = config['AZURE_OPENAI_DEPLOYMENT']
    api_version = config['AZURE_OPENAI_VERSION']

    headers = {
        "Content-Type": "application/json",
        "api-key": azure_openai_key,
    }

    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 3900
    }

    logging.debug(f"Sending payload to Azure API: {payload}")

    url = f"{azure_openai_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        logging.debug(f"Azure API response: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Azure API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status code: {e.response.status_code}")
            logging.error(f"Response content: {e.response.text}")
        return None  # Return None instead of raising an exception
