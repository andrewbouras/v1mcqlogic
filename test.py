from pymongo import MongoClient
from config import Config

client = MongoClient(Config.MONGODB_URI)
db = client.prompts_db
prompts_collection = db.prompts

extract_statements_prompt = prompts_collection.find_one({"prompt_name": "extract_statements"})
print(extract_statements_prompt)
