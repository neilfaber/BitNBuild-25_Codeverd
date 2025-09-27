"""
Django management command to initialize and preload AI models
Usage: python manage.py load_ai_models
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Initialize and preload AI models for tax optimization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload models even if they are already cached',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Load a specific model type (transaction_classifier, financial_bert, etc.)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting AI model initialization...'))
        
        try:
            from tax_optimization.ai_engine.model_loader import get_model_manager, initialize_models
            
            model_manager = get_model_manager()
            
            if options['force']:
                self.stdout.write('Clearing model cache...')
                model_manager.clear_cache()
            
            # Check if HuggingFace API key is available
            if not getattr(settings, 'HUGGING_FACE_API_KEY', None):
                self.stdout.write(
                    self.style.WARNING('No HuggingFace API key found in settings. Only rule-based models will be available.')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('HuggingFace API key detected. AI models will be enabled.')
                )
            
            if options['model']:
                # Load specific model
                model_type = options['model']
                self.stdout.write(f'Loading specific model: {model_type}')
                model = model_manager.get_model(model_type)
                if model:
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded {model_type}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to load {model_type}')
                    )
            else:
                # Load all models
                self.stdout.write('Loading all available models...')
                initialize_models()
                
                # Report status
                self.stdout.write('\nModel Status Report:')
                self.stdout.write('-' * 50)
                
                model_types = [
                    'transaction_classifier',
                    'financial_bert', 
                    'tax_category_classifier',
                    'sentiment_analyzer',
                    'recommendation_model'
                ]
                
                for model_type in model_types:
                    model = model_manager.get_model(model_type)
                    status = '✓ Loaded' if model else '✗ Failed/Disabled'
                    self.stdout.write(f'{model_type:<25} {status}')
                
                ai_status = 'Enabled' if model_manager.is_ai_enabled() else 'Disabled'
                self.stdout.write(f'\nAI Models Status: {ai_status}')
                
            self.stdout.write(
                self.style.SUCCESS('\nAI model initialization completed successfully!')
            )
            
        except Exception as e:
            logger.exception(f"Failed to initialize AI models: {str(e)}")
            raise CommandError(f'Model initialization failed: {str(e)}')