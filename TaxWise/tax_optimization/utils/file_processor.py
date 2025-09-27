"""
File Processing Utilities for Bank Statements and Financial Documents
Supports PDF, CSV, Excel files with transaction extraction
"""

import logging
import pandas as pd
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import io
import csv

# For PDF processing (install: pip install PyPDF2 pdfplumber)
try:
    import pdfplumber
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF processing libraries not installed. Install PyPDF2 and pdfplumber for PDF support.")

# For OCR support (install: pip install pytesseract pillow)
try:
    import pytesseract
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False
    logging.warning("OCR libraries not installed. Install pytesseract and pillow for OCR support.")

logger = logging.getLogger(__name__)

class BankStatementProcessor:
    """Process bank statements in various formats"""
    
    def __init__(self):
        self.date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY, DD-MM-YYYY
            r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}',  # YYYY/MM/DD, YYYY-MM-DD
            r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}',  # DD Mon YYYY
        ]
        
        self.amount_patterns = [
            r'[\d,]+\.\d{2}',  # Amount with decimal
            r'[\d,]+',         # Amount without decimal
        ]
        
        # Common bank statement formats
        self.bank_formats = {
            'SBI': {'date_col': 0, 'desc_col': 1, 'debit_col': 2, 'credit_col': 3, 'balance_col': 4},
            'HDFC': {'date_col': 0, 'desc_col': 1, 'debit_col': 2, 'credit_col': 3, 'balance_col': 4},
            'ICICI': {'date_col': 0, 'desc_col': 1, 'debit_col': 2, 'credit_col': 3, 'balance_col': 4},
            'AXIS': {'date_col': 0, 'desc_col': 1, 'debit_col': 2, 'credit_col': 3, 'balance_col': 4},
        }
    
    def process_csv_statement(self, file_path: str) -> List[Dict]:
        """Process CSV bank statement"""
        transactions = []
        
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not read CSV file with any supported encoding")
            
            # Auto-detect bank format
            bank_format = self.detect_bank_format(df.columns.tolist())
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    transaction = self.extract_transaction_from_row(row, bank_format)
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Failed to process row {index}: {str(e)}")
                    continue
            
            logger.info(f"Processed {len(transactions)} transactions from CSV")
            return transactions
            
        except Exception as e:
            logger.error(f"CSV processing error: {str(e)}")
            return []
    
    def process_excel_statement(self, file_path: str) -> List[Dict]:
        """Process Excel bank statement"""
        transactions = []
        
        try:
            # Read Excel file
            xl_file = pd.ExcelFile(file_path)
            
            # Try different sheet names commonly used
            sheet_names = ['Sheet1', 'Statement', 'Transactions', 'Account Statement']
            df = None
            
            for sheet_name in sheet_names:
                if sheet_name in xl_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    break
            
            if df is None:
                # Use first sheet
                df = pd.read_excel(file_path, sheet_name=0)
            
            # Auto-detect bank format
            bank_format = self.detect_bank_format(df.columns.tolist())
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    transaction = self.extract_transaction_from_row(row, bank_format)
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    logger.warning(f"Failed to process row {index}: {str(e)}")
                    continue
            
            logger.info(f"Processed {len(transactions)} transactions from Excel")
            return transactions
            
        except Exception as e:
            logger.error(f"Excel processing error: {str(e)}")
            return []
    
    def process_pdf_statement(self, file_path: str) -> List[Dict]:
        """Process PDF bank statement"""
        if not PDF_SUPPORT:
            raise ValueError("PDF processing not supported. Install PyPDF2 and pdfplumber.")
        
        transactions = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
            
            # Extract transactions from text
            transactions = self.extract_transactions_from_text(full_text)
            
            logger.info(f"Processed {len(transactions)} transactions from PDF")
            return transactions
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            return []
    
    def detect_bank_format(self, columns: List[str]) -> Dict:
        """Auto-detect bank statement format from column headers"""
        columns_lower = [col.lower().strip() for col in columns]
        
        format_mapping = {
            'date_col': None,
            'desc_col': None,
            'debit_col': None,
            'credit_col': None,
            'balance_col': None
        }
        
        # Date column detection
        date_keywords = ['date', 'txn date', 'transaction date', 'value date', 'posting date']
        for i, col in enumerate(columns_lower):
            if any(keyword in col for keyword in date_keywords):
                format_mapping['date_col'] = i
                break
        
        # Description column detection
        desc_keywords = ['description', 'particulars', 'details', 'narration', 'transaction details']
        for i, col in enumerate(columns_lower):
            if any(keyword in col for keyword in desc_keywords):
                format_mapping['desc_col'] = i
                break
        
        # Debit column detection
        debit_keywords = ['debit', 'withdrawal', 'debit amount', 'dr', 'out']
        for i, col in enumerate(columns_lower):
            if any(keyword in col for keyword in debit_keywords):
                format_mapping['debit_col'] = i
                break
        
        # Credit column detection
        credit_keywords = ['credit', 'deposit', 'credit amount', 'cr', 'in']
        for i, col in enumerate(columns_lower):
            if any(keyword in col for keyword in credit_keywords):
                format_mapping['credit_col'] = i
                break
        
        # Balance column detection
        balance_keywords = ['balance', 'closing balance', 'running balance', 'available balance']
        for i, col in enumerate(columns_lower):
            if any(keyword in col for keyword in balance_keywords):
                format_mapping['balance_col'] = i
                break
        
        return format_mapping
    
    def extract_transaction_from_row(self, row, bank_format: Dict) -> Optional[Dict]:
        """Extract transaction details from a data row"""
        try:
            # Get transaction date
            if bank_format['date_col'] is not None:
                date_str = str(row.iloc[bank_format['date_col']]).strip()
                transaction_date = self.parse_date(date_str)
                if not transaction_date:
                    return None
            else:
                return None
            
            # Get description
            description = ""
            if bank_format['desc_col'] is not None:
                description = str(row.iloc[bank_format['desc_col']]).strip()
            
            # Get amount (debit or credit)
            amount = 0
            transaction_type = "OTHER"
            
            if bank_format['debit_col'] is not None:
                debit_amount = self.parse_amount(str(row.iloc[bank_format['debit_col']]))
                if debit_amount > 0:
                    amount = -debit_amount  # Debit is negative
                    transaction_type = "EXPENSE"
            
            if bank_format['credit_col'] is not None:
                credit_amount = self.parse_amount(str(row.iloc[bank_format['credit_col']]))
                if credit_amount > 0:
                    amount = credit_amount  # Credit is positive
                    transaction_type = "INCOME"
            
            if amount == 0:
                return None
            
            return {
                'date': transaction_date,
                'description': description,
                'amount': abs(amount),
                'transaction_type': transaction_type,
                'raw_amount': amount
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract transaction: {str(e)}")
            return None
    
    def extract_transactions_from_text(self, text: str) -> List[Dict]:
        """Extract transactions from PDF text"""
        transactions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to extract transaction from line
            transaction = self.parse_transaction_line(line)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def parse_transaction_line(self, line: str) -> Optional[Dict]:
        """Parse a single line from PDF text to extract transaction"""
        try:
            # Look for date pattern
            date_match = None
            for pattern in self.date_patterns:
                match = re.search(pattern, line)
                if match:
                    date_match = match
                    break
            
            if not date_match:
                return None
            
            # Extract date
            date_str = date_match.group()
            transaction_date = self.parse_date(date_str)
            if not transaction_date:
                return None
            
            # Look for amount pattern
            amounts = []
            for pattern in self.amount_patterns:
                amounts.extend(re.findall(pattern, line))
            
            if not amounts:
                return None
            
            # Get the largest amount (likely the transaction amount)
            parsed_amounts = [self.parse_amount(amt) for amt in amounts]
            max_amount = max(parsed_amounts)
            
            if max_amount == 0:
                return None
            
            # Extract description (everything except date and amounts)
            description = line
            description = re.sub(date_match.group(), '', description)
            for amt in amounts:
                description = description.replace(amt, '')
            description = description.strip()
            
            return {
                'date': transaction_date,
                'description': description,
                'amount': max_amount,
                'transaction_type': 'OTHER'
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse line: {line} - {str(e)}")
            return None
    
    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str or date_str.lower() in ['nan', 'none', '']:
            return None
        
        # Remove extra whitespace
        date_str = re.sub(r'\s+', ' ', date_str.strip())
        
        # Common date formats
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y',
            '%Y/%m/%d', '%Y-%m-%d', '%Y/%d/%m', '%Y-%d-%m',
            '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y',
            '%d-%b-%Y', '%d-%B-%Y', '%b-%d-%Y', '%B-%d-%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try pandas date parsing as fallback
        try:
            return pd.to_datetime(date_str).date()
        except:
            logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        if not amount_str or amount_str.lower() in ['nan', 'none', '']:
            return 0.0
        
        # Remove currency symbols and whitespace
        amount_str = re.sub(r'[₹$€£,\s]', '', amount_str.strip())
        
        # Handle negative amounts
        is_negative = '-' in amount_str or '(' in amount_str
        amount_str = re.sub(r'[-()]', '', amount_str)
        
        try:
            amount = float(amount_str)
            return -amount if is_negative else amount
        except ValueError:
            return 0.0
    
    def validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Validate and clean extracted transactions"""
        valid_transactions = []
        
        for trans in transactions:
            # Check required fields
            if not all(key in trans for key in ['date', 'description', 'amount']):
                continue
            
            # Validate date
            if not isinstance(trans['date'], date):
                continue
            
            # Validate amount
            if trans['amount'] <= 0:
                continue
            
            # Clean description
            trans['description'] = self.clean_description(trans['description'])
            
            valid_transactions.append(trans)
        
        return valid_transactions
    
    def clean_description(self, description: str) -> str:
        """Clean transaction description"""
        if not description:
            return ""
        
        # Remove extra whitespace
        description = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            'UPI-', 'NEFT-', 'RTGS-', 'IMPS-', 'NACH-', 'ECS-',
            'CHQ-', 'DD-', 'POS-', 'ATM-', 'CASH-'
        ]
        
        for prefix in prefixes_to_remove:
            if description.startswith(prefix):
                description = description[len(prefix):].strip()
        
        return description

# Global processor instance
statement_processor = BankStatementProcessor()

def process_bank_statement(uploaded_file) -> List[Dict]:
    """Main function to process uploaded bank statement"""
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            transactions = statement_processor.process_csv_statement(temp_file_path)
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
            
        elif file_extension in ['xlsx', 'xls']:
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            transactions = statement_processor.process_excel_statement(temp_file_path)
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
            
        elif file_extension == 'pdf':
            if not PDF_SUPPORT:
                raise ValueError("PDF processing not supported. Install required libraries.")
            
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            transactions = statement_processor.process_pdf_statement(temp_file_path)
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
            
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        # Validate transactions
        validated_transactions = statement_processor.validate_transactions(transactions)
        
        logger.info(f"Successfully processed {len(validated_transactions)} valid transactions")
        return validated_transactions
        
    except Exception as e:
        logger.error(f"Bank statement processing failed: {str(e)}")
        raise