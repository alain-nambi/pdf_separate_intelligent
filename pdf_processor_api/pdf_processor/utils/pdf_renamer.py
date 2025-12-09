"""
Module pour renommer les PDFs avec OCR
"""

import os
import re
import fitz
from typing import Dict, Optional, Tuple
from datetime import datetime


class PDFRenamer:
    """Classe pour renommer les PDFs avec reconnaissance OCR"""
    
    def __init__(self, use_ocr: bool = False):
        """
        Initialiser le renamer
        
        Args:
            use_ocr: Utiliser l'OCR si nécessaire
        """
        self.use_ocr = use_ocr
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extraire le texte d'un PDF
        
        Args:
            pdf_path: Chemin du fichier PDF
            
        Returns:
            Texte extrait
        """
        try:
            doc = fitz.open(pdf_path)
            text = doc[0].get_text("text")  # Première page seulement
            doc.close()
            return text
        except Exception:
            return ""
    
    def extract_with_ocr(self, pdf_path: str) -> str:
        """
        Extraire le texte avec OCR (si disponible)
        
        Args:
            pdf_path: Chemin du fichier PDF
            
        Returns:
            Texte extrait avec OCR
        """
        try:
            # Importer pytesseract seulement si nécessaire
            import pytesseract
            from PIL import Image
            import io
            
            # Ouvrir le PDF
            doc = fitz.open(pdf_path)
            
            # Convertir la première page en image
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            # Appliquer l'OCR
            text = pytesseract.image_to_string(image, lang='fra')
            
            doc.close()
            return text
            
        except ImportError:
            # OCR non disponible
            return ""
        except Exception:
            return ""
    
    def find_employee_info(self, text: str) -> Optional[Dict]:
        """
        Trouver les informations de l'employé
        
        Args:
            text: Texte à analyser
            
        Returns:
            Informations de l'employé ou None
        """
        # Pattern: NOM Prénom Matricule Titre
        patterns = [
            r'([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][a-z]+)\s+(\d{5})\s+(.+)',
            r'([A-Z][A-Z\s-]*[A-Z])\s+([A-Z][a-z]+)\s+(\d{4,5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                nom = match.group(1).replace(' ', '_').upper()
                prenom = match.group(2).upper()
                matricule = str(int(match.group(3)))  # Enlever zéros de tête
                
                return {
                    'nom': nom,
                    'prenom': prenom,
                    'matricule': matricule
                }
        
        return None
    
    def find_period_info(self, text: str) -> Dict:
        """
        Trouver la période du bulletin
        
        Args:
            text: Texte à analyser
            
        Returns:
            Informations de période
        """
        # Chercher la période avec dates
        period_pattern = r'Période\s+du\s+(\d{2})/(\d{2})/(\d{2,4})'
        match = re.search(period_pattern, text)
        
        if match:
            mois_num = match.group(2)
            annee = match.group(3)
            
            # Convertir année 2 chiffres -> 4 chiffres
            if len(annee) == 2:
                annee = f"20{annee}"
            
            # Mois en abréviation
            mois_abbr = [
                'JAN', 'FEV', 'MAR', 'AVR', 'MAI', 'JUN',
                'JUL', 'AOU', 'SEP', 'OCT', 'NOV', 'DEC'
            ]
            
            try:
                mois_index = int(mois_num) - 1
                if 0 <= mois_index < 12:
                    mois = mois_abbr[mois_index]
                else:
                    mois = 'SEP'
            except ValueError:
                mois = 'SEP'
            
            return {'mois': mois, 'annee': annee}
        
        # Fallback: date actuelle
        today = datetime.now()
        mois = ['JAN', 'FEV', 'MAR', 'AVR', 'MAI', 'JUN',
                'JUL', 'AOU', 'SEP', 'OCT', 'NOV', 'DEC'][today.month - 1]
        
        return {'mois': mois, 'annee': str(today.year)}
    
    def rename_pdf(self, pdf_path: str, output_dir: str) -> Dict:
        """
        Renommer un fichier PDF
        
        Args:
            pdf_path: Chemin du fichier PDF à renommer
            output_dir: Dossier de sortie
            
        Returns:
            Résultat du renommage
        """
        try:
            # Extraire le texte
            text = self.extract_text(pdf_path)
            
            # Si pas de texte et OCR activé, essayer avec OCR
            if not text.strip() and self.use_ocr:
                text = self.extract_with_ocr(pdf_path)
            
            # Chercher les informations
            employee_info = self.find_employee_info(text)
            period_info = self.find_period_info(text)
            
            if not employee_info:
                return {
                    'success': False,
                    'error': 'Informations employé non trouvées',
                    'original_file': os.path.basename(pdf_path)
                }
            
            # Générer le nouveau nom
            new_name = f"{employee_info['matricule']}_{employee_info['nom']}_{employee_info['prenom']}_{period_info['mois']}{period_info['annee']}.pdf"
            
            # Créer le dossier de sortie
            os.makedirs(output_dir, exist_ok=True)
            
            # Chemin de sortie
            output_path = os.path.join(output_dir, new_name)
            
            # Gérer les doublons
            counter = 1
            while os.path.exists(output_path):
                name, ext = os.path.splitext(new_name)
                output_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # Copier le fichier
            import shutil
            shutil.copy2(pdf_path, output_path)
            
            return {
                'success': True,
                'original_file': os.path.basename(pdf_path),
                'new_file': os.path.basename(output_path),
                'output_path': output_path,
                'matricule': employee_info['matricule'],
                'nom': employee_info['nom'],
                'prenom': employee_info['prenom'],
                'mois': period_info['mois'],
                'annee': period_info['annee'],
                'has_duplicate': counter > 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_file': os.path.basename(pdf_path)
            }