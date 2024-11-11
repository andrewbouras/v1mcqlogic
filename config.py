import os

class Config:
    SECRET_KEY = 'YOUR_SECRET_KEY'
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
    IMAGE_INSPECTION_FOLDER = os.path.join(BASE_DIR, 'image_inspection')

    API_KEY = 'YOUR_API_KEY'
    IMAGE_PATH = 'YOUR_IMAGE_PATH'
    AZURE_ENDPOINT = 'https://notes-test-1.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-02-15-preview'
    AZURE_API_KEY = 'YOUR_AZURE_API_KEY'
    AZURE_DEPLOYMENT = 'gpt-4o-mini'
    AZURE_OPENAI_KEY = '198f39bb0cf246908be7adfbc8e86357'
    AZURE_OPENAI_ENDPOINT = 'https://notes-test-1.openai.azure.com'
    AZURE_OPENAI_VERSION = '2024-02-15-preview'
    AZURE_OPENAI_DEPLOYMENT = 'gpt-4o-mini'
    TOTAL_TOKENS_PER_MINUTE = 2000000
    TOKEN_ENCODING = "cl100k_base"

    MONGODB_URI = 'mongodb+srv://andrew:Dhruv123!@serverlessinstance0.i2qxywn.mongodb.net/prompts_db?retryWrites=true&w=majority&appName=ServerlessInstance0'
    MONGO_DB_NAME = 'prompts_db'

RESOURCE_GROUP = "Note1.0"
APP_NAME = "Smartify"
APP_SERVICE_PLAN = "ASP-Note10-8cf0"
LOCATION = "Canada Central"