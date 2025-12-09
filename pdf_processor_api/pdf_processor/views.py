"""
Vues API pour le traitement PDF
"""

import os
import uuid
import tempfile
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from .models import ProcessingTask
from .serializers import (
    PDFUploadSerializer,
    TaskStatusSerializer,
    TaskResultSerializer
)
from .tasks import process_pdf_task
from .utils.pdf_splitter import PDFSplitter


class ProcessPDFView(APIView):
    """
    API pour démarrer le traitement d'un PDF
    
    Processus:
    1. Upload du PDF
    2. Création d'une tâche asynchrone
    3. Retour immédiat avec l'ID de la tâche
    """
    
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Démarrer le traitement d'un PDF"""
        
        # Valider les données d'entrée
        serializer = PDFUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer le fichier et les paramètres
        pdf_file = serializer.validated_data['file']
        use_ocr = serializer.validated_data.get('use_ocr', False)
        output_dir = serializer.validated_data.get('output_dir', 'processed_pdfs')
        
        # Valider le fichier PDF
        splitter = PDFSplitter()
        
        # Sauvegarder temporairement le fichier
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_filename = f"{uuid.uuid4()}_{pdf_file.name}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        with open(temp_path, 'wb') as f:
            for chunk in pdf_file.chunks():
                f.write(chunk)
        
        # Valider que c'est un PDF valide
        if not splitter.validate_pdf(temp_path):
            os.remove(temp_path)
            return Response(
                {'success': False, 'message': 'Fichier PDF invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer une tâche dans la base de données
        task_id = str(uuid.uuid4())
        
        task = ProcessingTask.objects.create(
            task_id=task_id,
            original_filename=pdf_file.name,
            status='pending',
            source_path=temp_path
        )
        
        # Démarrer la tâche asynchrone
        process_pdf_task.delay(task_id, temp_path, use_ocr, output_dir)
        
        # Retourner la réponse immédiate
        return Response({
            'success': True,
            'message': 'Traitement démarré en arrière-plan',
            'task_id': task_id,
            'original_filename': pdf_file.name,
            'status_url': f"/api/tasks/{task_id}/status/",
            'result_url': f"/api/tasks/{task_id}/result/"
        }, status=status.HTTP_202_ACCEPTED)


class TaskStatusView(APIView):
    """
    API pour vérifier le statut d'une tâche
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, task_id):
        """Récupérer le statut d'une tâche"""
        
        try:
            task = ProcessingTask.objects.get(task_id=task_id)
            serializer = TaskStatusSerializer(task)
            
            return Response({
                'success': True,
                'task': serializer.data
            })
            
        except ProcessingTask.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Tâche non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )


class TaskResultView(APIView):
    """
    API pour récupérer les résultats d'une tâche
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, task_id):
        """Récupérer les résultats d'une tâche"""
        
        try:
            task = ProcessingTask.objects.get(task_id=task_id)
            serializer = TaskResultSerializer(task)
            
            # Préparer les URLs de téléchargement
            result_data = serializer.data
            
            # Ajouter les URLs des fichiers
            if task.renamed_dir and os.path.exists(task.renamed_dir):
                files = []
                for filename in os.listdir(task.renamed_dir):
                    if filename.endswith('.pdf'):
                        files.append({
                            'filename': filename,
                            'download_url': f"/media/renamed_pages/{task_id}/{filename}"
                        })
                
                result_data['files'] = files
            
            return Response({
                'success': True,
                'task': result_data
            })
            
        except ProcessingTask.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Tâche non trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )


class DownloadFileView(APIView):
    """
    API pour télécharger un fichier traité
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, task_id, filename):
        """Télécharger un fichier spécifique"""
        
        file_path = os.path.join(settings.MEDIA_ROOT, 'renamed_pages', task_id, filename)
        
        if not os.path.exists(file_path):
            return Response(
                {'success': False, 'message': 'Fichier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Dans une vraie application, utiliser FileResponse
        # Pour l'exemple, retourner le chemin
        return Response({
            'success': True,
            'filename': filename,
            'file_path': file_path,
            'file_url': f"/media/renamed_pages/{task_id}/{filename}"
        })


class HealthCheckView(APIView):
    """
    API pour vérifier l'état du service
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Vérifier l'état du service"""
        
        # Vérifier les dépendances
        dependencies = {
            'pymupdf': False,
            'redis': False,
            'database': False
        }
        
        try:
            import fitz
            dependencies['pymupdf'] = True
        except ImportError:
            pass
        
        try:
            import redis
            dependencies['redis'] = True
        except ImportError:
            pass
        
        # Vérifier la base de données
        try:
            ProcessingTask.objects.count()
            dependencies['database'] = True
        except:
            pass
        
        return Response({
            'status': 'healthy',
            'service': 'PDF Processor API',
            'version': '1.0.0',
            'dependencies': dependencies,
            'timestamp': timezone.now().isoformat()
        })