"""
AI Model Loader and Manager
Handles HuggingFace model initialization and caching for tax optimization
"""

import os
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """Singleton class to manage AI models for tax optimization"""
    
    _instance = None
    _models = {}
    _tokenizers = {}
    _pipelines = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            # Enable AI if HuggingFace API key is available
            self.ai_enabled = bool(getattr(settings, 'HUGGING_FACE_API_KEY', None))
            if self.ai_enabled:
                # Set the HuggingFace token
                os.environ['HUGGINGFACE_HUB_TOKEN'] = settings.HUGGING_FACE_API_KEY
                logger.info(f"ModelManager initialized with AI models enabled")
            else:
                logger.info(f"ModelManager initialized (AI models disabled - no API key)")
    
    def load_transaction_classifier(self) -> Optional[Any]:
        """Load transaction classifier using FinBERT or similar financial model"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using rule-based classification")
            return None
        
        if 'transaction_classifier' in self._models:
            return self._models['transaction_classifier']
        
        try:
            from transformers import pipeline, AutoTokenizer, AutoModel
            
            # Use a financial BERT model for transaction classification
            model_name = "ProsusAI/finbert"  # Financial BERT model
            
            logger.info(f"Loading transaction classifier: {model_name}")
            classifier = pipeline(
                "text-classification",
                model=model_name,
                tokenizer=model_name,
                device=-1  # Use CPU
            )
            
            self._models['transaction_classifier'] = classifier
            logger.info("Transaction classifier loaded successfully")
            return classifier
            
        except Exception as e:
            logger.error(f"Failed to load transaction classifier: {str(e)}")
            return None
    
    def load_financial_bert(self) -> Optional[Any]:
        """Load FinBERT model for financial text analysis"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using rule-based analysis")
            return None
        
        if 'financial_bert' in self._models:
            return self._models['financial_bert']
        
        try:
            from transformers import AutoTokenizer, AutoModel
            
            model_name = "ProsusAI/finbert"
            logger.info(f"Loading FinBERT model: {model_name}")
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            
            self._tokenizers['financial_bert'] = tokenizer
            self._models['financial_bert'] = model
            
            logger.info("FinBERT model loaded successfully")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {str(e)}")
            return None
    
    def load_custom_category_classifier(self) -> Optional[Any]:
        """Load custom fine-tuned model for tax category classification"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using keyword-based classification")
            return None
        
        if 'category_classifier' in self._models:
            return self._models['category_classifier']
        
        try:
            from transformers import pipeline
            
            # Use a general purpose text classifier for now
            # In production, you could fine-tune a model specifically for tax categories
            model_name = "facebook/bart-large-mnli"
            
            logger.info(f"Loading category classifier: {model_name}")
            classifier = pipeline(
                "zero-shot-classification",
                model=model_name,
                device=-1  # Use CPU
            )
            
            self._models['category_classifier'] = classifier
            logger.info("Category classifier loaded successfully")
            return classifier
            
        except Exception as e:
            logger.error(f"Failed to load category classifier: {str(e)}")
            return None
    
    def load_sentiment_analyzer(self) -> Optional[Any]:
        """Load sentiment analysis model for financial text"""
        if not self.ai_enabled:
            return None
        
        if 'sentiment_analyzer' in self._models:
            return self._models['sentiment_analyzer']
        
        try:
            from transformers import pipeline
            
            model_name = "ProsusAI/finbert"
            logger.info(f"Loading sentiment analyzer: {model_name}")
            
            sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=-1
            )
            
            self._models['sentiment_analyzer'] = sentiment_analyzer
            logger.info("Sentiment analyzer loaded successfully")
            return sentiment_analyzer
            
        except Exception as e:
            logger.error(f"Failed to load sentiment analyzer: {str(e)}")
            return None
    
    def load_recommendation_model(self) -> Optional[Any]:
        """Load model for generating tax optimization recommendations"""
        try:
            # Use rule-based approach (always available)
            from .recommendation_engine import RuleBasedRecommendationEngine
            
            engine = RuleBasedRecommendationEngine()
            self._models['recommendation_model'] = engine
            
            logger.info(f"Rule-based recommendation engine loaded")
            return engine
            
        except Exception as e:
            logger.error(f"Failed to load recommendation model: {str(e)}")
            return None
    
    def get_model(self, model_type: str) -> Optional[Any]:
        """Get a loaded model by type"""
        if model_type == 'transaction_classifier':
            return self.load_transaction_classifier()
        elif model_type == 'financial_bert':
            return self.load_financial_bert()
        elif model_type == 'tax_category_classifier':
            return self.load_custom_category_classifier()
        elif model_type == 'sentiment_analyzer':
            return self.load_sentiment_analyzer()
        elif model_type == 'recommendation_model':
            return self.load_recommendation_model()
        else:
            logger.warning(f"Unknown model type: {model_type}")
            return None
    
    def enable_ai_models(self):
        """Enable AI models (requires HuggingFace transformers)"""
        try:
            import torch
            from transformers import pipeline
            self.ai_enabled = True
            logger.info("AI models enabled")
        except ImportError:
            logger.warning("HuggingFace transformers not available - keeping AI disabled")
    
    def preload_all_models(self):
        """Preload available models"""
        try:
            logger.info("Preloading AI models...")
            
            # Always load rule-based recommendation engine
            self.get_model('recommendation_model')
            
            if self.ai_enabled:
                # Load AI models in background
                models_to_load = [
                    'transaction_classifier',
                    'financial_bert',
                    'tax_category_classifier',
                    'sentiment_analyzer'
                ]
                
                for model_type in models_to_load:
                    try:
                        logger.info(f"Loading {model_type}...")
                        self.get_model(model_type)
                    except Exception as e:
                        logger.error(f"Failed to load {model_type}: {str(e)}")
                        continue
                        
                logger.info("AI models preloading completed")
            else:
                logger.info("AI models disabled - only rule-based engines loaded")
                
        except Exception as e:
            logger.error(f"Failed to preload models: {str(e)}")
    
    def get_tokenizer(self, model_type: str) -> Optional[Any]:
        """Get tokenizer for a specific model type"""
        return self._tokenizers.get(model_type)
    
    def is_ai_enabled(self) -> bool:
        """Check if AI models are enabled"""
        return self.ai_enabled
    
    def clear_cache(self):
        """Clear all cached models"""
        self._models.clear()
        self._tokenizers.clear()
        self._pipelines.clear()
        logger.info("Model cache cleared")

# Global model manager instance
model_manager = ModelManager()

def initialize_models():
    """Initialize available AI models - called during Django startup"""
    try:
        logger.info("Initializing AI models...")
        model_manager.preload_all_models()
        logger.info("AI models initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize AI models: {str(e)}")

def get_model_manager() -> ModelManager:
    """Get the global model manager instance"""
    return model_manager