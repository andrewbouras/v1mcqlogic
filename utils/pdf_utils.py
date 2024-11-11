import fitz
import os
import uuid
from PIL import Image
import logging

def ocr_pdf(file_path):
    try:
        logging.info(f"Converting PDF to images: {file_path}")
        pdf_document = fitz.open(file_path)
        images = []
        folder_name = f"pdf_images_{uuid.uuid4().hex[:8]}"
        folder_path = os.path.join(os.path.dirname(file_path), folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        for page_number in range(len(pdf_document)):
            page = pdf_document.load_page(page_number)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_path = os.path.join(folder_path, f"page_{page_number + 1}.png")
            img.save(img_path)
            images.append((page_number + 1, img, img_path))

        logging.info(f"Converted {len(images)} pages to images")
        logging.info(f"Images saved in folder: {folder_path}")
        return images, folder_path
    except Exception as e:
        logging.error(f"Error in ocr_pdf: {str(e)}")
        logging.exception("Full traceback:")
        raise