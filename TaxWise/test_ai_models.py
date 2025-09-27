"""
Test script to verify AI models are working correctly
Run this in Django shell: python manage.py shell < test_ai_models.py
"""

print("=" * 60)
print("TaxWise AI Models Test Script")
print("=" * 60)

try:
    # Test model manager
    from tax_optimization.ai_engine.model_loader import get_model_manager
    
    model_manager = get_model_manager()
    print(f"✓ Model Manager initialized")
    print(f"  - AI Enabled: {model_manager.is_ai_enabled()}")
    
    # Test transaction classifier
    print("\n1. Testing Transaction Classifier...")
    classifier = model_manager.get_model('transaction_classifier')
    if classifier:
        test_transactions = [
            "Salary credited by TCS Ltd",
            "Medical bill at Apollo Hospital", 
            "House rent payment",
            "ELSS mutual fund investment"
        ]
        
        for transaction in test_transactions:
            try:
                result = classifier(transaction)
                print(f"   '{transaction}' -> {result}")
            except Exception as e:
                print(f"   Error classifying '{transaction}': {e}")
    else:
        print("   ✗ Transaction classifier not available")
    
    # Test FinBERT model
    print("\n2. Testing Financial BERT Model...")
    finbert = model_manager.get_model('financial_bert')
    if finbert:
        print("   ✓ FinBERT model loaded successfully")
    else:
        print("   ✗ FinBERT model not available")
    
    # Test category classifier
    print("\n3. Testing Category Classifier...")
    category_classifier = model_manager.get_model('tax_category_classifier')
    if category_classifier:
        test_text = "Medical expenses at hospital"
        categories = ['Medical', 'Investment', 'Salary', 'Rent', 'Food']
        try:
            result = category_classifier(test_text, categories)
            print(f"   '{test_text}' -> {result}")
        except Exception as e:
            print(f"   Error with category classification: {e}")
    else:
        print("   ✗ Category classifier not available")
    
    # Test sentiment analyzer
    print("\n4. Testing Sentiment Analyzer...")
    sentiment = model_manager.get_model('sentiment_analyzer')
    if sentiment:
        test_texts = [
            "Great returns on my investment",
            "Lost money in stock market",
            "Stable income from salary"
        ]
        for text in test_texts:
            try:
                result = sentiment(text)
                print(f"   '{text}' -> {result}")
            except Exception as e:
                print(f"   Error analyzing sentiment: {e}")
    else:
        print("   ✗ Sentiment analyzer not available")
    
    # Test recommendation engine
    print("\n5. Testing Recommendation Engine...")
    rec_engine = model_manager.get_model('recommendation_model')
    if rec_engine:
        print("   ✓ Recommendation engine loaded successfully")
        
        # Test with sample data
        test_profile = {
            'annual_income': 1200000,
            'age': 30,
            'has_dependents': True
        }
        
        test_investments = []
        
        try:
            recommendations = rec_engine.generate_recommendations(test_profile, test_investments, [])
            print(f"   Generated {len(recommendations)} recommendations")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"   {i}. {rec.title} - Potential Savings: ₹{rec.potential_savings}")
        except Exception as e:
            print(f"   Error generating recommendations: {e}")
    else:
        print("   ✗ Recommendation engine not available")

    print("\n" + "=" * 60)
    print("AI Models Test Completed!")
    print("=" * 60)

except Exception as e:
    print(f"✗ Test failed with error: {e}")
    import traceback
    traceback.print_exc()