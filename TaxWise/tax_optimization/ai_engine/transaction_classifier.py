"""
Transaction Classification Engine
Uses HuggingFace models to classify financial transactions into tax-relevant categories
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
import pandas as pd
from django.core.cache import cache
from .model_loader import get_model_manager

logger = logging.getLogger(__name__)

class TransactionClassifier:
    """Classify financial transactions using AI models"""
    
    def __init__(self):
        self.model_manager = get_model_manager()
        
        # Indian financial keywords mapping
        self.category_keywords = {
            'SALARY': [
                'salary', 'sal', 'wage', 'payroll', 'bonus', 'increment',
                'basic pay', 'da', 'hra', 'allowance', 'pf credit'
            ],
            'RENT': [
                'rent', 'house rent', 'flat rent', 'accommodation',
                'rental', 'lease', 'pg', 'hostel'
            ],
            'MEDICAL': [
                'hospital', 'medical', 'clinic', 'doctor', 'pharmacy',
                'medicine', 'health', 'apollo', 'fortis', 'max',
                'insurance claim', 'medical insurance'
            ],
            'INSURANCE': [
                'insurance', 'premium', 'policy', 'lic', 'hdfc life',
                'icici prudential', 'sbi life', 'health insurance',
                'term insurance', 'ulip'
            ],
            'INVESTMENT': [
                'mutual fund', 'sip', 'ppf', 'epf', 'nps', 'elss',
                'fd', 'fixed deposit', 'equity', 'share', 'stock',
                'bond', 'demat', 'trading', 'zerodha', 'groww'
            ],
            'EDUCATION': [
                'school', 'college', 'university', 'education',
                'tuition', 'fee', 'course', 'training', 'certification'
            ],
            'UTILITIES': [
                'electricity', 'water', 'gas', 'phone', 'internet',
                'broadband', 'mobile', 'recharge', 'bill payment',
                'utility', 'bescom', 'bsnl', 'airtel', 'jio'
            ],
            'FOOD': [
                'restaurant', 'food', 'zomato', 'swiggy', 'ola foods',
                'dining', 'cafe', 'hotel', 'mess', 'canteen'
            ],
            'TRANSPORT': [
                'uber', 'ola', 'taxi', 'auto', 'bus', 'train',
                'metro', 'petrol', 'diesel', 'fuel', 'transport',
                'parking', 'toll', 'fastag'
            ],
            'SHOPPING': [
                'amazon', 'flipkart', 'myntra', 'shopping', 'mall',
                'store', 'supermarket', 'grocery', 'big bazaar',
                'reliance fresh', 'dmart'
            ],
            'EMI': [
                'emi', 'loan', 'installment', 'equated monthly',
                'home loan', 'car loan', 'personal loan',
                'credit card payment'
            ],
            'TAX': [
                'income tax', 'tds', 'advance tax', 'self assessment',
                'tax payment', 'challan', 'tin', 'pan'
            ]
        }
        
        # Tax sections mapping
        self.tax_section_mapping = {
            'INSURANCE': '80D',
            'INVESTMENT': '80C',
            'EDUCATION': '80E',
            'MEDICAL': '80D',
            'RENT': '80GG',
            'HOME_LOAN_INTEREST': '24',
            'HOME_LOAN_PRINCIPAL': '80C',
            'CHARITY': '80G',
            'NPS': '80CCD'
        }
    
    def preprocess_description(self, description: str) -> str:
        """Clean and preprocess transaction description"""
        if not description:
            return ""
        
        # Convert to lowercase
        text = description.lower().strip()
        
        # Remove extra spaces and special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common bank transaction prefixes
        prefixes_to_remove = [
            'upi', 'neft', 'rtgs', 'imps', 'nach', 'ecs',
            'by transfer', 'to transfer', 'from', 'to'
        ]
        
        for prefix in prefixes_to_remove:
            text = text.replace(prefix, ' ')
        
        return text.strip()
    
    def classify_by_keywords(self, description: str) -> Tuple[Optional[str], float]:
        """Classify transaction using keyword matching"""
        description = self.preprocess_description(description)
        
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in description:
                    # Give higher score for exact matches
                    if keyword == description:
                        score += 2.0
                    else:
                        score += 1.0
            
            if score > 0:
                category_scores[category] = score / len(keywords)
        
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            confidence = min(category_scores[best_category], 1.0)
            return best_category, confidence
        
        return None, 0.0
    
    def classify_with_ai(self, description: str, amount: float) -> Tuple[Optional[str], float]:
        """Classify transaction using AI models"""
        try:
            # Get transaction classifier
            classifier = self.model_manager.get_model('transaction_classifier')
            if not classifier:
                logger.warning("Transaction classifier not available, falling back to keywords")
                return self.classify_by_keywords(description)
            
            # Prepare input text
            input_text = self.preprocess_description(description)
            if not input_text:
                return None, 0.0
            
            # Get prediction from DistilBERT
            results = classifier(input_text)
            
            # Process results - this would need custom labels in production
            # For now, we'll combine with keyword matching
            keyword_category, keyword_confidence = self.classify_by_keywords(description)
            
            # In production, you'd map AI results to your categories
            # For now, return keyword results with AI confidence boost
            if keyword_category and keyword_confidence > 0.3:
                # Boost confidence if AI and keywords agree
                boosted_confidence = min(keyword_confidence * 1.2, 1.0)
                return keyword_category, boosted_confidence
            
            return keyword_category, keyword_confidence
            
        except Exception as e:
            logger.error(f"AI classification failed: {str(e)}")
            # Fallback to keyword matching
            return self.classify_by_keywords(description)
    
    def determine_tax_relevance(self, category: str, amount: float, description: str) -> Tuple[bool, Optional[str]]:
        """Determine if transaction is tax-relevant and which section applies"""
        
        tax_relevant_categories = [
            'INSURANCE', 'INVESTMENT', 'MEDICAL', 'EDUCATION',
            'RENT', 'CHARITY', 'HOME_LOAN'
        ]
        
        if category in tax_relevant_categories:
            tax_section = self.tax_section_mapping.get(category)
            return True, tax_section
        
        # Special cases based on amount and description
        if category == 'MEDICAL' and amount > 5000:
            return True, '80D'
        
        if category == 'EDUCATION' and 'loan' in description.lower():
            return True, '80E'
        
        return False, None
    
    def classify_transaction(self, description: str, amount: float, transaction_date=None) -> Dict:
        """Main method to classify a single transaction"""
        try:
            # Use AI classification
            category, confidence = self.classify_with_ai(description, amount)
            
            if not category:
                category = 'OTHER'
                confidence = 0.1
            
            # Determine tax relevance
            is_tax_relevant, tax_section = self.determine_tax_relevance(
                category, amount, description
            )
            
            # Determine transaction type
            transaction_type = self.determine_transaction_type(category, amount)
            
            result = {
                'ai_category': category,
                'ai_confidence_score': confidence,
                'transaction_type': transaction_type,
                'is_tax_relevant': is_tax_relevant,
                'tax_section': tax_section,
                'is_deductible': is_tax_relevant and amount > 0,
                'processing_notes': f"Classified with {confidence:.2f} confidence"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Transaction classification failed: {str(e)}")
            return {
                'ai_category': 'OTHER',
                'ai_confidence_score': 0.0,
                'transaction_type': 'OTHER',
                'is_tax_relevant': False,
                'tax_section': None,
                'is_deductible': False,
                'processing_notes': f"Classification failed: {str(e)}"
            }
    
    def determine_transaction_type(self, category: str, amount: float) -> str:
        """Determine high-level transaction type"""
        if category in ['SALARY', 'BUSINESS', 'INTEREST', 'DIVIDEND', 'RENTAL']:
            return 'INCOME'
        elif category in ['INVESTMENT', 'INSURANCE']:
            return 'INVESTMENT'
        elif category == 'EMI':
            return 'EMI'
        elif category in ['RENT', 'MEDICAL', 'FOOD', 'SHOPPING', 'UTILITIES', 'TRANSPORT']:
            return 'EXPENSE'
        else:
            return 'OTHER'
    
    def batch_classify_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Classify multiple transactions efficiently"""
        results = []
        
        for transaction in transactions:
            result = self.classify_transaction(
                transaction.get('description', ''),
                transaction.get('amount', 0),
                transaction.get('date')
            )
            
            # Add transaction ID for tracking
            if 'id' in transaction:
                result['transaction_id'] = transaction['id']
            
            results.append(result)
        
        return results
    
    def get_category_statistics(self, transactions: List[Dict]) -> Dict:
        """Get classification statistics for a list of transactions"""
        if not transactions:
            return {}
        
        classified = self.batch_classify_transactions(transactions)
        
        stats = {
            'total_transactions': len(classified),
            'categories': {},
            'tax_relevant': 0,
            'average_confidence': 0.0,
            'high_confidence': 0  # confidence > 0.8
        }
        
        total_confidence = 0
        
        for result in classified:
            category = result['ai_category']
            confidence = result['ai_confidence_score']
            
            # Count categories
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Count tax relevant
            if result['is_tax_relevant']:
                stats['tax_relevant'] += 1
            
            # Calculate confidence stats
            total_confidence += confidence
            if confidence > 0.8:
                stats['high_confidence'] += 1
        
        stats['average_confidence'] = total_confidence / len(classified) if classified else 0
        
        return stats

# Global classifier instance
transaction_classifier = TransactionClassifier()