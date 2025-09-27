# analyzer/models.py
from django.db import models
from django.contrib.auth.models import User
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    file = models.FileField(upload_to="uploads/")
    filename = models.CharField(max_length=255, default='unnamed.pdf')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    auto_uploaded = models.BooleanField(default=False)
    file_type = models.CharField(max_length=10, choices=[
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ], default='pdf')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')

    def __str__(self):
        return f"{self.filename} ({self.user.username if self.user else 'no user'})"

class Transaction(models.Model):
    pdf = models.ForeignKey(UploadedPDF, on_delete=models.CASCADE)
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, default='Uncategorized')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-date']
        
    def __str__(self):
        return f"{self.date} - {self.description[:30]}"