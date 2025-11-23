"""
Test script to verify confidence variation and classic car warnings
"""
import sys
sys.path.append('c:\\Users\\Igor Cretu\\Desktop\\Bachelor\\Project\\BackEnd\\API')

from app.ml.predictor import CarPricePredictor

predictor = CarPricePredictor()

print("=" * 60)
print("Testing Confidence Variation and Classic Car Warnings")
print("=" * 60)

# Test 1: Classic car (1961 Ferrari)
print("\n1. Classic Car (1961 Ferrari):")
result1 = predictor.predict({
    'brand': 'Ferrari',
    'model': '250 GTE',
    'year': 1961,
    'mileage': 71300,
    'fuel_type': 'Petrol',
    'transmission': 'Manual',
    'body_type': 'Coupe'
})
print(f"   Predicted Price: {result1['predicted_price']:,.0f} DKK")
print(f"   Confidence: {result1['confidence']:.1f}%")
if 'warning' in result1:
    print(f"   Warning: {result1['warning']}")

# Test 2: Old car (1995)
print("\n2. Old Car (1995 Toyota Corolla):")
result2 = predictor.predict({
    'brand': 'Toyota',
    'model': 'Corolla',
    'year': 1995,
    'mileage': 150000,
    'fuel_type': 'Petrol',
    'transmission': 'Manual',
    'body_type': 'Sedan'
})
print(f"   Predicted Price: {result2['predicted_price']:,.0f} DKK")
print(f"   Confidence: {result2['confidence']:.1f}%")
if 'warning' in result2:
    print(f"   Warning: {result2['warning']}")

# Test 3: Older modern car (2009)
print("\n3. Older Modern Car (2009 BMW 3 Series):")
result3 = predictor.predict({
    'brand': 'BMW',
    'model': '320d',
    'year': 2009,
    'mileage': 180000,
    'fuel_type': 'Diesel',
    'transmission': 'Automatic',
    'body_type': 'Sedan'
})
print(f"   Predicted Price: {result3['predicted_price']:,.0f} DKK")
print(f"   Confidence: {result3['confidence']:.1f}%")
if 'warning' in result3:
    print(f"   Warning: {result3['warning']}")

# Test 4: Recent car (2020)
print("\n4. Recent Car (2020 Tesla Model 3):")
result4 = predictor.predict({
    'brand': 'Tesla',
    'model': 'Model 3',
    'year': 2020,
    'mileage': 45000,
    'fuel_type': 'Electricity',
    'transmission': 'Automatic',
    'body_type': 'Sedan',
    'horsepower': 283
})
print(f"   Predicted Price: {result4['predicted_price']:,.0f} DKK")
print(f"   Confidence: {result4['confidence']:.1f}%")
if 'warning' in result4:
    print(f"   Warning: {result4['warning']}")

# Test 5: New car with missing data (2024)
print("\n5. New Car with Missing Data (2024 VW Golf):")
result5 = predictor.predict({
    'brand': 'Volkswagen',
    'model': 'Golf',
    'year': 2024,
    'mileage': 0,  # New car
    'fuel_type': 'Petrol',
    'transmission': 'Automatic',
    'body_type': 'Hatchback'
    # Missing horsepower
})
print(f"   Predicted Price: {result5['predicted_price']:,.0f} DKK")
print(f"   Confidence: {result5['confidence']:.1f}%")
if 'warning' in result5:
    print(f"   Warning: {result5['warning']}")

print("\n" + "=" * 60)
print("Confidence should now vary based on:")
print("  - Car age (pre-2000: 30-55%, 2000-2010: ~79%, 2010+: ~89%)")
print("  - Missing data (reduces confidence by 5%)")
print("  - Classic cars show warning message")
print("=" * 60)
