# analyzer/forms.py
from django import forms

class UploadForm(forms.Form):
    pdf_file = forms.FileField(label="Bank / Card statement (PDF)", help_text="PDF only. Max ~100MB (subject to SDK limits).")
    
    def clean_pdf_file(self):
        f = self.cleaned_data['pdf_file']
        if not f.name.lower().endswith('.pdf'):
            raise forms.ValidationError("Please upload a PDF file.")
        # optional: size limit
        if f.size > 200 * 1024 * 1024:
            raise forms.ValidationError("File too large.")
        return f
