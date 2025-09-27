import PyPDF2
import pandas as pd
import pdfplumber
from datetime import datetime
from typing import Dict, List, Optional
import re
import magic
from django.core.files.uploadedfile import UploadedFile

def detect_statement_type(uploaded_file: UploadedFile) -> Optional[str]:
    """Detect the type of statement file"""
    try:
        # Get MIME type
        mime = magic.from_buffer(uploaded_file.read(2048), mime=True)
        uploaded_file.seek(0)  # Reset file pointer
        
        if mime == 'application/pdf':
            return 'pdf'
        elif mime == 'text/csv':
            return 'csv'
        elif mime == 'application/vnd.ms-excel':
            return 'csv'
        
        return None
    except Exception as e:
        print(f"Error detecting file type: {e}")
        return None

def process_statement(pdf_instance) -> Dict:
    """Process uploaded bank statement and extract information"""
    result = {
        'categories': [],
        'transactions': [],
        'metadata': {}
    }
    
    try:
        # Process based on file type
        if pdf_instance.file_type == 'pdf':
            result = process_pdf(pdf_instance.file)
        elif pdf_instance.file_type == 'csv':
            result = process_csv(pdf_instance.file)
            
        # Add metadata
        result['metadata'] = extract_metadata(pdf_instance)
        return result
        
    except Exception as e:
        print(f"Error processing statement: {e}")
        return result

def extract_metadata(pdf_instance) -> Dict:
    """Extract metadata from statement"""
    metadata = {
        'bank_name': detect_bank_name(pdf_instance),
        'statement_period': extract_statement_period(pdf_instance),
        'account_type': detect_account_type(pdf_instance)
    }
    return metadata

def detect_bank_name(pdf_instance) -> str:
    """Detect the bank name from the statement"""
    common_banks = [
        'Chase', 'Bank of America', 'Wells Fargo', 'Citibank',
        'Capital One', 'US Bank', 'PNC Bank'
    ]
    
    try:
        content = extract_text_content(pdf_instance)
        for bank in common_banks:
            if bank.lower() in content.lower():
                return bank
    except:
        pass
        
    return "Unknown Bank"

def extract_statement_period(pdf_instance) -> Dict:
    """Extract statement period dates"""
    try:
        content = extract_text_content(pdf_instance)
        # Look for date patterns
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
        if len(dates) >= 2:
            return {
                'start_date': dates[0],
                'end_date': dates[1]
            }
    except:
        pass
        
    return {
        'start_date': None,
        'end_date': None
    }

def detect_account_type(pdf_instance) -> str:
    """Detect the type of account"""
    account_types = {
        'checking': ['checking', 'current account'],
        'savings': ['savings', 'save'],
        'credit': ['credit card', 'credit account'],
        'investment': ['investment', 'trading', 'brokerage']
    }
    
    try:
        content = extract_text_content(pdf_instance)
        for acc_type, keywords in account_types.items():
            if any(keyword in content.lower() for keyword in keywords):
                return acc_type
    except:
        pass
        
    return "unknown"

def extract_text_content(pdf_instance) -> str:
    """Extract text content from PDF"""
    if pdf_instance.file_type == 'pdf':
        with pdfplumber.open(pdf_instance.file) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages)
    return ""

def process_pdf(file_obj) -> Dict:
    """Process PDF bank statements"""
    result = {
        'categories': [],
        'transactions': []
    }
    
    try:
        # Read PDF content
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text_content = ""
        
        # Extract text from all pages
        for page in pdf_reader.pages:
            text_content += page.extract_text()
            
        # Extract transactions using regex patterns
        transactions = extract_transactions(text_content)
        
        # Categorize transactions
        categorized = categorize_transactions(transactions)
        
        result['transactions'] = transactions
        result['categories'] = categorized
        
    except Exception as e:
        print(f"PDF processing error: {str(e)}")
        
    return result

def process_csv(file_obj) -> Dict:
    """Process CSV bank statements"""
    result = {
        'categories': [],
        'transactions': []
    }
    
    try:
        # Read CSV content
        df = pd.read_csv(file_obj)
        
        # Common CSV column names for different banks
        date_columns = ['Date', 'Transaction Date', 'Posted Date']
        amount_columns = ['Amount', 'Transaction Amount', 'Debit', 'Credit']
        description_columns = ['Description', 'Narration', 'Transaction Description']
        
        # Find the actual column names in the CSV
        date_col = next((col for col in date_columns if col in df.columns), None)
        amount_col = next((col for col in amount_columns if col in df.columns), None)
        desc_col = next((col for col in description_columns if col in df.columns), None)
        
        if all([date_col, amount_col, desc_col]):
            transactions = []
            
            # Convert DataFrame to list of transactions
            for _, row in df.iterrows():
                transaction = {
                    'date': str(row[date_col]),
                    'amount': float(row[amount_col]),
                    'description': str(row[desc_col])
                }
                transactions.append(transaction)
                
            # Categorize transactions
            categorized = categorize_transactions(transactions)
            
            result['transactions'] = transactions
            result['categories'] = categorized
            
    except Exception as e:
        print(f"CSV processing error: {str(e)}")
        
    return result

def extract_transactions(text_content: str) -> List[Dict]:
    """Extract transactions from text using regex patterns"""
    transactions = []
    
    # Common date patterns
    date_pattern = r'\d{2}[-/]\d{2}[-/]\d{4}'
    
    # Common amount patterns
    amount_pattern = r'\d+,?\d*\.\d{2}'
    
    # Find potential transactions in text
    lines = text_content.split('\n')
    
    for line in lines:
        # Look for lines containing both date and amount
        dates = re.findall(date_pattern, line)
        amounts = re.findall(amount_pattern, line)
        
        if dates and amounts:
            transaction = {
                'date': dates[0],
                'amount': float(amounts[0].replace(',', '')),
                'description': line.strip()
            }
            transactions.append(transaction)
    
    return transactions

def categorize_transactions(transactions: List[Dict]) -> List[Dict]:
    """Categorize transactions based on description patterns"""
    categories = []
    
    # Category patterns
    category_patterns = {
        'Food & Dining': [r'restaurant', r'cafe', r'food', r'dining'],
        'Shopping': [r'shop', r'store', r'retail', r'mall'],
        'Transportation': [r'uber', r'lyft', r'taxi', r'transport', r'fuel'],
        'Utilities': [r'electric', r'water', r'gas', r'internet', r'phone'],
        'Entertainment': [r'movie', r'theatre', r'netflix', r'spotify'],
        'Healthcare': [r'hospital', r'clinic', r'pharmacy', r'medical'],
        'Insurance': [r'insurance', r'policy'],
        'Education': [r'school', r'college', r'university', r'course'],
    }
    
    for transaction in transactions:
        desc = transaction['description'].lower()
        
        # Find matching category
        for category, patterns in category_patterns.items():
            if any(re.search(pattern, desc) for pattern in patterns):
                categories.append({
                    'transaction_id': id(transaction),
                    'suggested_category': category,
                    'confidence': 0.85  # Basic confidence score
                })
                break
                
    return categories