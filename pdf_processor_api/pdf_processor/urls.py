from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Traitement PDF
    path('process/', views.ProcessPDFView.as_view(), name='process-pdf'),
    
    # Suivi des tâches
    path('tasks/<str:task_id>/status/', views.TaskStatusView.as_view(), name='task-status'),
    path('tasks/<str:task_id>/result/', views.TaskResultView.as_view(), name='task-result'),
    path('tasks/<str:task_id>/download/<str:filename>/', views.DownloadFileView.as_view(), name='download-file'),
    
    # Utilitaires
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
]

# Servir les fichiers média en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)