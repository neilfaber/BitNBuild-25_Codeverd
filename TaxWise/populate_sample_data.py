"""
Quick Credit Card Data Population Script
Run directly: python populate_sample_data.py
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to the path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TaxWise.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command

def main():
    print("🚀 CIBIL Credit Card Data Population Script")
    print("=" * 50)
    
    # Check if admin user exists
    try:
        admin_user = User.objects.get(username='admin')
        print(f"✓ Found admin user: {admin_user.username}")
    except User.DoesNotExist:
        print("Creating admin user...")
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True
        )
        print(f"✓ Created admin user: {admin_user.username}")

    # Create sample users with different CIBIL scenarios
    scenarios = [
        ('excellent_user', 'excellent', 'John Doe'),
        ('good_user', 'good', 'Jane Smith'), 
        ('fair_user', 'fair', 'Mike Johnson'),
        ('poor_user', 'poor', 'Sarah Wilson')
    ]
    
    for username, scenario, full_name in scenarios:
        first_name, last_name = full_name.split(' ', 1)
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'password': 'pbkdf2_sha256$600000$test123$hash',  # password: test123
                'first_name': first_name,
                'last_name': last_name,
                'is_active': True
            }
        )
        
        if created:
            user.set_password('test123')
            user.save()
        
        print(f"\n📊 Creating {scenario} scenario data for {user.username}...")
        
        # Call the management command
        call_command(
            'populate_cibil_data',
            user_id=user.id,
            months=12,
            cards=3,
            scenario=scenario,
            verbosity=1
        )
        
        print(f"✅ Completed {scenario} scenario for {user.username}")
    
    print("\n" + "=" * 50)
    print("🎉 All sample data created successfully!")
    print("\n📝 Test Users Created:")
    print("Username: admin | Password: admin123 | Scenario: N/A")
    print("Username: excellent_user | Password: test123 | CIBIL: 750-850")
    print("Username: good_user | Password: test123 | CIBIL: 650-749")  
    print("Username: fair_user | Password: test123 | CIBIL: 550-649")
    print("Username: poor_user | Password: test123 | CIBIL: 350-549")
    
    print("\n🔗 Access the application:")
    print("1. Login: http://127.0.0.1:8000/auth/login/")
    print("2. CIBIL Dashboard: http://127.0.0.1:8000/cibil/dashboard/")
    print("3. Score Analysis: http://127.0.0.1:8000/cibil/analysis/")
    print("4. Improve Score: http://127.0.0.1:8000/cibil/improve/")
    print("5. What-If Analysis: http://127.0.0.1:8000/cibil/what-if/")
    
    print("\n💡 Tips:")
    print("- Try different users to see varying CIBIL scenarios")
    print("- Each user has 12 months of credit card transaction history")
    print("- 3 different bank credit cards per user")
    print("- Realistic transaction patterns and payment behaviors")

if __name__ == '__main__':
    main()