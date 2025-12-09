"""
Tâches Celery pour le traitement asynchrone
"""

import os
import uuid
import shutil
from datetime import datetime
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import ProcessingTask, ProcessedPage
from .utils.pdf_splitter import PDFSplitter
from .utils.pdf_renamer import PDFRenamer


@shared_task(bind=True)
def process_pdf_task(self, task_id: str, pdf_path: str, use_ocr: bool, output_dir: str):
    """
    Tâche principale pour traiter un PDF
    
    Étapes:
    1. Séparer le PDF en pages individuelles
    2. Renommer chaque page avec OCR
    3. Mettre à jour la base de données
    """
    
    try:
        # Récupérer la tâche
        task = ProcessingTask.objects.get(task_id=task_id)
        task.status = 'processing'
        task.started_at = timezone.now()
        task.save()
        
        print(f"🎯 Démarrage du traitement: {task.original_filename}")
        
        # Étape 1: Séparer le PDF en pages
        print("📄 Étape 1: Séparation du PDF en pages...")
        
        # Créer un dossier pour les pages séparées
        split_dir = os.path.join(settings.MEDIA_ROOT, 'split_pages', task_id)
        
        # Utiliser le PDFSplitter
        splitter = PDFSplitter()
        split_result = splitter.split_pdf_by_page(pdf_path, split_dir)
        
        if not split_result['success']:
            task.status = 'failed'
            task.error_message = f"Erreur de séparation: {split_result.get('error', 'Erreur inconnue')}"
            task.save()
            return
        
        # Mettre à jour la tâche
        task.total_pages = split_result['total_pages']
        task.split_dir = split_dir
        task.save()
        
        print(f"✅ {task.total_pages} pages créées dans: {split_dir}")
        
        # Étape 2: Renommer chaque page
        print("🔄 Étape 2: Renommage des pages...")
        
        # Créer un dossier pour les pages renommées
        renamed_dir = os.path.join(settings.MEDIA_ROOT, 'renamed_pages', task_id)
        
        # Initialiser le renamer
        renamer = PDFRenamer(use_ocr=use_ocr)
        
        # Traiter chaque page
        successful_pages = 0
        failed_pages = 0
        
        for page_info in split_result['files']:
            page_number = page_info['page_number']
            page_path = page_info['path']
            
            try:
                # Renommer la page
                rename_result = renamer.rename_pdf(page_path, renamed_dir)
                
                # Créer l'enregistrement de la page
                processed_page = ProcessedPage.objects.create(
                    task=task,
                    page_number=page_number,
                    original_name=page_info['filename'],
                    new_name=rename_result.get('new_file', ''),
                    matricule=rename_result.get('matricule', ''),
                    nom=rename_result.get('nom', ''),
                    prenom=rename_result.get('prenom', ''),
                    mois=rename_result.get('mois', ''),
                    annee=rename_result.get('annee', ''),
                    file_path=rename_result.get('output_path', ''),
                    success=rename_result.get('success', False),
                    error_message=rename_result.get('error', '')
                )
                
                if rename_result['success']:
                    successful_pages += 1
                    print(f"✅ Page {page_number} renommée: {rename_result['new_file']}")
                else:
                    failed_pages += 1
                    print(f"❌ Page {page_number} échouée: {rename_result.get('error', 'Erreur')}")
                    
            except Exception as e:
                failed_pages += 1
                print(f"❌ Page {page_number} erreur: {str(e)}")
                
                # Enregistrer la page en échec
                ProcessedPage.objects.create(
                    task=task,
                    page_number=page_number,
                    original_name=page_info['filename'],
                    new_name='',
                    success=False,
                    error_message=str(e)
                )
            
            # Mettre à jour le compteur de pages traitées
            task.processed_pages = page_number
            task.save()
        
        # Étape 3: Finaliser la tâche
        print("🎯 Étape 3: Finalisation...")
        
        # Mettre à jour la tâche
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.renamed_dir = renamed_dir
        task.result_data = {
            'successful_pages': successful_pages,
            'failed_pages': failed_pages,
            'total_pages': task.total_pages,
            'success_rate': round((successful_pages / task.total_pages) * 100, 2) if task.total_pages > 0 else 0
        }
        task.save()
        
        print(f"🎉 Traitement terminé: {successful_pages} succès, {failed_pages} échecs")
        
        # Nettoyer le fichier source temporaire
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'successful_pages': successful_pages,
            'failed_pages': failed_pages,
            'total_pages': task.total_pages
        }
        
    except Exception as e:
        # En cas d'erreur générale
        print(f"❌ Erreur dans la tâche: {str(e)}")
        
        try:
            task = ProcessingTask.objects.get(task_id=task_id)
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
        except:
            pass
        
        # Nettoyer les fichiers temporaires
        if 'pdf_path' in locals() and os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        raise e


@shared_task
def cleanup_old_files():
    """
    Tâche de nettoyage: supprimer les fichiers temporaires anciens
    """
    try:
        media_root = settings.MEDIA_ROOT
        
        # Dossiers à nettoyer
        temp_dirs = [
            os.path.join(media_root, 'temp_uploads'),
            os.path.join(media_root, 'split_pages'),
            os.path.join(media_root, 'renamed_pages')
        ]
        
        # Supprimer les fichiers de plus de 7 jours
        cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
        
        return "Nettoyage terminé"
        
    except Exception as e:
        return f"Erreur de nettoyage: {str(e)}"