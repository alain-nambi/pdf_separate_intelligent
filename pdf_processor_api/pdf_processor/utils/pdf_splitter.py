"""
Module pour séparer un PDF en pages individuelles
"""

import os
import fitz  # PyMuPDF
from typing import List, Dict


class PDFSplitter:
    """Classe pour séparer un PDF en pages individuelles"""
    
    @staticmethod
    def split_pdf_by_page(pdf_path: str, output_dir: str) -> Dict:
        """
        Séparer un PDF en fichiers individuels - 1 page = 1 PDF
        
        Args:
            pdf_path: Chemin du fichier PDF source
            output_dir: Dossier de sortie pour les pages séparées
            
        Returns:
            Dictionnaire avec les résultats
        """
        try:
            # Créer le dossier de sortie
            os.makedirs(output_dir, exist_ok=True)
            
            # Ouvrir le PDF source
            source_pdf = fitz.open(pdf_path)
            total_pages = source_pdf.page_count
            
            # Liste pour stocker les chemins des fichiers créés
            created_files = []
            
            # Pour chaque page, créer un PDF séparé
            for page_num in range(total_pages):
                # Créer un nouveau PDF vide
                new_pdf = fitz.open()
                
                # Ajouter uniquement la page courante
                new_pdf.insert_pdf(source_pdf, from_page=page_num, to_page=page_num)
                
                # Nom du fichier pour cette page
                page_filename = f"page_{page_num + 1:03d}.pdf"
                page_path = os.path.join(output_dir, page_filename)
                
                # Sauvegarder le PDF d'une seule page
                new_pdf.save(page_path)
                new_pdf.close()
                
                # Ajouter à la liste
                created_files.append({
                    'page_number': page_num + 1,
                    'filename': page_filename,
                    'path': page_path,
                    'size': os.path.getsize(page_path)
                })
            
            # Fermer le PDF source
            source_pdf.close()
            
            # Retourner les résultats
            return {
                'success': True,
                'total_pages': total_pages,
                'output_dir': output_dir,
                'files': created_files,
                'source_file': os.path.basename(pdf_path)
            }
            
        except Exception as e:
            # En cas d'erreur
            return {
                'success': False,
                'error': str(e),
                'total_pages': 0,
                'files': []
            }
    
    @staticmethod
    def validate_pdf(file_path: str) -> bool:
        """
        Valider qu'un fichier est un PDF valide
        
        Args:
            file_path: Chemin du fichier à valider
            
        Returns:
            True si le fichier est un PDF valide
        """
        try:
            # Vérifier l'extension
            if not file_path.lower().endswith('.pdf'):
                return False
            
            # Vérifier que le fichier existe
            if not os.path.exists(file_path):
                return False
            
            # Essayer d'ouvrir le PDF
            with fitz.open(file_path) as doc:
                # Vérifier qu'il a au moins une page
                return len(doc) > 0
                
        except Exception:
            return False