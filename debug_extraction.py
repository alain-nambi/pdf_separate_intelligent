#!/usr/bin/env python3
"""
Debug script for pay slip OCR extraction
"""

import fitz
from PIL import Image
import io
import re
from typing import Optional, Tuple

from app.utils import extract_employee_info


def analyze_pdf(pdf_path):
    print(f"Analyzing: {pdf_path}")
    print("=" * 50)

    # Method 1: Direct PDF text extraction
    print("1. DIRECT PDF TEXT EXTRACTION:")
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(min(2, len(doc))):
            page = doc.load_page(page_num)
            text += page.get_text("text") + "\n"
        doc.close()

        print(f"Text length: {len(text)}")
        print(f"Text preview: {text[:500]}...")
        print()

        employee_info = extract_employee_info(text)
        if employee_info:
            matricule, nom, prenom = employee_info
            print(f"✅ FOUND EMPLOYEE: Matricule={matricule}, Nom={nom}, Prénom={prénom}")
        else:
            print("❌ No employee info found in direct text")

    except Exception as e:
        print(f"❌ Error extracting text: {e}")

    print("\n" + "=" * 50)
    print("2. OCR TEXT EXTRACTION:")
    # Method 2: OCR
    try:
        import pytesseract
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("ppm")
        image = Image.open(io.BytesIO(img_data))
        ocr_text = pytesseract.image_to_string(image, lang='fra')
        doc.close()

        print(f"OCR text length: {len(ocr_text)}")
        print(f"OCR text preview: {ocr_text[:500]}...")
        print()

        employee_info_ocr = extract_employee_info(ocr_text)
        if employee_info_ocr:
            matricule, nom, prenom = employee_info_ocr
            print(f"✅ FOUND EMPLOYEE IN OCR: Matricule={matricule}, Nom={nom}, Prénom={prénom}")
        else:
            print("❌ No employee info found in OCR text")

    except ImportError:
        print("❌ pytesseract not available")
    except Exception as e:
        print(f"❌ OCR Error: {e}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    import sys
    import glob
    import os

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf_path', help='Path to specific PDF file')
    args = parser.parse_args()

    if not args.pdf_path:
        print("Usage: python debug_extraction.py <pdf_path>")
        sys.exit(1)

    if not os.path.exists(args.pdf_path):
        print(f"File not found: {args.pdf_path}")
        sys.exit(1)

    analyze_pdf(args.pdf_path)
