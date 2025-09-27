import os
import re
import json
import tempfile
import google.generativeai as genai
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import UploadedPDF

# ============================================================
# CONFIGURE GEMINI API
# ============================================================
genai.configure(api_key="AIzaSyBJIV6SFqxNLCHagY2l8QLJ1DJ_QDdR3MA")

# ============================================================
# FUNCTION TO ANALYZE PDF WITH GEMINI
# ============================================================
def analyze_pdf_with_gemini(pdf_path):
    """
    Uploads a PDF (bank/credit card statement) to Gemini 1.5 Flash,
    analyzes the transactions, and categorizes them intelligently.
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Upload the file to Gemini
        uploaded_file = genai.upload_file(pdf_path)

        # Prompt Gemini to analyze the file
        prompt = """
        You are an AI financial assistant. Analyze the uploaded bank or credit card statement PDF.
        Identify and categorize all transactions into the following groups:
        - Recurring Income (like salary)
        - EMIs or Loans
        - SIPs or Investments
        - Rent or Utilities
        - Insurance Payments
        - Miscellaneous Expenses

        Return a well-formatted JSON object strictly following this schema:
        {
          "Recurring Income": [{"date": "YYYY-MM-DD", "description": "...", "amount": 123.45}],
          "EMIs": [{"date": "YYYY-MM-DD", "description": "...", "amount": 456.78}],
          "SIPs": [{"date": "YYYY-MM-DD", "description": "...", "amount": 1000.00}],
          "Rent": [{"date": "YYYY-MM-DD", "description": "...", "amount": 15000.00}],
          "Insurance": [{"date": "YYYY-MM-DD", "description": "...", "amount": 2500.00}],
          "Miscellaneous": [{"date": "YYYY-MM-DD", "description": "...", "amount": 200.00}]
        }

        Make sure your output is valid JSON.
        """

        # Generate the response (send file + text prompt)
        response = model.generate_content([uploaded_file, prompt])

        # Extract the text result
        result_text = response.text

        # Attempt to extract valid JSON
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"error": "Gemini response did not contain valid JSON.", "raw_output": result_text}

        return data

    except Exception as e:
        return {"error": f"Error while processing file: {str(e)}"}


# ============================================================
# MAIN UPLOAD VIEW
# ============================================================
def upload_view(request):
    """
    Handles PDF upload and sends it for Gemini analysis.
    Displays results in a dashboard after processing.
    """
    if request.method == "POST" and request.FILES.get("pdf"):
        pdf = request.FILES["pdf"]

        # Save uploaded file in temporary storage
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in pdf.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Save record in DB
        uploaded = UploadedPDF.objects.create(file=pdf)

        # Analyze using Gemini
        analysis_result = analyze_pdf_with_gemini(tmp_path)

        # Clean up temp file
        os.remove(tmp_path)

        # Store analysis in DB
        uploaded.analysis_result = analysis_result
        uploaded.save()

        return render(request, "bank_analyzer/dashboard.html", {
            "analysis": analysis_result,
            "file": uploaded,
        })

    return render(request, "bank_analyzer/upload.html")


# ============================================================
# DETAIL VIEW FOR A SPECIFIC UPLOADED FILE
# ============================================================
def detail_view(request, pk):
    """
    Displays the transaction analysis for a previously uploaded file.
    """
    file_obj = get_object_or_404(UploadedPDF, pk=pk)
    return render(request, "bank_analyzer/dashboard.html", {
        "analysis": file_obj.analysis_result,
        "file": file_obj,
    })
