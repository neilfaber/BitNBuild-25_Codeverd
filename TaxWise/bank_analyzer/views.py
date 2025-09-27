import os
import re
import json
import tempfile
from datetime import datetime
from decimal import Decimal, InvalidOperation
import google.generativeai as genai
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import UploadedPDF, BankTransaction, TransactionSummary

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
    analyzes the transactions, and categorizes them intelligently with debit/credit classification.
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Upload the file to Gemini
        uploaded_file = genai.upload_file(pdf_path)

        # Enhanced prompt to include debit/credit classification
        prompt = """
        You are an AI financial assistant. Analyze the uploaded bank or credit card statement PDF.
        Identify and categorize all transactions into appropriate groups.
        
        For each transaction, determine:
        1. Whether it's a DEBIT (money going out) or CREDIT (money coming in)
        2. The appropriate category based on the description
        3. Extract the exact date, description, and amount
        
        Return a well-formatted JSON object strictly following this schema:
        {
          "transactions": [
            {
              "date": "YYYY-MM-DD",
              "description": "Transaction description",
              "amount": 123.45,
              "type": "DEBIT" or "CREDIT",
              "category": "category_name",
              "confidence": 0.95
            }
          ],
          "summary": {
            "total_transactions": 10,
            "total_credits": 5000.00,
            "total_debits": 3000.00,
            "net_amount": 2000.00,
            "period": "Month Year or date range"
          }
        }
        
        Categories should be one of:
        - RECURRING_INCOME (salary, pension, interest)
        - EMI (loan payments, EMIs)
        - SIP (mutual funds, investments, SIPs)
        - RENT (rent, utilities, maintenance)
        - INSURANCE (insurance premiums)
        - FOOD (restaurants, groceries, food delivery)
        - TRANSPORT (fuel, cab, public transport)
        - SHOPPING (retail, online shopping, clothes)
        - ENTERTAINMENT (movies, games, subscriptions)
        - HEALTHCARE (medical, pharmacy, hospitals)
        - EDUCATION (fees, books, courses)
        - MISCELLANEOUS (others)
        
        Guidelines for DEBIT vs CREDIT:
        - DEBIT: Expenses, withdrawals, purchases, bill payments, transfers out
        - CREDIT: Income, deposits, refunds, cashbacks, transfers in
        
        Make sure your output is valid JSON and amounts are positive numbers.
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


def save_transactions_to_db(analysis_result, uploaded_pdf, user):
    """
    Save individual transactions from analysis result to database
    """
    if not analysis_result or 'transactions' not in analysis_result:
        return []
    
    saved_transactions = []
    
    try:
        with transaction.atomic():  # Ensure all transactions are saved or none
            for trans_data in analysis_result['transactions']:
                try:
                    # Parse date
                    if isinstance(trans_data.get('date'), str):
                        trans_date = datetime.strptime(trans_data['date'], '%Y-%m-%d').date()
                    else:
                        continue  # Skip if date parsing fails
                    
                    # Parse amount
                    try:
                        amount = Decimal(str(trans_data.get('amount', 0)))
                    except (InvalidOperation, ValueError):
                        continue  # Skip if amount parsing fails
                    
                    # Create transaction record
                    bank_transaction = BankTransaction.objects.create(
                        user=user,
                        uploaded_pdf=uploaded_pdf,
                        transaction_date=trans_date,
                        description=trans_data.get('description', ''),
                        amount=amount,
                        transaction_type=trans_data.get('type', 'DEBIT').upper(),
                        category=trans_data.get('category', 'MISCELLANEOUS').upper(),
                        ai_confidence=float(trans_data.get('confidence', 0.0))
                    )
                    saved_transactions.append(bank_transaction)
                    
                except Exception as e:
                    print(f"Error saving transaction: {e}")
                    continue
                    
            # Create summary if we have transactions
            if saved_transactions:
                create_transaction_summary(saved_transactions, uploaded_pdf, user)
                
    except Exception as e:
        print(f"Error in transaction batch save: {e}")
    
    return saved_transactions


def create_transaction_summary(transactions, uploaded_pdf, user):
    """
    Create transaction summary for the uploaded statement
    """
    if not transactions:
        return None
    
    # Group by month/year
    summaries = {}
    
    for trans in transactions:
        month = trans.transaction_date.month
        year = trans.transaction_date.year
        key = f"{year}-{month}"
        
        if key not in summaries:
            summaries[key] = {
                'month': month,
                'year': year,
                'credits': Decimal('0'),
                'debits': Decimal('0'),
                'credit_count': 0,
                'debit_count': 0,
                'categories': {}
            }
        
        summary = summaries[key]
        
        if trans.is_credit:
            summary['credits'] += trans.amount
            summary['credit_count'] += 1
        else:
            summary['debits'] += trans.amount
            summary['debit_count'] += 1
        
        # Category breakdown
        category = trans.category
        if category not in summary['categories']:
            summary['categories'][category] = {'amount': Decimal('0'), 'count': 0}
        summary['categories'][category]['amount'] += trans.amount
        summary['categories'][category]['count'] += 1
    
    # Save summaries to database
    for key, summary_data in summaries.items():
        summary_obj, created = TransactionSummary.objects.get_or_create(
            user=user,
            uploaded_pdf=uploaded_pdf,
            month=summary_data['month'],
            year=summary_data['year'],
            defaults={
                'total_credits': summary_data['credits'],
                'total_debits': summary_data['debits'],
                'net_amount': summary_data['credits'] - summary_data['debits'],
                'credit_count': summary_data['credit_count'],
                'debit_count': summary_data['debit_count'],
                'total_transactions': summary_data['credit_count'] + summary_data['debit_count'],
                'category_breakdown': {k: {'amount': float(v['amount']), 'count': v['count']} 
                                     for k, v in summary_data['categories'].items()}
            }
        )
        
        if not created:
            # Update existing summary
            summary_obj.total_credits += summary_data['credits']
            summary_obj.total_debits += summary_data['debits']
            summary_obj.net_amount = summary_obj.total_credits - summary_obj.total_debits
            summary_obj.credit_count += summary_data['credit_count']
            summary_obj.debit_count += summary_data['debit_count']
            summary_obj.total_transactions += summary_data['credit_count'] + summary_data['debit_count']
            
            # Merge category breakdown
            existing_categories = summary_obj.category_breakdown
            for category, data in summary_data['categories'].items():
                if category in existing_categories:
                    existing_categories[category]['amount'] += float(data['amount'])
                    existing_categories[category]['count'] += data['count']
                else:
                    existing_categories[category] = {'amount': float(data['amount']), 'count': data['count']}
            
            summary_obj.category_breakdown = existing_categories
            summary_obj.save()
    
    return summaries


# ============================================================
# MAIN UPLOAD VIEW
# ============================================================
@login_required
def upload_view(request):
    """
    Handles PDF upload and sends it for Gemini analysis.
    Displays results in a dashboard after processing.
    Now includes debit/credit classification and saves individual transactions.
    """
    if request.method == "POST" and request.FILES.get("pdf"):
        pdf = request.FILES["pdf"]

        # Save uploaded file in temporary storage
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in pdf.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Save record in DB with user association
        uploaded = UploadedPDF.objects.create(
            file=pdf,
            user=request.user
        )

        # Analyze using Gemini
        analysis_result = analyze_pdf_with_gemini(tmp_path)

        # Clean up temp file
        os.remove(tmp_path)

        # Store analysis in DB
        uploaded.analysis_result = analysis_result
        uploaded.save()
        
        # Save individual transactions to database
        if not analysis_result.get('error'):
            saved_transactions = save_transactions_to_db(analysis_result, uploaded, request.user)
            messages.success(request, f"Successfully processed {len(saved_transactions)} transactions!")
        else:
            messages.error(request, f"Error processing file: {analysis_result.get('error', 'Unknown error')}")

        return render(request, "bank_analyzer/dashboard.html", {
            "analysis": analysis_result,
            "file": uploaded,
            "transactions": BankTransaction.objects.filter(uploaded_pdf=uploaded)[:50],  # Limit for display
            "user_summaries": TransactionSummary.objects.filter(user=request.user, uploaded_pdf=uploaded)
        })

    # Show user's recent uploads
    recent_uploads = UploadedPDF.objects.filter(user=request.user).order_by('-uploaded_at')[:5] if request.user.is_authenticated else []
    
    return render(request, "bank_analyzer/upload.html", {
        "recent_uploads": recent_uploads
    })


# ============================================================
# DETAIL VIEW FOR A SPECIFIC UPLOADED FILE
# ============================================================
@login_required
def detail_view(request, pk):
    """
    Displays the transaction analysis for a previously uploaded file.
    Now includes individual transaction details and summaries.
    """
    file_obj = get_object_or_404(UploadedPDF, pk=pk, user=request.user)  # Ensure user can only see their own files
    
    # Get individual transactions
    transactions = BankTransaction.objects.filter(uploaded_pdf=file_obj).order_by('-transaction_date')
    
    # Get summaries
    summaries = TransactionSummary.objects.filter(user=request.user, uploaded_pdf=file_obj)
    
    # Calculate additional statistics
    total_credits = sum(t.amount for t in transactions if t.is_credit)
    total_debits = sum(t.amount for t in transactions if t.is_debit)
    
    context = {
        "analysis": file_obj.analysis_result,
        "file": file_obj,
        "transactions": transactions[:100],  # Limit for display
        "user_summaries": summaries,
        "total_transactions": transactions.count(),
        "total_credits": total_credits,
        "total_debits": total_debits,
        "net_amount": total_credits - total_debits,
    }
    
    return render(request, "bank_analyzer/dashboard.html", context)


# ============================================================
# USER TRANSACTION DASHBOARD
# ============================================================
@login_required
def user_dashboard(request):
    """
    Display user's complete transaction dashboard with all their data
    """
    # Get all user's transactions
    all_transactions = BankTransaction.objects.filter(user=request.user).order_by('-transaction_date')
    
    # Get all summaries
    all_summaries = TransactionSummary.objects.filter(user=request.user).order_by('-year', '-month')
    
    # Calculate overall statistics
    total_credits = sum(t.amount for t in all_transactions if t.is_credit)
    total_debits = sum(t.amount for t in all_transactions if t.is_debit)
    
    # Category breakdown
    category_stats = {}
    for transaction in all_transactions:
        category = transaction.get_category_display()
        if category not in category_stats:
            category_stats[category] = {'amount': 0, 'count': 0, 'credits': 0, 'debits': 0}
        
        category_stats[category]['amount'] += transaction.amount
        category_stats[category]['count'] += 1
        
        if transaction.is_credit:
            category_stats[category]['credits'] += transaction.amount
        else:
            category_stats[category]['debits'] += transaction.amount
    
    context = {
        "all_transactions": all_transactions[:100],  # Limit for display
        "all_summaries": all_summaries,
        "total_transactions": all_transactions.count(),
        "total_credits": total_credits,
        "total_debits": total_debits,
        "net_amount": total_credits - total_debits,
        "category_stats": category_stats,
        "recent_uploads": UploadedPDF.objects.filter(user=request.user).order_by('-uploaded_at')[:10]
    }
    
    return render(request, "bank_analyzer/user_dashboard.html", context)
