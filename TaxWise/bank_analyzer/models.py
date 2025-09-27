# analyzer/models.py
from django.db import models
from django.utils import timezone

class UploadedDocument(models.Model):
    file = models.FileField(upload_to='uploads/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    raw_response = models.TextField(blank=True, null=True)      # raw text response from Gemini
    analysis_json = models.JSONField(blank=True, null=True)     # stored parsed JSON if Gemini returns JSON

    def __str__(self):
        return self.filename or f"Upload {self.pk}"

class UploadedPDF(models.Model):
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PDF {self.id} - {self.file.name}"