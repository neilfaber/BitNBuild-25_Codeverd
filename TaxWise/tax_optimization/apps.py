from django.apps import AppConfig

class TaxOptimizationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tax_optimization'
    verbose_name = 'AI Tax Optimization Engine'
    
    def ready(self):
        """Initialize AI models and load configurations when Django starts"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from .ai_engine.model_loader import initialize_models
            logger.info("Initializing AI models on startup...")
            initialize_models()
            logger.info("Tax optimization app is ready with AI models!")
        except Exception as e:
            logger.warning(f"Failed to initialize AI models on startup: {e}")
            logger.info("Tax optimization app is ready (rule-based mode)!")