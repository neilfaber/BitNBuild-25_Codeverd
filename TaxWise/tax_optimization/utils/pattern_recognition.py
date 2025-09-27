"""
AI-Powered Transaction Pattern Recognition Engine
Identifies EMIs, SIPs, rent, insurance, and other recurring patterns
"""

import re
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict, Counter
from decimal import Decimal
import pandas as pd
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class TransactionPatternRecognizer:
    """AI-powered transaction pattern recognition system"""
    
    def __init__(self):
        # Transaction category keywords with weights
        self.category_patterns = {
            'EMI': {
                'keywords': [
                    'emi', 'loan', 'home loan', 'car loan', 'personal loan',
                    'education loan', 'equated monthly installment', 'mortgage',
                    'financing', 'hdfc home loan', 'sbi home loan', 'icici loan',
                    'axis loan', 'bajaj finserv', 'tata capital', 'mahindra finance',
                    'repayment', 'installment', 'ecs loan', 'nach loan'
                ],
                'patterns': [
                    r'.*loan.*emi.*', r'.*emi.*loan.*', r'.*home.*loan.*',
                    r'.*car.*loan.*', r'.*personal.*loan.*', r'.*education.*loan.*',
                    r'.*mortgage.*', r'.*financing.*', r'.*installment.*',
                    r'.*repayment.*'
                ],
                'weight': 0.9
            },
            'SIP': {
                'keywords': [
                    'sip', 'systematic investment plan', 'mutual fund',
                    'mf investment', 'sbi mf', 'hdfc mf', 'icici mf', 'axis mf',
                    'aditya birla', 'nippon', 'franklin templeton', 'invesco',
                    'dsp', 'kotak mf', 'reliance mf', 'tata mf', 'uti mf',
                    'mirae asset', 'l&t mf', 'ppfas', 'parag parikh'
                ],
                'patterns': [
                    r'.*sip.*', r'.*systematic.*investment.*', r'.*mutual.*fund.*',
                    r'.*mf.*investment.*', r'.*\bmf\b.*', r'.*fund.*house.*'
                ],
                'weight': 0.95
            },
            'RENT': {
                'keywords': [
                    'rent', 'house rent', 'home rent', 'apartment rent',
                    'flat rent', 'room rent', 'rental', 'lease', 'landlord',
                    'property rent', 'monthly rent', 'advance rent'
                ],
                'patterns': [
                    r'.*rent.*', r'.*rental.*', r'.*lease.*',
                    r'.*landlord.*', r'.*property.*rent.*'
                ],
                'weight': 0.85
            },
            'INSURANCE': {
                'keywords': [
                    'insurance', 'premium', 'lic', 'life insurance',
                    'health insurance', 'term insurance', 'car insurance',
                    'vehicle insurance', 'home insurance', 'travel insurance',
                    'hdfc ergo', 'icici lombard', 'bajaj allianz', 'star health',
                    'care health', 'max bupa', 'oriental insurance', 'new india',
                    'united india', 'national insurance', 'policy premium'
                ],
                'patterns': [
                    r'.*insurance.*', r'.*premium.*', r'.*\blic\b.*',
                    r'.*policy.*premium.*', r'.*life.*insurance.*',
                    r'.*health.*insurance.*', r'.*car.*insurance.*'
                ],
                'weight': 0.9
            },
            'UTILITIES': {
                'keywords': [
                    'electricity', 'gas', 'water', 'broadband', 'internet',
                    'mobile', 'phone', 'dth', 'cable', 'wifi', 'airtel',
                    'jio', 'vi', 'bsnl', 'tata sky', 'dish tv', 'sun direct',
                    'videocon', 'reliance digital tv', 'bill payment',
                    'utility bill', 'power bill', 'water bill'
                ],
                'patterns': [
                    r'.*electricity.*', r'.*gas.*bill.*', r'.*water.*bill.*',
                    r'.*broadband.*', r'.*internet.*', r'.*mobile.*',
                    r'.*phone.*', r'.*dth.*', r'.*cable.*', r'.*wifi.*',
                    r'.*utility.*bill.*', r'.*power.*bill.*'
                ],
                'weight': 0.8
            },
            'SALARY': {
                'keywords': [
                    'salary', 'sal credit', 'payroll', 'wages', 'income',
                    'monthly salary', 'net salary', 'gross salary',
                    'employee salary', 'company salary', 'sal transfer'
                ],
                'patterns': [
                    r'.*salary.*', r'.*sal.*credit.*', r'.*payroll.*',
                    r'.*wages.*', r'.*monthly.*salary.*', r'.*sal.*transfer.*'
                ],
                'weight': 0.95
            },
            'INVESTMENT': {
                'keywords': [
                    'investment', 'fd', 'fixed deposit', 'rd', 'recurring deposit',
                    'ppf', 'epf', 'nps', 'elss', 'equity', 'bond', 'debenture',
                    'gold', 'silver', 'crypto', 'bitcoin', 'shares', 'stock',
                    'trading', 'zerodha', 'upstox', 'groww', 'angelone'
                ],
                'patterns': [
                    r'.*investment.*', r'.*fixed.*deposit.*', r'.*recurring.*deposit.*',
                    r'.*\bfd\b.*', r'.*\brd\b.*', r'.*\bppf\b.*', r'.*\bepf\b.*',
                    r'.*\bnps\b.*', r'.*trading.*', r'.*shares.*', r'.*stock.*'
                ],
                'weight': 0.85
            },
            'SUBSCRIPTION': {
                'keywords': [
                    'subscription', 'netflix', 'prime', 'hotstar', 'spotify',
                    'youtube', 'apple music', 'amazon music', 'zee5',
                    'sony liv', 'voot', 'alt balaji', 'mx player',
                    'jio saavn', 'gaana', 'wynk', 'magazine', 'newspaper'
                ],
                'patterns': [
                    r'.*subscription.*', r'.*netflix.*', r'.*prime.*',
                    r'.*hotstar.*', r'.*spotify.*', r'.*youtube.*premium.*',
                    r'.*music.*subscription.*'
                ],
                'weight': 0.8
            },
            'GROCERY': {
                'keywords': [
                    'grocery', 'supermarket', 'big bazaar', 'dmart', 'reliance fresh',
                    'more', 'spencer', 'food bazaar', 'easyday', 'hypercity',
                    'nature basket', 'godrej nature', 'star bazaar',
                    'online grocery', 'bigbasket', 'grofers', 'amazon fresh'
                ],
                'patterns': [
                    r'.*grocery.*', r'.*supermarket.*', r'.*big.*bazaar.*',
                    r'.*dmart.*', r'.*reliance.*fresh.*', r'.*bigbasket.*',
                    r'.*grofers.*', r'.*amazon.*fresh.*'
                ],
                'weight': 0.7
            }
        }
        
        # Minimum confidence threshold for pattern recognition
        self.confidence_threshold = 0.6
        
        # Recurring transaction detection parameters
        self.recurrence_window_days = 35  # ±5 days from expected date
        self.min_occurrences = 3  # Minimum occurrences to consider recurring
        
    def analyze_transactions(self, transactions: List[Dict]) -> Dict:
        """
        Analyze all transactions and identify patterns
        Returns categorized transactions with confidence scores
        """
        try:
            if not transactions:
                return {'categorized_transactions': [], 'patterns': {}, 'summary': {}}
            
            # Sort transactions by date
            sorted_transactions = sorted(transactions, key=lambda x: x['date'])
            
            # Categorize transactions
            categorized_transactions = []
            for trans in sorted_transactions:
                category, confidence = self.classify_transaction(trans)
                trans_with_category = trans.copy()
                trans_with_category.update({
                    'predicted_category': category,
                    'confidence': confidence,
                    'is_recurring': False,
                    'recurrence_pattern': None
                })
                categorized_transactions.append(trans_with_category)
            
            # Detect recurring patterns
            recurring_patterns = self.detect_recurring_patterns(categorized_transactions)
            
            # Update transactions with recurrence information
            categorized_transactions = self.mark_recurring_transactions(
                categorized_transactions, recurring_patterns
            )
            
            # Generate summary statistics
            summary = self.generate_pattern_summary(categorized_transactions)
            
            return {
                'categorized_transactions': categorized_transactions,
                'patterns': recurring_patterns,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Transaction analysis failed: {str(e)}")
            return {'categorized_transactions': [], 'patterns': {}, 'summary': {}}
    
    def classify_transaction(self, transaction: Dict) -> Tuple[str, float]:
        """
        Classify a single transaction into a category
        Returns category and confidence score
        """
        description = transaction.get('description', '').lower().strip()
        amount = transaction.get('amount', 0)
        
        if not description:
            return 'OTHER', 0.0
        
        category_scores = {}
        
        # Calculate scores for each category
        for category, config in self.category_patterns.items():
            score = self.calculate_category_score(description, config)
            if score > 0:
                category_scores[category] = score * config['weight']
        
        # Find best matching category
        if not category_scores:
            return 'OTHER', 0.0
        
        best_category = max(category_scores.items(), key=lambda x: x[1])
        category, confidence = best_category
        
        # Apply confidence threshold
        if confidence < self.confidence_threshold:
            return 'OTHER', confidence
        
        return category, confidence
    
    def calculate_category_score(self, description: str, config: Dict) -> float:
        """Calculate matching score for a category"""
        keyword_score = 0.0
        pattern_score = 0.0
        
        # Keyword matching
        keywords = config['keywords']
        for keyword in keywords:
            if keyword in description:
                # Exact match gets higher score
                if keyword == description.strip():
                    keyword_score = 1.0
                    break
                else:
                    # Partial match based on keyword importance
                    match_ratio = len(keyword) / len(description)
                    keyword_score = max(keyword_score, match_ratio * 0.8)
        
        # Pattern matching
        patterns = config['patterns']
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                pattern_score = max(pattern_score, 0.7)
        
        # Combine scores
        final_score = max(keyword_score, pattern_score)
        
        # Boost score for exact keyword matches
        for keyword in keywords:
            if description.startswith(keyword) or description.endswith(keyword):
                final_score = min(final_score + 0.2, 1.0)
                break
        
        return final_score
    
    def detect_recurring_patterns(self, transactions: List[Dict]) -> Dict:
        """Detect recurring transaction patterns"""
        patterns = {}
        
        # Group transactions by category and similar amounts
        category_groups = defaultdict(list)
        
        for trans in transactions:
            category = trans.get('predicted_category', 'OTHER')
            if category != 'OTHER':
                category_groups[category].append(trans)
        
        # Analyze each category for recurring patterns
        for category, trans_list in category_groups.items():
            category_patterns = self.find_category_patterns(trans_list, category)
            if category_patterns:
                patterns[category] = category_patterns
        
        return patterns
    
    def find_category_patterns(self, transactions: List[Dict], category: str) -> List[Dict]:
        """Find recurring patterns within a category"""
        if len(transactions) < self.min_occurrences:
            return []
        
        patterns = []
        
        # Group by similar amounts (within 10% tolerance)
        amount_groups = self.group_by_similar_amounts(transactions)
        
        for amount_range, trans_group in amount_groups.items():
            if len(trans_group) < self.min_occurrences:
                continue
            
            # Check for temporal patterns
            temporal_pattern = self.detect_temporal_pattern(trans_group)
            
            if temporal_pattern:
                # Further group by similar descriptions
                desc_groups = self.group_by_similar_descriptions(trans_group)
                
                for desc_key, desc_transactions in desc_groups.items():
                    if len(desc_transactions) >= self.min_occurrences:
                        pattern = {
                            'pattern_id': f"{category}_{amount_range}_{desc_key}",
                            'category': category,
                            'description_pattern': desc_key,
                            'amount_range': amount_range,
                            'frequency': temporal_pattern['frequency'],
                            'next_expected_date': temporal_pattern['next_expected_date'],
                            'confidence': self.calculate_pattern_confidence(desc_transactions),
                            'transactions': desc_transactions,
                            'avg_amount': sum(t['amount'] for t in desc_transactions) / len(desc_transactions)
                        }
                        patterns.append(pattern)
        
        return patterns
    
    def group_by_similar_amounts(self, transactions: List[Dict], tolerance: float = 0.1) -> Dict:
        """Group transactions by similar amounts"""
        amount_groups = defaultdict(list)
        
        for trans in transactions:
            amount = trans['amount']
            
            # Find existing group with similar amount
            matched_group = None
            for existing_amount in amount_groups.keys():
                avg_amount = float(existing_amount.split('-')[0])
                if abs(amount - avg_amount) / avg_amount <= tolerance:
                    matched_group = existing_amount
                    break
            
            if matched_group:
                amount_groups[matched_group].append(trans)
            else:
                # Create new group
                group_key = f"{amount:.2f}-{amount:.2f}"
                amount_groups[group_key] = [trans]
        
        return amount_groups
    
    def group_by_similar_descriptions(self, transactions: List[Dict], similarity_threshold: float = 0.7) -> Dict:
        """Group transactions by similar descriptions"""
        desc_groups = defaultdict(list)
        
        for trans in transactions:
            description = trans['description']
            
            # Find most similar existing description
            best_match = None
            best_similarity = 0
            
            for existing_desc in desc_groups.keys():
                similarity = SequenceMatcher(None, description.lower(), existing_desc.lower()).ratio()
                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_match = existing_desc
            
            if best_match:
                desc_groups[best_match].append(trans)
            else:
                desc_groups[description] = [trans]
        
        return desc_groups
    
    def detect_temporal_pattern(self, transactions: List[Dict]) -> Optional[Dict]:
        """Detect temporal patterns in transaction dates"""
        if len(transactions) < self.min_occurrences:
            return None
        
        # Sort by date
        sorted_trans = sorted(transactions, key=lambda x: x['date'])
        
        # Calculate intervals between consecutive transactions
        intervals = []
        for i in range(1, len(sorted_trans)):
            interval = (sorted_trans[i]['date'] - sorted_trans[i-1]['date']).days
            intervals.append(interval)
        
        if not intervals:
            return None
        
        # Analyze intervals for patterns
        avg_interval = sum(intervals) / len(intervals)
        
        # Check if intervals are consistent (within tolerance)
        tolerance_days = 5
        consistent_intervals = [
            interval for interval in intervals
            if abs(interval - avg_interval) <= tolerance_days
        ]
        
        consistency_ratio = len(consistent_intervals) / len(intervals)
        
        if consistency_ratio >= 0.7:  # 70% of intervals are consistent
            # Determine frequency
            if 25 <= avg_interval <= 35:
                frequency = 'MONTHLY'
            elif 85 <= avg_interval <= 95:
                frequency = 'QUARTERLY'
            elif 175 <= avg_interval <= 195:
                frequency = 'SEMI_ANNUAL'
            elif 360 <= avg_interval <= 370:
                frequency = 'ANNUAL'
            elif 6 <= avg_interval <= 8:
                frequency = 'WEEKLY'
            elif 13 <= avg_interval <= 16:
                frequency = 'BI_WEEKLY'
            else:
                frequency = 'CUSTOM'
            
            # Predict next expected date
            last_date = sorted_trans[-1]['date']
            next_expected_date = last_date + timedelta(days=int(avg_interval))
            
            return {
                'frequency': frequency,
                'avg_interval_days': int(avg_interval),
                'next_expected_date': next_expected_date,
                'consistency_ratio': consistency_ratio
            }
        
        return None
    
    def calculate_pattern_confidence(self, transactions: List[Dict]) -> float:
        """Calculate confidence score for a recurring pattern"""
        if len(transactions) < self.min_occurrences:
            return 0.0
        
        # Base confidence from number of occurrences
        occurrence_score = min(len(transactions) / 12.0, 1.0)  # Max at 12 occurrences
        
        # Amount consistency score
        amounts = [t['amount'] for t in transactions]
        avg_amount = sum(amounts) / len(amounts)
        amount_variations = [abs(amt - avg_amount) / avg_amount for amt in amounts]
        amount_consistency = 1.0 - (sum(amount_variations) / len(amount_variations))
        
        # Description consistency score
        descriptions = [t['description'] for t in transactions]
        desc_consistency = self.calculate_description_consistency(descriptions)
        
        # Category confidence score
        category_confidences = [t.get('confidence', 0.5) for t in transactions]
        avg_category_confidence = sum(category_confidences) / len(category_confidences)
        
        # Combine scores
        total_confidence = (
            occurrence_score * 0.3 +
            amount_consistency * 0.3 +
            desc_consistency * 0.2 +
            avg_category_confidence * 0.2
        )
        
        return round(total_confidence, 3)
    
    def calculate_description_consistency(self, descriptions: List[str]) -> float:
        """Calculate consistency score for descriptions"""
        if len(descriptions) <= 1:
            return 1.0
        
        similarities = []
        for i in range(len(descriptions)):
            for j in range(i + 1, len(descriptions)):
                similarity = SequenceMatcher(None, descriptions[i].lower(), descriptions[j].lower()).ratio()
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def mark_recurring_transactions(self, transactions: List[Dict], patterns: Dict) -> List[Dict]:
        """Mark transactions that are part of recurring patterns"""
        pattern_transactions = set()
        
        # Collect all transaction IDs that are part of patterns
        for category, category_patterns in patterns.items():
            for pattern in category_patterns:
                for trans in pattern['transactions']:
                    # Use a combination of date, amount, and description as ID
                    trans_id = f"{trans['date']}_{trans['amount']}_{trans['description']}"
                    pattern_transactions.add(trans_id)
        
        # Update transactions
        updated_transactions = []
        for trans in transactions:
            trans_id = f"{trans['date']}_{trans['amount']}_{trans['description']}"
            
            if trans_id in pattern_transactions:
                # Find the specific pattern for this transaction
                pattern_info = self.find_transaction_pattern(trans, patterns)
                trans['is_recurring'] = True
                trans['recurrence_pattern'] = pattern_info
            else:
                trans['is_recurring'] = False
                trans['recurrence_pattern'] = None
            
            updated_transactions.append(trans)
        
        return updated_transactions
    
    def find_transaction_pattern(self, transaction: Dict, patterns: Dict) -> Optional[Dict]:
        """Find the specific pattern for a transaction"""
        category = transaction.get('predicted_category', 'OTHER')
        
        if category not in patterns:
            return None
        
        for pattern in patterns[category]:
            for pattern_trans in pattern['transactions']:
                if (pattern_trans['date'] == transaction['date'] and
                    pattern_trans['amount'] == transaction['amount'] and
                    pattern_trans['description'] == transaction['description']):
                    return {
                        'pattern_id': pattern['pattern_id'],
                        'frequency': pattern['frequency'],
                        'next_expected_date': pattern['next_expected_date'],
                        'confidence': pattern['confidence']
                    }
        
        return None
    
    def generate_pattern_summary(self, transactions: List[Dict]) -> Dict:
        """Generate summary statistics for patterns"""
        total_transactions = len(transactions)
        
        if total_transactions == 0:
            return {}
        
        # Category distribution
        category_counts = Counter(t.get('predicted_category', 'OTHER') for t in transactions)
        category_distribution = {
            cat: {'count': count, 'percentage': (count / total_transactions) * 100}
            for cat, count in category_counts.items()
        }
        
        # Recurring vs one-time transactions
        recurring_count = sum(1 for t in transactions if t.get('is_recurring', False))
        recurring_percentage = (recurring_count / total_transactions) * 100
        
        # Monthly spending by category
        monthly_spending = defaultdict(float)
        for trans in transactions:
            category = trans.get('predicted_category', 'OTHER')
            amount = trans.get('amount', 0)
            if trans.get('transaction_type') == 'EXPENSE' or trans.get('raw_amount', 0) < 0:
                monthly_spending[category] += amount
        
        # Confidence statistics
        confidences = [t.get('confidence', 0) for t in transactions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'total_transactions': total_transactions,
            'category_distribution': category_distribution,
            'recurring_transactions': {
                'count': recurring_count,
                'percentage': round(recurring_percentage, 2)
            },
            'monthly_spending_by_category': dict(monthly_spending),
            'average_confidence': round(avg_confidence, 3),
            'high_confidence_transactions': sum(1 for c in confidences if c >= 0.8),
            'categories_detected': len(category_counts)
        }

# Global recognizer instance
pattern_recognizer = TransactionPatternRecognizer()

def recognize_transaction_patterns(transactions: List[Dict]) -> Dict:
    """
    Main function to recognize patterns in transactions
    Returns analysis results with categories and patterns
    """
    return pattern_recognizer.analyze_transactions(transactions)

def predict_next_transactions(patterns: Dict) -> List[Dict]:
    """
    Predict upcoming transactions based on recurring patterns
    Returns list of predicted transactions
    """
    predictions = []
    
    for category, category_patterns in patterns.items():
        for pattern in category_patterns:
            if pattern['confidence'] >= 0.7:  # High confidence patterns only
                prediction = {
                    'predicted_date': pattern['next_expected_date'],
                    'category': category,
                    'description': pattern['description_pattern'],
                    'predicted_amount': pattern['avg_amount'],
                    'confidence': pattern['confidence'],
                    'frequency': pattern['frequency'],
                    'pattern_id': pattern['pattern_id']
                }
                predictions.append(prediction)
    
    # Sort by predicted date
    return sorted(predictions, key=lambda x: x['predicted_date'])