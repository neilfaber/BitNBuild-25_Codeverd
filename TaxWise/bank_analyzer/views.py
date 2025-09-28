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
from .models import (
    UploadedPDF, BankTransaction, TransactionSummary,
    CreditCardStatement, CreditCardTransaction, CreditCardFee, 
    CreditCardInterest, CreditCardReward
)

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

        # Read the PDF file content directly (newer Gemini API approach)
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Create the file upload object for Gemini API
        import mimetypes
        mime_type = mimetypes.guess_type(pdf_path)[0] or 'application/pdf'
        
        # Create file data object for newer Gemini API
        file_data = {
            "mime_type": mime_type,
            "data": pdf_content
        }

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
        response = model.generate_content([file_data, prompt])

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


def analyze_credit_card_statement_with_gemini(pdf_path):
    """
    Specialized function to analyze credit card statements with comprehensive data extraction.
    Extracts account summary, transaction details, fees, interest, and reward information.
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Read the PDF file content directly (newer Gemini API approach)
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Create the file upload object for Gemini API
        import mimetypes
        mime_type = mimetypes.guess_type(pdf_path)[0] or 'application/pdf'
        
        # Create file data object for newer Gemini API
        file_data = {
            "mime_type": mime_type,
            "data": pdf_content
        }

        # Simplified prompt for credit card statement analysis focused on CIBIL data
        prompt = """
        You are an AI financial assistant. Analyze the uploaded credit card statement PDF.
        Extract key information needed for CIBIL score analysis and transaction categorization.
        
        Return a well-formatted JSON object strictly following this schema:
        {
          "statement_type": "credit_card",
          "account_summary": {
            "bank_name": "Bank name from statement",
            "card_number_last_four": "Last 4 digits of card",
            "statement_date": "YYYY-MM-DD",
            "payment_due_date": "YYYY-MM-DD", 
            "previous_balance": 5000.00,
            "current_balance": 7500.00,
            "minimum_amount_due": 750.00,
            "total_credit_limit": 50000.00,
            "credit_utilization_percentage": 15.0
          },
          "transactions": [
            {
              "date": "YYYY-MM-DD",
              "description": "Transaction description",
              "amount": 123.45,
              "type": "PURCHASE/PAYMENT/CREDIT/FEE",
              "category": "category_name",
              "confidence": 0.95
            }
          ],
          "payment_behavior": {
            "on_time_payment": true,
            "minimum_payment_made": true,
            "overlimit_usage": false,
            "late_fees": 0.00,
            "total_fees": 0.00,
            "total_interest": 0.00
          },
          "summary": {
            "total_transactions": 25,
            "total_purchases": 15000.00,
            "total_payments": 10000.00,
            "total_fees": 500.00,
            "net_change": 5500.00,
            "period": "Month Year"
          }
        }
        
        Categories should be one of:
        - DINING (restaurants, food delivery)
        - SHOPPING (retail, online shopping)
        - GROCERY (supermarkets, grocery)
        - FUEL (petrol pumps, gas stations)
        - TRANSPORT (cab, airlines, metro)
        - ENTERTAINMENT (movies, streaming)
        - HEALTHCARE (medical, pharmacy)
        - UTILITIES (electricity, phone bills)
        - EDUCATION (fees, books)
        - INSURANCE (insurance premiums)
        - EMI (loan payments, EMIs)
        - ATM (cash withdrawals)
        - MISCELLANEOUS (others)
        
        Transaction Types:
        - PURCHASE: Spending transactions
        - PAYMENT: Credit card bill payments
        - CREDIT: Refunds, cashbacks
        - FEE: Late fees, annual fees
        
        Focus on extracting data that impacts CIBIL score:
        - Payment behavior (on-time, late, missed)
        - Credit utilization percentage
        - Outstanding balances
        - Fees and penalties
        - Overlimit usage
        
        Return ONLY valid JSON without markdown formatting.
        """

        # Generate the response
        response = model.generate_content([file_data, prompt])

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
        return {"error": f"Error while processing credit card statement: {str(e)}"}


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


def save_credit_card_statement_to_db(analysis_result, uploaded_pdf, user):
    """
    Save credit card statement data to database with all components
    """
    if not analysis_result or 'account_summary' not in analysis_result:
        return None
    
    try:
        with transaction.atomic():
            # Extract account summary
            account_data = analysis_result.get('account_summary', {})
            
            # Parse statement date
            statement_date = None
            if account_data.get('statement_date'):
                try:
                    statement_date = datetime.strptime(account_data['statement_date'], '%Y-%m-%d').date()
                except:
                    pass
            
            # Parse billing period dates
            billing_start = None
            billing_end = None
            due_date = None
            
            if account_data.get('billing_period_start'):
                try:
                    billing_start = datetime.strptime(account_data['billing_period_start'], '%Y-%m-%d').date()
                except:
                    pass
            
            if account_data.get('billing_period_end'):
                try:
                    billing_end = datetime.strptime(account_data['billing_period_end'], '%Y-%m-%d').date()
                except:
                    pass
                    
            if account_data.get('payment_due_date'):
                try:
                    due_date = datetime.strptime(account_data['payment_due_date'], '%Y-%m-%d').date()
                except:
                    pass
            
            # Create credit card statement
            statement = CreditCardStatement.objects.create(
                user=user,
                uploaded_pdf=uploaded_pdf,
                card_number_last_four=account_data.get('card_number_last_four', '')[:4],
                cardholder_name=account_data.get('cardholder_name', ''),
                bank_name=account_data.get('bank_name', ''),
                card_type=account_data.get('card_type', ''),
                statement_date=statement_date,
                billing_period_start=billing_start,
                billing_period_end=billing_end,
                payment_due_date=due_date,
                previous_balance=Decimal(str(account_data.get('previous_balance', 0))),
                current_balance=Decimal(str(account_data.get('current_balance', 0))),
                statement_balance=Decimal(str(account_data.get('statement_balance', 0))),
                minimum_amount_due=Decimal(str(account_data.get('minimum_amount_due', 0))),
                total_amount_due=Decimal(str(account_data.get('total_amount_due', 0))),
                total_credit_limit=Decimal(str(account_data.get('total_credit_limit', 0))),
                available_credit=Decimal(str(account_data.get('available_credit', 0))),
                credit_utilization_percentage=float(account_data.get('credit_utilization_percentage', 0)),
                raw_analysis_result=analysis_result
            )
            
            # Save transactions
            saved_transactions = []
            for trans_data in analysis_result.get('transactions', []):
                try:
                    # Parse transaction date
                    trans_date = datetime.strptime(trans_data.get('transaction_date'), '%Y-%m-%d').date()
                    
                    # Parse posting date if available
                    posting_date = None
                    if trans_data.get('posting_date'):
                        try:
                            posting_date = datetime.strptime(trans_data.get('posting_date'), '%Y-%m-%d').date()
                        except:
                            posting_date = trans_date
                    else:
                        posting_date = trans_date
                    
                    # Create transaction
                    credit_transaction = CreditCardTransaction.objects.create(
                        statement=statement,
                        user=user,
                        transaction_date=trans_date,
                        posting_date=posting_date,
                        description=trans_data.get('description', ''),
                        merchant_name=trans_data.get('merchant_name', ''),
                        transaction_amount=Decimal(str(trans_data.get('transaction_amount', 0))),
                        transaction_type=trans_data.get('transaction_type', 'PURCHASE').upper(),
                        category=trans_data.get('category', 'MISCELLANEOUS').upper(),
                        ai_confidence_score=float(trans_data.get('confidence', 0.0)),
                        reference_number=trans_data.get('reference_number', ''),
                        is_international=trans_data.get('is_international', False),
                        reward_points_earned=int(trans_data.get('reward_points_earned', 0)),
                        cashback_earned=Decimal(str(trans_data.get('cashback_earned', 0)))
                    )
                    saved_transactions.append(credit_transaction)
                    
                except Exception as e:
                    print(f"Error saving credit card transaction: {e}")
                    continue
            
            # Save fees and charges
            for fee_data in analysis_result.get('fees_and_charges', []):
                try:
                    fee_date = datetime.strptime(fee_data.get('fee_date'), '%Y-%m-%d').date()
                    
                    CreditCardFee.objects.create(
                        statement=statement,
                        user=user,
                        fee_type=fee_data.get('fee_type', 'OTHER').upper(),
                        fee_description=fee_data.get('fee_description', ''),
                        fee_amount=Decimal(str(fee_data.get('fee_amount', 0))),
                        fee_date=fee_date,
                        base_amount=Decimal(str(fee_data.get('base_amount', 0))) if fee_data.get('base_amount') else None,
                        fee_rate=float(fee_data.get('fee_rate', 0)) if fee_data.get('fee_rate') else None
                    )
                except Exception as e:
                    print(f"Error saving credit card fee: {e}")
                    continue
            
            # Save interest charges
            for interest_data in analysis_result.get('interest_charges', []):
                try:
                    interest_date = datetime.strptime(interest_data.get('interest_date'), '%Y-%m-%d').date()
                    
                    CreditCardInterest.objects.create(
                        statement=statement,
                        user=user,
                        interest_type=interest_data.get('interest_type', 'PURCHASE').upper(),
                        interest_description=interest_data.get('interest_description', ''),
                        interest_amount=Decimal(str(interest_data.get('interest_amount', 0))),
                        interest_date=interest_date,
                        principal_amount=Decimal(str(interest_data.get('principal_amount', 0))) if interest_data.get('principal_amount') else None,
                        annual_percentage_rate=float(interest_data.get('annual_percentage_rate', 0)) if interest_data.get('annual_percentage_rate') else None,
                        number_of_days=int(interest_data.get('number_of_days', 0)) if interest_data.get('number_of_days') else None
                    )
                except Exception as e:
                    print(f"Error saving credit card interest: {e}")
                    continue
            
            # Save rewards
            for reward_data in analysis_result.get('rewards', []):
                try:
                    reward_date = datetime.strptime(reward_data.get('reward_date'), '%Y-%m-%d').date()
                    expiry_date = None
                    if reward_data.get('expiry_date'):
                        try:
                            expiry_date = datetime.strptime(reward_data.get('expiry_date'), '%Y-%m-%d').date()
                        except:
                            pass
                    
                    CreditCardReward.objects.create(
                        statement=statement,
                        user=user,
                        reward_type=reward_data.get('reward_type', 'POINTS').upper(),
                        reward_description=reward_data.get('reward_description', ''),
                        reward_date=reward_date,
                        points_earned=int(reward_data.get('points_earned', 0)),
                        cashback_amount=Decimal(str(reward_data.get('cashback_amount', 0))),
                        reward_rate=float(reward_data.get('reward_rate', 0)),
                        expiry_date=expiry_date
                    )
                except Exception as e:
                    print(f"Error saving credit card reward: {e}")
                    continue
            
            # Update statement totals from summary
            summary_data = analysis_result.get('summary', {})
            statement.total_purchases = Decimal(str(summary_data.get('total_purchases', 0)))
            statement.total_payments = Decimal(str(summary_data.get('total_payments', 0)))
            statement.total_fees = Decimal(str(summary_data.get('total_fees', 0)))
            statement.total_interest = Decimal(str(summary_data.get('total_interest', 0)))
            statement.total_credits = Decimal(str(summary_data.get('total_credits', 0)))
            statement.reward_points_earned = int(summary_data.get('reward_points_earned', 0))
            statement.cashback_earned = Decimal(str(summary_data.get('cashback_earned', 0)))
            statement.save()
            
            return statement, saved_transactions
            
    except Exception as e:
        print(f"Error saving credit card statement: {e}")
        return None, []


# ============================================================
# MAIN UPLOAD VIEW
# ============================================================
@login_required
def upload_view(request):
    """
    Handles PDF upload and sends it for Gemini analysis.
    Automatically detects whether it's a bank statement or credit card statement.
    Displays results in a dashboard after processing.
    """
    if request.method == "POST" and request.FILES.get("pdf"):
        pdf = request.FILES["pdf"]
        statement_type = request.POST.get('statement_type', 'auto')  # auto, bank, credit_card

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

        try:
            # Determine analysis type
            if statement_type == 'credit_card':
                # Force credit card analysis
                analysis_result = analyze_credit_card_statement_with_gemini(tmp_path)
                is_credit_card = True
            elif statement_type == 'bank':
                # Force bank statement analysis
                analysis_result = analyze_pdf_with_gemini(tmp_path)
                is_credit_card = False
            else:
                # Auto-detect: Try credit card first, then bank statement
                analysis_result = analyze_credit_card_statement_with_gemini(tmp_path)
                
                # Check if it's actually a credit card statement
                if (analysis_result.get('statement_type') == 'credit_card' and 
                    analysis_result.get('account_summary') and
                    not analysis_result.get('error')):
                    is_credit_card = True
                else:
                    # Fall back to bank statement analysis
                    analysis_result = analyze_pdf_with_gemini(tmp_path)
                    is_credit_card = False

            # Clean up temp file
            os.remove(tmp_path)

            # Store analysis in DB
            uploaded.analysis_result = analysis_result
            uploaded.save()
            
            # Process and save data based on statement type
            if not analysis_result.get('error'):
                if is_credit_card and analysis_result.get('account_summary'):
                    # Save credit card statement data
                    statement, saved_transactions = save_credit_card_statement_to_db(
                        analysis_result, uploaded, request.user
                    )
                    
                    if statement:
                        messages.success(request, 
                            f"Successfully processed credit card statement with {len(saved_transactions)} transactions!")
                        
                        # Render credit card dashboard
                        return render(request, "bank_analyzer/credit_card_dashboard.html", {
                            "analysis": analysis_result,
                            "file": uploaded,
                            "statement": statement,
                            "transactions": saved_transactions[:50],
                            "fees": statement.fees.all(),
                            "interest_charges": statement.interest_charges.all(),
                            "rewards": statement.rewards.all(),
                            "is_credit_card": True
                        })
                    else:
                        messages.error(request, "Error processing credit card statement data")
                else:
                    # Save as bank statement data
                    saved_transactions = save_transactions_to_db(analysis_result, uploaded, request.user)
                    messages.success(request, f"Successfully processed {len(saved_transactions)} bank transactions!")
                    
                    # Render bank statement dashboard
                    return render(request, "bank_analyzer/dashboard.html", {
                        "analysis": analysis_result,
                        "file": uploaded,
                        "transactions": BankTransaction.objects.filter(uploaded_pdf=uploaded)[:50],
                        "user_summaries": TransactionSummary.objects.filter(user=request.user, uploaded_pdf=uploaded),
                        "is_credit_card": False
                    })
            else:
                messages.error(request, f"Error processing file: {analysis_result.get('error', 'Unknown error')}")
                
                # Return basic dashboard with error
                return render(request, "bank_analyzer/dashboard.html", {
                    "analysis": analysis_result,
                    "file": uploaded,
                    "transactions": [],
                    "user_summaries": [],
                    "is_credit_card": False
                })
        
        except Exception as e:
            # Clean up temp file if it still exists
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            
            messages.error(request, f"Error processing file: {str(e)}")
            
            # Return error dashboard
            return render(request, "bank_analyzer/dashboard.html", {
                "analysis": {"error": str(e)},
                "file": uploaded,
                "transactions": [],
                "user_summaries": [],
                "is_credit_card": False
            })

    # Show user's recent uploads
    recent_uploads = UploadedPDF.objects.filter(user=request.user).order_by('-uploaded_at')[:5] if request.user.is_authenticated else []
    recent_credit_cards = CreditCardStatement.objects.filter(user=request.user).order_by('-statement_date')[:5] if request.user.is_authenticated else []
    
    return render(request, "bank_analyzer/upload.html", {
        "recent_uploads": recent_uploads,
        "recent_credit_cards": recent_credit_cards
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


# Add these functions to your existing views.py file

def generate_financial_predictions_with_gemini(user_data):
    """
    Use Gemini to analyze user's financial data and generate predictions
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Create comprehensive financial profile for analysis
        financial_prompt = f"""
        You are an expert financial advisor and tax consultant. Analyze the following user's financial data 
        and provide comprehensive predictions for future troubles and benefits regarding taxes and finances.
        
        USER FINANCIAL DATA:
        
        TRANSACTION SUMMARY:
        - Total Credits (Income): ₹{user_data.get('total_credits', 0):,.2f}
        - Total Debits (Expenses): ₹{user_data.get('total_debits', 0):,.2f}
        - Net Amount: ₹{user_data.get('net_amount', 0):,.2f}
        - Total Transactions: {user_data.get('total_transactions', 0)}
        
        CATEGORY BREAKDOWN:
        {user_data.get('category_breakdown_text', '')}
        
        MONTHLY PATTERNS:
        {user_data.get('monthly_patterns_text', '')}
        
        CREDIT CARD DATA (if available):
        - Credit Utilization: {user_data.get('credit_utilization', 0)}%
        - Payment Behavior: {user_data.get('payment_behavior', 'Unknown')}
        - Total Credit Limit: ₹{user_data.get('total_credit_limit', 0):,.2f}
        - Outstanding Balance: ₹{user_data.get('outstanding_balance', 0):,.2f}
        
        INVESTMENT PATTERNS:
        - SIP Amount: ₹{user_data.get('sip_amount', 0):,.2f}
        - Investment Frequency: {user_data.get('investment_frequency', 'Unknown')}
        
        Based on this data, provide a detailed JSON response with the following structure:
        
        {{
            "overall_financial_health": {{
                "score": 85,
                "status": "Good/Average/Poor",
                "key_strengths": ["Regular SIP investments", "Controlled spending"],
                "major_concerns": ["High credit utilization", "Irregular income"]
            }},
            "tax_predictions": {{
                "current_year_liability": {{
                    "estimated_tax": 125000,
                    "confidence_level": "High/Medium/Low",
                    "basis": "Based on salary credits and investment patterns"
                }},
                "next_year_projections": {{
                    "expected_tax_increase": 15000,
                    "potential_savings": 35000,
                    "recommended_investments": ["ELSS", "PPF", "NPS"]
                }},
                "tax_optimization_opportunities": [
                    {{
                        "strategy": "Increase ELSS investment",
                        "potential_savings": 46800,
                        "implementation": "Invest ₹1.5L in ELSS funds",
                        "timeline": "Before March 31st"
                    }}
                ],
                "compliance_alerts": [
                    {{
                        "issue": "ITR filing deadline",
                        "severity": "High/Medium/Low",
                        "action_required": "File ITR by July 31st",
                        "estimated_penalty": 5000
                    }}
                ]
            }},
            "financial_predictions": {{
                "short_term_forecast": {{
                    "next_3_months": {{
                        "expected_income": 450000,
                        "expected_expenses": 380000,
                        "surplus_deficit": 70000,
                        "key_challenges": ["High utility bills in summer"],
                        "opportunities": ["Bonus expected in Q1"]
                    }},
                    "next_6_months": {{
                        "cash_flow_projection": 140000,
                        "major_expenses": ["Insurance renewal", "Festival expenses"],
                        "recommended_actions": ["Build emergency fund", "Review insurance"]
                    }}
                }},
                "long_term_forecast": {{
                    "next_year": {{
                        "wealth_growth_projection": 8.5,
                        "risk_factors": ["Market volatility", "Inflation impact"],
                        "growth_opportunities": ["Real estate investment", "Equity markets"]
                    }},
                    "5_year_outlook": {{
                        "projected_net_worth": 2500000,
                        "retirement_readiness": 65,
                        "major_goals_feasibility": ["Home purchase - Feasible", "Child education - Need planning"]
                    }}
                }}
            }},
            "risk_assessment": {{
                "immediate_risks": [
                    {{
                        "risk": "High credit card debt",
                        "impact": "High/Medium/Low",
                        "probability": "High/Medium/Low",
                        "mitigation": "Pay off high-interest debt first",
                        "estimated_cost": 45000
                    }}
                ],
                "future_challenges": [
                    {{
                        "challenge": "Inflation impact on expenses",
                        "timeline": "Next 2 years",
                        "impact_amount": 85000,
                        "preparation_needed": "Increase income by 8% annually"
                    }}
                ]
            }},
            "recommendations": {{
                "immediate_actions": [
                    {{
                        "priority": "High/Medium/Low",
                        "action": "Reduce credit card utilization below 30%",
                        "expected_benefit": "Improve CIBIL score by 50 points",
                        "timeline": "Within 3 months",
                        "estimated_savings": 25000
                    }}
                ],
                "strategic_planning": [
                    {{
                        "goal": "Tax optimization",
                        "strategy": "Systematic investment plan",
                        "investment_amount": 150000,
                        "expected_returns": 12.5,
                        "tax_savings": 46800
                    }}
                ],
                "emergency_preparations": [
                    {{
                        "scenario": "Job loss",
                        "required_fund": 600000,
                        "current_preparedness": 35,
                        "recommended_action": "Build 6-month emergency fund"
                    }}
                ]
            }},
            "monthly_action_plan": [
                {{
                    "month": 1,
                    "focus_area": "Debt reduction",
                    "specific_actions": ["Pay extra ₹10K toward credit card", "Cancel unused subscriptions"],
                    "budget_allocation": {{
                        "debt_payment": 25000,
                        "investments": 15000,
                        "emergency_fund": 5000
                    }}
                }}
            ]
        }}
        
        Make sure all predictions are realistic, data-driven, and actionable. Consider Indian tax laws, 
        current economic conditions, and practical financial planning strategies. All amounts should be in INR.
        """
        
        # Generate the response
        response = model.generate_content(financial_prompt)
        result_text = response.text
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            predictions_data = json.loads(json_match.group())
        else:
            predictions_data = {"error": "Could not parse predictions", "raw_output": result_text}
        
        return predictions_data
        
    except Exception as e:
        return {"error": f"Error generating predictions: {str(e)}"}


