from django.db import models
from django.utils import timezone


class ProcessingTask(models.Model):
    """Modèle pour suivre les tâches de traitement"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    
    # Informations de la tâche
    task_id = models.CharField(max_length=255, unique=True)
    original_filename = models.CharField(max_length=255)
    total_pages = models.IntegerField(default=0)
    processed_pages = models.IntegerField(default=0)
    
    # Statut et timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Chemins des fichiers
    source_path = models.CharField(max_length=500, blank=True)
    split_dir = models.CharField(max_length=500, blank=True)
    renamed_dir = models.CharField(max_length=500, blank=True)
    
    # Résultats
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"


class ProcessedPage(models.Model):
    """Modèle pour chaque page traitée"""
    
    task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, related_name='pages')
    page_number = models.IntegerField()
    original_name = models.CharField(max_length=255)
    new_name = models.CharField(max_length=255)
    matricule = models.CharField(max_length=10, blank=True)
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100, blank=True)
    mois = models.CharField(max_length=3, blank=True)
    annee = models.CharField(max_length=4, blank=True)
    file_path = models.CharField(max_length=500)
    processed_at = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['page_number']
    
    def __str__(self):
        return f"Page {self.page_number}: {self.original_name} -> {self.new_name}"