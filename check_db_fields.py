import psycopg2

DB_PARAMS = {
    'dbname': 'car_prediction',
    'user': 'bpr_user',
    'password': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

conn = psycopg2.connect(**DB_PARAMS)
cur = conn.cursor()

cur.execute("""
    SELECT fuel_consumption, co2_emission, euro_norm, periodic_tax, 
           tank_capacity, gear_count, cylinders, torque_nm, engine_size, 
           first_registration, category, load_capacity, airbags, location,
           width, length, height, energy_consumption, home_charging_ac,
           fast_charging_dc, charging_time_dc
    FROM cars 
    WHERE external_id = '6093980'
""")

row = cur.fetchone()

print('Current DB values for car 6093980:')
print('=' * 60)

cols = [
    'fuel_consumption', 'co2_emission', 'euro_norm', 'periodic_tax',
    'tank_capacity', 'gear_count', 'cylinders', 'torque_nm', 'engine_size',
    'first_registration', 'category', 'load_capacity', 'airbags', 'location',
    'width', 'length', 'height', 'energy_consumption', 'home_charging_ac',
    'fast_charging_dc', 'charging_time_dc'
]

for i, col in enumerate(cols):
    print(f'{col:25s}: {row[i]}')

cur.close()
conn.close()
