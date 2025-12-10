import fitz
import os
import re
import shutil
from datetime import datetime
from typing import Optional, Tuple
import tempfile
from PIL import Image
import pytesseract
import io


def extract_text_with_fallback(pdf_path: str, use_ocr: bool = False) -> str:
    """
    Extraire le texte d'un PDF avec fallback OCR si nécessaire
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""

        for page_num in range(min(2, len(doc))):  # Lire les 2 premières pages max
            page = doc[page_num]
            page_text = page.get_text("text")

            # Si le texte est vide ou trop court, essayer OCR
            if use_ocr and (not page_text or len(page_text.strip()) < 50):
                try:
                    # Convertir la page en image
                    pix = page.get_pixmap(dpi=200)
                    img_data = pix.tobytes("ppm")
                    image = Image.open(io.BytesIO(img_data))

                    # OCR en français
                    page_text = pytesseract.image_to_string(image, lang='fra')
                except ImportError:
                    pass  # OCR non disponible

            text += page_text + "\n"

        doc.close()
        return text

    except Exception as e:
        print(f"⚠️ Erreur lecture PDF: {e}")
        return ""


def extract_employee_info(text: str) -> Optional[Tuple[str, str, str]]:
    """
    Extraire nom, prénom et matricule du texte
    Plusieurs patterns pour plus de robustesse
    """

    # Normalize text for better matching
    text = text.upper()

    # Prioritize patterns where ID has 4-5 digits and is after names (most common)
    patterns = [
        # NOM Prénom 4-5 chiffres (most common format)
        r'([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][A-Z\s-]*[A-Z])\s+(\d{4,5})\b',

        # Ligne contenant les 3 informations avec ID 4-5
        r'([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][A-Z\s-]*[A-Z]).*?(\d{4,5})\b',

        # Format avec espaces variables et ID 4-5
        r'([A-Z]{2,})\s+([A-Z]{2,})\s+(\d{4,5})\b',

        # Plus flexible pour OCR avec ID 4-5
        r'([A-Z\s-]{2,}?)\s+([A-Z\s-]{2,}?)\s+(\d{4,5})\b',

        # Recherche matricule puis noms avant (ID 4-5)
        r'(\d{4,5})\b.*?(?<= )([A-Z\s-]{2,}?)\s+([A-Z\s-]{2,}?)(?=\s|$)',

        # Fallback: ID NOM Prénom (ID can be 1-5 digits)
        r'(\d{1,5})\s+([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][A-Z\s-]*[A-Z])\b',

        # NOM Prénom chiffres (1-5 digits, less priority)
        r'([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][A-Z\s-]*[A-Z])\s+(\d{1,5})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Handle different capturing group orders
            if len(match.groups()) >= 3:
                if pattern == patterns[5]:  # Special case for matricule-first pattern
                    matricule = str(int(match.group(1).strip()))
                    nom = re.sub(r'\s+', '_', match.group(2).strip()).upper()
                    prenom = re.sub(r'\s+', '_', match.group(3).strip()).upper()
                else:
                    nom = re.sub(r'\s+', '_', match.group(1).strip()).upper()
                    prenom = re.sub(r'\s+', '_', match.group(2).strip()).upper()
                    matricule = str(int(match.group(3).strip()))  # Enlève les zéros de tête
                return matricule, nom, prenom

    return None


def extract_period_from_dates(text: str) -> Tuple[str, str]:
    """
    Extraire le mois et l'année à partir des dates de période
    Format: Période du 01/09/25 au 30/09/25
    """

    # Chercher la période avec dates
    period_patterns = [
        r'Période\s+du\s+(\d{2})/(\d{2})/(\d{2,4})\s+au\s+(\d{2})/(\d{2})/(\d{2,4})',
        r'du\s+(\d{2})/(\d{2})/(\d{2,4})\s+au\s+(\d{2})/(\d{2})/(\d{2,4})',
        r'(\d{2})/(\d{2})/(\d{2,4})\s+à\s+(\d{2})/(\d{2})/(\d{2,4})',
    ]

    for pattern in period_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                # Prendre la première date (début de période)
                jour = match.group(1)
                mois = match.group(2)
                annee = match.group(3)

                # Gérer les années sur 2 chiffres
                if len(annee) == 2:
                    annee = "20" + annee

                # Vérifier la validité du mois
                if mois.isdigit() and 1 <= int(mois) <= 12:
                    mois_abbr = [
                        'JAN', 'FEV', 'MAR', 'AVR', 'MAI', 'JUN',
                        'JUL', 'AOU', 'SEP', 'OCT', 'NOV', 'DEC'
                    ][int(mois) - 1]

                    return mois_abbr, annee

            except (IndexError, ValueError):
                continue

    # Fallback: chercher le mois dans le texte
    mois_fr = re.search(r'(Janvier|Février|Mars|Avril|Mai|Juin|Juillet|Août|Septembre|Octobre|Novembre|Décembre)', text, re.IGNORECASE)
    annee_match = re.search(r'(20\d{2})', text)

    if mois_fr:
        mois_map = {
            'Janvier': 'JAN', 'Février': 'FEV', 'Mars': 'MAR',
            'Avril': 'AVR', 'Mai': 'MAI', 'Juin': 'JUN',
            'Juillet': 'JUL', 'Août': 'AOU', 'Septembre': 'SEP',
            'Octobre': 'OCT', 'Novembre': 'NOV', 'Décembre': 'DEC'
        }
        mois_abbr = mois_map.get(mois_fr.group(1).capitalize(), 'SEP')
        annee = annee_match.group(1) if annee_match else "2025"
        return mois_abbr, annee

    # Fallback ultime: mois et année actuels
    today = datetime.now()
    mois_abbr = ['JAN', 'FEV', 'MAR', 'AVR', 'MAI', 'JUN',
                 'JUL', 'AOU', 'SEP', 'OCT', 'NOV', 'DEC'][today.month - 1]
    return mois_abbr, str(today.year)


def generate_pay_slip_filename(employee_info: Optional[Tuple[str, str, str]], period_info: Tuple[str, str], page_num: int) -> str:
    """
    Génère un nom de fichier basé sur les infos employé et période
    Format: {ID}_{LAST_NAME}_{FIRST_NAME}_{MONTH}{YEAR}.pdf
    """
    if employee_info:
        matricule, nom, prenom = employee_info
        mois, annee = period_info
        return f"{matricule}_{nom}_{prenom}_{mois}{annee}.pdf"

    # Fallback si pas d'infos employé
    mois, annee = period_info
    return f"UNKNOWN_{page_num:03d}_PAYSLIP_{mois}{annee}.pdf"


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


def process_pay_slip_pdf(pdf_path: str, page_num: int, output_dir: str, use_ocr: bool = False) -> str:
    """
    Traiter un bulletin de paie PDF avec OCR spécialisé
    """
    # Extraire le texte
    text = extract_text_with_fallback(pdf_path, use_ocr)

    if not text.strip():
        # Fallback générique si aucun texte
        text = extract_text_from_pdf(pdf_path) or ""

    employee_info = None
    period_info = extract_period_from_dates(text)

    # Tenter l'extraction OCR si infos employé pas trouvées
    if not employee_info and not use_ocr:
        try:
            import pytesseract
            employee_info = extract_employee_info_from_ocr(pdf_path)
        except ImportError:
            pass

    # Si toujours pas d'infos employé, essayer avec OCR forcé
    if not employee_info:
        try:
            text_ocr = extract_text_with_fallback(pdf_path, use_ocr=True)
            if text_ocr != text:
                employee_info = extract_employee_info(text_ocr)
        except:
            pass

    # Générer le nom de fichier
    new_filename = generate_pay_slip_filename(employee_info, period_info, page_num)
    new_path = os.path.join(output_dir, new_filename)

    # Gérer les doublons
    counter = 1
    original_new_path = new_path
    while os.path.exists(new_path):
        base, ext = os.path.splitext(original_new_path)
        new_path = os.path.join(output_dir, f"{base}_{counter}{ext}")
        counter += 1

    # Renommer/copier
    shutil.move(pdf_path, new_path)

    return new_path


def extract_employee_info_from_ocr(pdf_path: str) -> Optional[Tuple[str, str, str]]:
    """
    Extraire les infos employé directement via OCR complet
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("ppm")
        image = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(image, lang='fra')
        doc.close()
        return extract_employee_info(text)
    except Exception as e:
        print(f"OCR extract failed: {e}")
        return None


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from the first page of a PDF using OCR (legacy function)
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

        # Clean text (less aggressive cleaning for pay slips)
        text = text.strip()

        doc.close()
        return text or "Unknown"
    except Exception as e:
        print(f"OCR failed for {pdf_path}: {e}")
        return "Unknown"


# Alias pour compatibilité
process_single_page_pdf = process_pay_slip_pdf
