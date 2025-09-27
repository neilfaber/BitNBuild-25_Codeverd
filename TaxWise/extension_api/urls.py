from django.urls import path
from . import views

app_name = 'extension_api'

urlpatterns = [
    path('status/', views.status, name='status'),
    path('upload-statement/', views.upload_statement, name='upload_statement'),
    path('recent-uploads/', views.recent_uploads, name='recent_uploads'),
    path('update-categories/<int:pdf_id>/', views.update_categories, name='update_categories'),
]