def prepare_user_financial_data(user):
    """
    Prepare comprehensive financial data for prediction analysis
    """
    # Get all user transactions
    all_transactions = BankTransaction.objects.filter(user=user)
    credit_card_statements = CreditCardStatement.objects.filter(user=user)
    
    # Calculate basic stats
    total_credits = sum(t.amount for t in all_transactions if t.is_credit)
    total_debits = sum(t.amount for t in all_transactions if t.is_debit)
    
    # Category breakdown
    category_breakdown = {}
    for transaction in all_transactions:
        category = transaction.category
        if category not in category_breakdown:
            category_breakdown[category] = {'amount': 0, 'count': 0, 'credits': 0, 'debits': 0}
        
        category_breakdown[category]['amount'] += float(transaction.amount)
        category_breakdown[category]['count'] += 1
        
        if transaction.is_credit:
            category_breakdown[category]['credits'] += float(transaction.amount)
        else:
            category_breakdown[category]['debits'] += float(transaction.amount)
    
    # Monthly patterns
    monthly_summaries = TransactionSummary.objects.filter(user=user).order_by('-year', '-month')[:12]
    
    # Credit card analysis
    latest_cc_statement = credit_card_statements.first() if credit_card_statements.exists() else None
    
    # Create text representations for Gemini
    category_breakdown_text = "\n".join([
        f"- {category}: ₹{data['amount']:,.2f} ({data['count']} transactions)"
        for category, data in category_breakdown.items()
    ])
    
    monthly_patterns_text = "\n".join([
        f"- {summary.month}/{summary.year}: Credits ₹{summary.total_credits:,.2f}, "
        f"Debits ₹{summary.total_debits:,.2f}, Net ₹{summary.net_amount:,.2f}"
        for summary in monthly_summaries
    ])
    
    # SIP and investment analysis
    sip_transactions = all_transactions.filter(category='SIP')
    sip_amount = sum(t.amount for t in sip_transactions)
    sip_frequency = len(sip_transactions)
    
    return {
        'total_credits': float(total_credits),
        'total_debits': float(total_debits),
        'net_amount': float(total_credits - total_debits),
        'total_transactions': all_transactions.count(),
        'category_breakdown_text': category_breakdown_text,
        'monthly_patterns_text': monthly_patterns_text,
        'credit_utilization': float(latest_cc_statement.credit_utilization_percentage) if latest_cc_statement else 0,
        'payment_behavior': 'Good' if latest_cc_statement and latest_cc_statement.minimum_amount_due > 0 else 'Unknown',
        'total_credit_limit': float(latest_cc_statement.total_credit_limit) if latest_cc_statement else 0,
        'outstanding_balance': float(latest_cc_statement.current_balance) if latest_cc_statement else 0,
        'sip_amount': float(sip_amount),
        'investment_frequency': f"{sip_frequency} transactions" if sip_frequency > 0 else 'No regular investments',
        'category_breakdown': category_breakdown,
        'monthly_summaries': [
            {
                'month': s.month,
                'year': s.year,
                'credits': float(s.total_credits),
                'debits': float(s.total_debits),
                'net': float(s.net_amount)
            }
            for s in monthly_summaries
        ]
    }


