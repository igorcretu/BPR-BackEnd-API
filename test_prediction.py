import psycopg2
import requests
import json

# Database connection
conn = psycopg2.connect(
    dbname="car_prediction",
    user="bpr_user",
    password="postgres",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

# Fetch the car
car_id = "1d8c61c2-48b8-4e37-835c-abcb6a066ac1"
cur.execute("""
    SELECT id, brand, model, year, mileage, fuel_type, transmission, body_type, 
           horsepower, engine_size, doors, color, drive_type, variant, price
    FROM cars 
    WHERE id = %s
""", (car_id,))

car = cur.fetchone()

if not car:
    print(f"❌ Car with ID {car_id} not found")
    cur.close()
    conn.close()
    exit(1)

# Parse car data
(id, brand, model, year, mileage, fuel_type, transmission, body_type, 
 horsepower, engine_size, doors, color, drive_type, variant, price) = car

print("=" * 60)
print(f"Car Details:")
print("=" * 60)
print(f"ID:           {id}")
print(f"Brand:        {brand}")
print(f"Model:        {model}")
print(f"Variant:      {variant}")
print(f"Year:         {year}")
print(f"Mileage:      {mileage} km")
print(f"Fuel Type:    {fuel_type}")
print(f"Transmission: {transmission}")
print(f"Body Type:    {body_type}")
print(f"Horsepower:   {horsepower}")
print(f"Engine Size:  {engine_size}")
print(f"Doors:        {doors}")
print(f"Color:        {color}")
print(f"Drive Type:   {drive_type}")
print(f"Actual Price: {price:,.0f} DKK")
print("=" * 60)

# Prepare prediction payload
payload = {
    "brand": brand,
    "model": model,
    "year": int(year) if year else 2020,
    "mileage": int(mileage) if mileage else 0,  # Use 0 for new cars or null mileage
    "fuel_type": fuel_type,
    "transmission": transmission,
    "body_type": body_type,
}

# Add optional fields if they exist
if horsepower:
    payload["horsepower"] = int(horsepower)
if engine_size:
    payload["engine_size"] = float(engine_size)
if doors:
    payload["doors"] = int(doors)
if color:
    payload["color"] = color
if drive_type:
    payload["drive_type"] = drive_type

print("\nSending prediction request...")
print("Payload:", json.dumps(payload, indent=2))
print("=" * 60)

# Make prediction request
try:
    response = requests.post("https://test.bachelorproject26.site/api/predict", json=payload, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        predicted_price = result.get("predicted_price")
        confidence = result.get("confidence")
        price_range = result.get("price_range", {})
        
        print("\n✅ Prediction Successful!")
        print("=" * 60)
        print(f"Predicted Price:  {predicted_price:,.0f} DKK")
        print(f"Confidence:       {confidence:.1f}%")
        print(f"Price Range:      {price_range.get('min', 0):,.0f} - {price_range.get('max', 0):,.0f} DKK")
        print(f"Actual Price:     {price:,.0f} DKK")
        
        # Calculate difference
        diff = predicted_price - float(price)
        diff_pct = (diff / float(price) * 100) if price else 0
        
        print("=" * 60)
        print(f"Difference:       {diff:+,.0f} DKK ({diff_pct:+.1f}%)")
        
        if abs(diff_pct) < 10:
            print("🎯 Excellent prediction! Within 10% of actual price")
        elif abs(diff_pct) < 20:
            print("👍 Good prediction! Within 20% of actual price")
        else:
            print("⚠️  Prediction differs significantly from actual price")
        
    elif response.status_code == 400:
        print(f"\n❌ Bad Request (400)")
        print("Response:", response.json())
        print("\nThis likely means validation failed. Check the payload values.")
    else:
        print(f"\n❌ Request failed with status {response.status_code}")
        print("Response:", response.text)
        
except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to API server")
    print("Make sure the server is running on https://test.bachelorproject26.site")
except Exception as e:
    print(f"\n❌ Error: {e}")

cur.close()
conn.close()
