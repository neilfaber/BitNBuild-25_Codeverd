from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.utils import timezone
import json
from bank_analyzer.models import UploadedPDF, Transaction
from .utils import process_statement, detect_statement_type, extract_transactions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
def status(request):
    """Check server status and return basic info"""
    return Response({
        'status': 'online',
        'timestamp': timezone.now(),
        'authenticated': request.user.is_authenticated
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_statement(request):
    """Handle statement upload from extension"""
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file provided'}, status=400)
            
        # Detect statement type and validate
        file_type = detect_statement_type(uploaded_file)
        if not file_type:
            return Response({'error': 'Invalid file type'}, status=400)
            
        # Save the file
        pdf_instance = UploadedPDF.objects.create(
            user=request.user,
            file=uploaded_file,
            filename=uploaded_file.name,
            auto_uploaded=True,
            file_type=file_type
        )
        
        # Process and categorize
        try:
            processing_result = process_statement(pdf_instance)
            transactions = extract_transactions(pdf_instance)
            
            # Save extracted transactions
            for trans in transactions:
                Transaction.objects.create(
                    pdf=pdf_instance,
                    date=trans['date'],
                    description=trans['description'],
                    amount=trans['amount'],
                    category=trans.get('category', 'Uncategorized')
                )
                
            return Response({
                'status': 'success',
                'message': 'Statement processed successfully',
                'id': pdf_instance.id,
                'transactions_count': len(transactions),
                'categories': processing_result.get('categories', []),
                'summary': {
                    'total_amount': sum(t['amount'] for t in transactions),
                    'date_range': {
                        'start': min(t['date'] for t in transactions),
                        'end': max(t['date'] for t in transactions)
                    }
                }
            })
            
        except Exception as e:
            # If processing fails, still save the file but return error
            return Response({
                'status': 'partial',
                'message': 'File saved but processing failed',
                'id': pdf_instance.id,
                'error': str(e)
            }, status=206)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_uploads(request):
    """Get user's recent uploads"""
    try:
        uploads = UploadedPDF.objects.filter(
            user=request.user,
            auto_uploaded=True
        ).order_by('-uploaded_at')[:5]
        
        return Response({
            'uploads': [{
                'id': upload.id,
                'filename': upload.filename,
                'uploaded_at': upload.uploaded_at,
                'status': upload.status,
                'transaction_count': upload.transaction_set.count()
            } for upload in uploads]
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_categories(request, pdf_id):
    """Update transaction categories for a statement"""
    try:
        pdf = UploadedPDF.objects.get(id=pdf_id, user=request.user)
        categories = request.data.get('categories', [])
        
        for cat in categories:
            Transaction.objects.filter(
                pdf=pdf,
                id=cat['transaction_id']
            ).update(category=cat['category'])
            
        return Response({
            'message': 'Categories updated successfully',
            'updated_count': len(categories)
        })
        
    except UploadedPDF.DoesNotExist:
        return Response({'error': 'Statement not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