@login_required
def financial_predictions_view(request):
    """
    Generate and display financial predictions for the user
    """
    # Get user's financial data
    user_data = prepare_user_financial_data(request.user)
    
    # Check if user has sufficient data for predictions
    if user_data['total_transactions'] < 10:
        messages.warning(request, "Upload more bank statements to get accurate financial predictions.")
        return render(request, 'bank_analyzer/financial_predictions.html', {
            'insufficient_data': True,
            'transaction_count': user_data['total_transactions']
        })
    
    # Generate predictions using Gemini
    predictions = generate_financial_predictions_with_gemini(user_data)
    
    if predictions.get('error'):
        messages.error(request, f"Error generating predictions: {predictions['error']}")
        predictions = None
    
    # Prepare context for template
    context = {
        'user_data': user_data,
        'predictions': predictions,
        'sufficient_data': True,
        'generated_at': datetime.now(),
    }
    
    return render(request, 'bank_analyzer/financial_predictions.html', context)


@login_required
def prediction_details_view(request, prediction_type):
    """
    Show detailed view for specific prediction category
    """
    user_data = prepare_user_financial_data(request.user)
    predictions = generate_financial_predictions_with_gemini(user_data)
    
    # Extract specific prediction data based on type
    detail_data = {}
    if prediction_type == 'tax':
        detail_data = predictions.get('tax_predictions', {})
    elif prediction_type == 'financial':
        detail_data = predictions.get('financial_predictions', {})
    elif prediction_type == 'risk':
        detail_data = predictions.get('risk_assessment', {})
    elif prediction_type == 'recommendations':
        detail_data = predictions.get('recommendations', {})
    
    context = {
        'prediction_type': prediction_type,
        'detail_data': detail_data,
        'user_data': user_data,
        'full_predictions': predictions
    }
    
    return render(request, 'bank_analyzer/prediction_details.html', context)