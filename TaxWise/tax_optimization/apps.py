from django.apps import AppConfig

class TaxOptimizationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tax_optimization'
    verbose_name = 'AI Tax Optimization Engine'
    
    def ready(self):
        """Initialize AI models and load configurations when Django starts"""
        print("Tax optimization app is ready!")
        # Disable AI model loading for now to allow server to start
        # try:
        #     # Import AI model initialization
        #     from .ai_engine.model_loader import initialize_models
        #     initialize_models()
        # except ImportError:
        #     pass  # AI models not yet implemented