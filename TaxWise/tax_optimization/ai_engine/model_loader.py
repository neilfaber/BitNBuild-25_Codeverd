"""
AI Model Loader and Manager
Handles HuggingFace model initialization and caching for tax optimization
"""

import os
import logging
from typing import Dict, Any, Optional

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
            self.ai_enabled = False  # Disabled by default for stability
            logger.info(f"ModelManager initialized (AI models disabled for stability)")
    
    def load_transaction_classifier(self) -> Optional[Any]:
        """Load transaction classifier (currently using rule-based approach)"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using rule-based classification")
            return None
        
        # HuggingFace model loading code would go here when AI is enabled
        return None
    
    def load_financial_bert(self) -> Optional[Any]:
        """Load FinBERT model (currently disabled)"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using rule-based analysis")
            return None
        
        return None
    
    def load_custom_category_classifier(self) -> Optional[Any]:
        """Load custom fine-tuned model (currently disabled)"""
        if not self.ai_enabled:
            logger.info("AI models disabled - using keyword-based classification")
            return None
        
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
            # Only load rule-based recommendation engine by default
            self.get_model('recommendation_model')
        except Exception as e:
            logger.error(f"Failed to preload models: {str(e)}")
    
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