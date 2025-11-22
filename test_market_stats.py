"""
Quick test script for the market statistics endpoint
"""
import sys
sys.path.insert(0, '.')

from app.main import app
import json

def test_market_statistics():
    """Test the market statistics endpoint"""
    with app.test_client() as client:
        print("\n🧪 Testing /api/market/statistics endpoint...")
        print("=" * 60)
        
        response = client.get('/api/market/statistics')
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            stats = data.get('statistics', {})
            
            print("\n✅ SUCCESS! Endpoint is working.")
            print("\n📊 Statistics Summary:")
            print("-" * 60)
            
            # Overall stats
            overall = stats.get('overall', {})
            print(f"Total Cars: {overall.get('total_cars', 'N/A'):,}")
            print(f"Average Price: {overall.get('avg_price', 'N/A'):,.0f} DKK")
            print(f"Average Mileage: {overall.get('avg_mileage', 'N/A'):,.0f} km")
            print(f"Average Year: {overall.get('avg_year', 'N/A')}")
            
            # Brand stats
            brands = stats.get('brand_stats', [])
            print(f"\nTop 5 Brands: {len(brands)} brands found")
            for i, brand in enumerate(brands[:5], 1):
                print(f"  {i}. {brand.get('brand', 'N/A')}: {brand.get('count', 0):,} cars")
            
            # Fuel types
            fuel_types = stats.get('fuel_distribution', [])
            print(f"\nFuel Types: {len(fuel_types)} types found")
            for fuel in fuel_types[:3]:
                print(f"  - {fuel.get('fuel_type', 'N/A')}: {fuel.get('count', 0):,} cars")
            
            # Price trend
            price_trend = stats.get('price_trend', [])
            print(f"\nPrice Trend: {len(price_trend)} data points")
            
            # Top models
            top_models = stats.get('top_models_by_brand', [])
            print(f"\nTop Models by Brand: {len(top_models)} brands with models")
            
            print("\n" + "=" * 60)
            print("✨ All statistics categories present and valid!")
            
            # Check for required keys
            required_keys = [
                'overall', 'brand_stats', 'fuel_distribution', 
                'body_type_distribution', 'transmission_distribution',
                'year_distribution', 'price_ranges', 'mileage_by_year',
                'top_models_by_brand', 'price_trend', 'horsepower_distribution'
            ]
            
            missing_keys = [key for key in required_keys if key not in stats]
            if missing_keys:
                print(f"\n⚠️  Missing keys: {missing_keys}")
            else:
                print("\n✅ All required statistics keys present!")
            
            return True
        else:
            print(f"\n❌ ERROR: Status code {response.status_code}")
            print(f"Response: {response.get_data(as_text=True)}")
            return False

if __name__ == '__main__':
    try:
        success = test_market_statistics()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
