import fitz  # PyMuPDF
import os
import tempfile
from PIL import Image
import pytesseract
import re

def split_pdf_one_page_per_file(input_pdf: str, output_dir: str):
    """
    Crée un fichier PDF séparé pour chaque page
    """
    # Créer le dossier de sortie
    os.makedirs(output_dir, exist_ok=True)

    # Ouvrir le PDF
    doc = fitz.open(input_pdf)
    total_pages = doc.page_count

    page_files = []  # Liste des chemins de fichiers créés

    # Pour CHAQUE page, créer un PDF séparé
    for page_num in range(total_pages):
        # Créer un nouveau document vide
        new_doc = fitz.open()

        # Ajouter UNIQUEMENT cette page
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

        # Nom temporaire du fichier
        output_filename = f"temp_page_{page_num + 1:03d}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        # Sauvegarder
        new_doc.save(output_path)
        new_doc.close()

        page_files.append(output_path)

    # Fermer le document original
    doc.close()

    return page_files


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from the first page of a PDF using OCR
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)

        # Convert to image with better settings
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("png")

        # Handle potential null bytes
        if b'\x00' in img_bytes:
            # Alternative: save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                pix.save(tmp.name)
                img = Image.open(tmp.name)
        else:
            from io import BytesIO
            img = Image.open(BytesIO(img_bytes))

        # OCR
        text = pytesseract.image_to_string(img)

        # Clean text
        text = text.strip()
        # Keep only alphanumeric, spaces, hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'\s+', ' ', text)

        doc.close()
        return text or "Unknown"
    except Exception as e:
        print(f"OCR failed for {pdf_path}: {e}")
        return "Unknown"


def generate_filename(text: str, page_num: int) -> str:
    """
    Generate a safe filename from extracted text
    """
    if text:
        # Truncate to 50 chars
        filename_part = text[:50].strip()
        # Replace spaces with underscores
        filename_part = re.sub(r'\s+', '_', filename_part)
        # Remove trailing underscores
        filename_part = filename_part.rstrip('_')
        if filename_part:
            return f"page_{page_num:03d}_{filename_part}.pdf"
    # Fallback
    return f"page_{page_num:03d}.pdf"


def process_single_page_pdf(pdf_path: str, page_num: int, output_dir: str) -> str:
    """
    For a single page PDF: extract text, generate filename, rename
    """
    text = extract_text_from_pdf(pdf_path)
    new_filename = generate_filename(text, page_num)
    new_path = os.path.join(output_dir, new_filename)

    os.rename(pdf_path, new_path)
    return new_path
