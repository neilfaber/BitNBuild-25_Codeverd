# analyzer/admin.py
from django.contrib import admin
from .models import UploadedDocument

@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'uploaded_at')
    readonly_fields = ('raw_response', 'analysis_json')
