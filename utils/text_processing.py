import tiktoken
from utils.azure_config import call_azure_api
import io
from PyPDF2 import PdfReader
import json
from models import get_prompt, get_rubric
import logging
import re

def chunk_text(text, max_tokens=3000):
    enc = tiktoken.get_encoding('cl100k_base')
    tokens = enc.encode(text)
    chunks = []
    current_chunk = []
    current_tokens = 0

    for token in tokens:
        current_chunk.append(token)
        current_tokens += 1
        if current_tokens >= max_tokens:
            chunk = enc.decode(current_chunk)
            chunks.append(chunk)
            current_chunk = []
            current_tokens = 0

    if current_chunk:
        chunk = enc.decode(current_chunk)
        chunks.append(chunk)

    logging.debug(f"Number of chunks created: {len(chunks)}")
    logging.debug(f"First chunk (truncated): {chunks[0][:100]}...")
    logging.debug(f"Last chunk (truncated): {chunks[-1][-100:]}")

    for i, chunk in enumerate(chunks):
        logging.debug(f"Chunk {i} (first 100 chars): {chunk[:100]}...")

    return chunks

def extract_statements(text_chunks, config):
    logging.debug(f"Number of chunks: {len(text_chunks)}")
    logging.debug(f"First chunk: {text_chunks[0][:100]}...")
    all_statements = []
    prompt_data = get_prompt("extract_statements")
    logging.debug(f"Retrieved prompt data: {prompt_data}")
    
    if not prompt_data:
        logging.error("Failed to retrieve prompt data for extract_statements")
        return []
    
    prompt_text = prompt_data.get("prompt_text", "")
    if not prompt_text:
        logging.error("No prompt text found for extract_statements")
        return []
    
    logging.debug(f"Prompt text: {prompt_text}")
    
    for chunk in text_chunks:
        try:
            prompt = prompt_text.replace("{chunk}", chunk)
        except Exception as e:
            logging.error(f"Error when formatting prompt: {e}")
            logging.debug(f"Prompt text: {prompt_text}")
            logging.debug(f"Chunk: {chunk}")
            continue
        
        response = call_azure_api(prompt, "statement_extraction", config)
        chunk_statements = process_api_response(response)
        all_statements.extend(chunk_statements)

    # New code to improve statements
    improved_statements = improve_statements(all_statements, config)

    logging.debug(f"Total statements extracted and improved: {len(improved_statements)}")
    return improved_statements

def improve_statements(statements, config):
    improved_statements = []
    rubric = get_rubric("statement_improvement_rubric")
    
    if not rubric:
        logging.error("Failed to retrieve rubric for statement improvement")
        return statements  # Return original statements if rubric is not found
    
    for i in range(0, len(statements), 10):
        batch = statements[i:i+10]
        prompt_data = get_prompt("improve_statements")
        
        if not prompt_data:
            logging.error("Failed to retrieve prompt for statement improvement")
            return statements  # Return original statements if prompt is not found
        
        prompt = prompt_data["prompt_text"].format(
            rubric=rubric["rubric_text"],
            statements=json.dumps(batch, indent=2)
        )
        
        response = call_azure_api(prompt, "statement_improvement", config)
        improved_batch = process_api_response(response)
        improved_statements.extend(improved_batch)
    
    return improved_statements

def extract_text_from_pdf(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + '\n'
    return text

def process_api_response(response):
    if not response or 'choices' not in response or not response['choices']:
        logging.error("Invalid or empty response from Azure API")
        return []
    
    content = response['choices'][0]['message']['content']
    content = content.strip()
    
    # Remove code block markers if present
    content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)
    
    try:
        parsed_content = json.loads(content)
        if isinstance(parsed_content, list):
            return parsed_content
        elif isinstance(parsed_content, dict) and "Statements of information" in parsed_content:
            return parsed_content["Statements of information"]
        else:
            logging.warning(f"Unexpected JSON structure: {parsed_content}")
            return []
    except json.JSONDecodeError:
        logging.error(f"Failed to parse API response as JSON: {content}")
        # Attempt to extract statements using regex
        statements = re.findall(r'"([^"]*)"', content)
        if not statements:
            statements = [s.strip() for s in content.split('\n') if s.strip()]
        return statements
