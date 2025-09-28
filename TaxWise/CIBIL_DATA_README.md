# CIBIL Sample Data Population Scripts

This directory contains scripts to populate the database with realistic credit card statement data for demonstrating the CIBIL score analysis functionality.

## 📋 What Gets Created

The scripts generate:
- **Multiple credit cards** per user (3 cards by default)
- **12 months of transaction history** per card
- **Realistic transaction patterns** (shopping, dining, fuel, etc.)
- **Payment behaviors** based on CIBIL scenarios
- **Late payment fees** and interest charges (scenario-dependent)
- **CIBIL score calculations** based on generated data

## 🚀 Quick Start (Recommended)

### Option 1: Auto-populate All Scenarios
```bash
cd c:\Codes\BNnB2025\BitNBuild-25_Codeverd\TaxWise
python populate_sample_data.py
```

This creates 4 test users with different CIBIL scenarios:
- `excellent_user` (750-850 score)
- `good_user` (650-749 score) 
- `fair_user` (550-649 score)
- `poor_user` (350-549 score)

All users have password: `test123`

### Option 2: Manual Population

```bash
# Create data for specific user
python manage.py populate_cibil_data --username=admin --scenario=good

# Create new user with data
python manage.py populate_cibil_data --create_user=john_doe --scenario=excellent

# Advanced options
python manage.py populate_cibil_data --user_id=1 --months=18 --cards=4 --scenario=fair
```

## 🎯 Available Scenarios

### Excellent (750-850)
- **Credit Utilization**: 5-25%
- **Payment Behavior**: 95-100% of balance paid
- **Late Payment Probability**: 2%
- **Credit Limits**: ₹1,00,000 - ₹3,00,000

### Good (650-749)  
- **Credit Utilization**: 15-45%
- **Payment Behavior**: 85-100% of balance paid
- **Late Payment Probability**: 5%
- **Credit Limits**: ₹50,000 - ₹2,00,000

### Fair (550-649)
- **Credit Utilization**: 35-65%
- **Payment Behavior**: 25-85% of balance paid
- **Late Payment Probability**: 12%
- **Credit Limits**: ₹30,000 - ₹1,00,000

### Poor (350-549)
- **Credit Utilization**: 60-90%
- **Payment Behavior**: 5-35% of balance paid
- **Late Payment Probability**: 25%
- **Credit Limits**: ₹20,000 - ₹50,000

## 🏦 Generated Banks & Cards

The script creates cards from these Indian banks:
- HDFC Bank (Visa)
- ICICI Bank (Mastercard)
- SBI Bank (Visa)
- Axis Bank (Mastercard)
- Kotak Bank (Visa)

## 💳 Transaction Categories

Realistic Indian spending patterns:
- **Dining**: McDonald's, Domino's, Zomato, Swiggy
- **Shopping**: Amazon, Flipkart, Myntra, Big Bazaar
- **Fuel**: Indian Oil, Shell petrol pumps
- **Grocery**: DMart, Spencer's, Metro Cash & Carry
- **Entertainment**: BookMyShow, PVR Cinemas
- **Transport**: Uber rides

## 📊 Command Options

```bash
python manage.py populate_cibil_data [OPTIONS]

Options:
  --user_id=ID          Target user by ID
  --username=NAME       Target user by username  
  --create_user=NAME    Create new user
  --months=N            Months of data (default: 12)
  --cards=N             Number of cards (default: 3)
  --scenario=TYPE       Scenario: excellent|good|fair|poor
  --help                Show help
```

## 🔍 Testing the Results

After running the scripts:

1. **Login** with created users:
   - URL: http://127.0.0.1:8000/auth/login/
   - Use credentials shown after script completion

2. **View CIBIL Dashboard**:
   - URL: http://127.0.0.1:8000/cibil/dashboard/
   - See calculated scores and analysis

3. **Explore Features**:
   - Score Analysis: `/cibil/analysis/`
   - Improve Score: `/cibil/improve/`
   - What-If Scenarios: `/cibil/what-if/`
   - Score History: `/cibil/history/`

## 🗑️ Cleanup

To clear data for a specific user:
```bash
# The script automatically clears existing data before creating new data
python manage.py populate_cibil_data --username=testuser --scenario=good
```

To clear all data:
```python
# In Django shell
from bank_analyzer.models import CreditCardStatement
from cibil.models import CIBILScore
CreditCardStatement.objects.all().delete()
CIBILScore.objects.all().delete()
```

## 🔧 Troubleshooting

### Common Issues:

1. **User not found**: Use `--create_user` to create a new user
2. **Permission denied**: Ensure you're running from the correct directory
3. **Module not found**: Make sure Django is properly set up

### Data Verification:

```python
# Check created data in Django shell
from bank_analyzer.models import CreditCardStatement
from cibil.models import CIBILScore
from django.contrib.auth.models import User

# View users
User.objects.all()

# View statements
CreditCardStatement.objects.all()

# View CIBIL scores  
CIBILScore.objects.all()
```

## 📝 Notes

- Transaction amounts are in Indian Rupees (₹)
- All dates are relative to current date
- Credit card numbers use realistic last-4-digit patterns
- Reward points and cashback are calculated automatically
- Late fees are added based on scenario probabilities
- Payment dates simulate real-world payment patterns