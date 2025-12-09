from rest_framework import serializers
from .models import ProcessingTask, ProcessedPage


class PDFUploadSerializer(serializers.Serializer):
    """Sérialiseur pour l'upload de PDF"""
    
    file = serializers.FileField(
        required=True,
        help_text="Fichier PDF contenant plusieurs pages"
    )
    
    use_ocr = serializers.BooleanField(
        default=False,
        required=False,
        help_text="Utiliser l'OCR si nécessaire"
    )
    
    output_dir = serializers.CharField(
        default="processed_pdfs",
        required=False,
        max_length=100,
        help_text="Dossier de sortie pour les fichiers traités"
    )


class TaskStatusSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le statut d'une tâche"""
    
    class Meta:
        model = ProcessingTask
        fields = [
            'task_id',
            'original_filename',
            'status',
            'total_pages',
            'processed_pages',
            'created_at',
            'started_at',
            'completed_at',
            'progress_percentage'
        ]
        read_only_fields = fields
    
    def get_progress_percentage(self, obj):
        """Calculer le pourcentage de progression"""
        if obj.total_pages > 0:
            return round((obj.processed_pages / obj.total_pages) * 100, 1)
        return 0


class ProcessedPageSerializer(serializers.ModelSerializer):
    """Sérialiseur pour une page traitée"""
    
    class Meta:
        model = ProcessedPage
        fields = [
            'page_number',
            'original_name',
            'new_name',
            'matricule',
            'nom',
            'prenom',
            'mois',
            'annee',
            'success',
            'processed_at'
        ]


class TaskResultSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les résultats d'une tâche"""
    
    pages = ProcessedPageSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingTask
        fields = [
            'task_id',
            'original_filename',
            'status',
            'total_pages',
            'processed_pages',
            'progress_percentage',
            'created_at',
            'started_at',
            'completed_at',
            'split_dir',
            'renamed_dir',
            'pages',
            'error_message'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.total_pages > 0:
            return round((obj.processed_pages / obj.total_pages) * 100, 1)
        return 0