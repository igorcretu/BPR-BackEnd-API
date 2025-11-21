-- init.sql - BPR Car Prediction Platform
-- English columns compatible with bilbasen.dk scraped data

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE fuel_type_enum AS ENUM ('Petrol', 'Diesel', 'Electric', 'Hybrid', 'Plugin-Hybrid');
CREATE TYPE transmission_enum AS ENUM ('Manual', 'Automatic', 'Semi-Automatic');
CREATE TYPE body_type_enum AS ENUM ('Sedan', 'Hatchback', 'SUV', 'Coupe', 'Wagon', 'Van', 'Convertible', 'Pickup', 'MPV');
CREATE TYPE drive_type_enum AS ENUM ('FWD', 'RWD', 'AWD');

-- Main cars table
CREATE TABLE IF NOT EXISTS cars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    variant VARCHAR(200),
    title VARCHAR(300),
    description TEXT,
    price DECIMAL(12,2) NOT NULL CHECK (price >= 0),
    new_price DECIMAL(12,2),
    model_year INTEGER CHECK (model_year >= 1900 AND model_year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1),
    year INTEGER CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1),
    first_registration VARCHAR(20),
    production_date VARCHAR(20),
    mileage INTEGER CHECK (mileage >= 0),
    fuel_type VARCHAR(50),
    transmission VARCHAR(50),
    gear_count INTEGER,
    cylinders INTEGER,
    horsepower INTEGER,
    torque_nm INTEGER,
    acceleration DECIMAL(4,1),
    top_speed INTEGER,
    range_km INTEGER,
    battery_capacity DECIMAL(5,1),
    energy_consumption INTEGER,
    home_charging_ac VARCHAR(50),
    fast_charging_dc VARCHAR(50),
    charging_time_dc VARCHAR(50),
    fuel_consumption VARCHAR(50),
    co2_emission VARCHAR(50),
    euro_norm VARCHAR(10),
    tank_capacity INTEGER,
    body_type VARCHAR(50),
    weight INTEGER,
    width INTEGER,
    length INTEGER,
    height INTEGER,
    trunk_size INTEGER,
    load_capacity INTEGER,
    towing_capacity INTEGER,
    max_towing_weight INTEGER,
    drive_type VARCHAR(50),
    abs_brakes BOOLEAN DEFAULT true,
    esp BOOLEAN DEFAULT true,
    airbags INTEGER,
    doors INTEGER CHECK (doors >= 2 AND doors <= 5),
    seats INTEGER CHECK (seats >= 2 AND seats <= 9),
    color VARCHAR(100),
    category VARCHAR(50),
    equipment TEXT,
    periodic_tax VARCHAR(50),
    engine_size DECIMAL(3,1),
    source_url TEXT,
    location VARCHAR(200),
    dealer_name VARCHAR(300),
    listing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    car_id UUID REFERENCES cars(id) ON DELETE SET NULL,
    predicted_price DECIMAL(12,2) NOT NULL,
    actual_price DECIMAL(12,2),
    prediction_accuracy DECIMAL(5,2),
    confidence DECIMAL(5,2),
    price_range_min DECIMAL(12,2),
    price_range_max DECIMAL(12,2),
    model_version VARCHAR(50),
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(100) NOT NULL,
    cars_scraped INTEGER DEFAULT 0,
    cars_updated INTEGER DEFAULT 0,
    cars_new INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    fuel_type VARCHAR(50),
    avg_price DECIMAL(12,2),
    min_price DECIMAL(12,2),
    max_price DECIMAL(12,2),
    avg_mileage INTEGER,
    total_listings INTEGER,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 100 CHECK (priority >= 0),
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_error_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_cars_brand ON cars(brand);
CREATE INDEX idx_cars_model ON cars(model);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_price ON cars(price);
CREATE INDEX idx_cars_fuel_type ON cars(fuel_type);
CREATE INDEX idx_cars_mileage ON cars(mileage);
CREATE INDEX idx_cars_listing_date ON cars(listing_date);
CREATE INDEX idx_cars_body_type ON cars(body_type);
CREATE INDEX idx_predictions_car_id ON price_predictions(car_id);
CREATE INDEX idx_predictions_created_at ON price_predictions(created_at);
CREATE INDEX idx_prediction_jobs_status ON prediction_jobs(status);
CREATE INDEX idx_prediction_jobs_priority ON prediction_jobs(priority);

-- Sample data
INSERT INTO cars (brand, model, variant, title, price, new_price, year, mileage, fuel_type, transmission, horsepower, torque_nm, body_type, weight, trunk_size, drive_type, doors, color, location, dealer_name) VALUES
('Tesla', 'Model 3', 'Long Range', 'Tesla Model 3 Long Range', 329000, 420000, 2022, 38000, 'Electric', 'Automatic', 283, 450, 'Sedan', 1847, 425, 'AWD', 4, 'White', 'Copenhagen', 'Tesla Denmark'),
('VW', 'ID.4', 'Pro Performance', 'VW ID.4 Pro Performance', 385000, 450000, 2023, 22000, 'Electric', 'Automatic', 204, 310, 'SUV', 2124, 543, 'RWD', 5, 'Blue', 'Aarhus', 'VW Center'),
('Toyota', 'Corolla', '1.8 Hybrid', 'Toyota Corolla Hybrid', 215000, 280000, 2021, 45000, 'Hybrid', 'Automatic', 122, 142, 'Sedan', 1380, 361, 'FWD', 4, 'Silver', 'Copenhagen', 'Toyota Danmark'),
('BMW', '320i', 'M Sport', 'BMW 320i M Sport', 389000, 520000, 2021, 52000, 'Petrol', 'Automatic', 184, 300, 'Sedan', 1540, 480, 'RWD', 4, 'Black', 'Copenhagen', 'BMW Copenhagen'),
('Audi', 'A4', '2.0 TFSI', 'Audi A4 TFSI', 349000, 480000, 2020, 62000, 'Petrol', 'Automatic', 190, 320, 'Sedan', 1540, 460, 'FWD', 4, 'White', 'Aarhus', 'Audi Aarhus'),
('Volkswagen', 'Golf', '1.5 TSI', 'VW Golf TSI', 259000, 320000, 2022, 25000, 'Petrol', 'Manual', 150, 250, 'Hatchback', 1355, 380, 'FWD', 5, 'Grey', 'Aalborg', 'VW Aalborg'),
('Skoda', 'Octavia', '2.0 TDI', 'Skoda Octavia TDI', 229000, 310000, 2021, 68000, 'Diesel', 'Automatic', 150, 360, 'Wagon', 1450, 640, 'FWD', 5, 'Blue', 'Copenhagen', 'Skoda Center'),
('Mercedes-Benz', 'C220d', 'AMG Line', 'Mercedes C220d AMG', 449000, 620000, 2022, 35000, 'Diesel', 'Automatic', 200, 440, 'Sedan', 1635, 455, 'RWD', 4, 'Silver', 'Copenhagen', 'Mercedes Copenhagen'),
('Hyundai', 'Tucson', 'Hybrid Premium', 'Hyundai Tucson Hybrid', 389000, 450000, 2023, 18000, 'Hybrid', 'Automatic', 230, 350, 'SUV', 1715, 546, 'AWD', 5, 'Green', 'Aarhus', 'Hyundai Aarhus'),
('Nissan', 'Qashqai', 'N-Style', 'Nissan Qashqai N-Style', 289000, 350000, 2022, 32000, 'Petrol', 'Automatic', 158, 270, 'SUV', 1450, 436, 'FWD', 5, 'Grey', 'Odense', 'Nissan Odense'),
('Volvo', 'XC60', 'T6 Recharge', 'Volvo XC60 Recharge', 549000, 720000, 2022, 28000, 'Plugin-Hybrid', 'Automatic', 350, 590, 'SUV', 2175, 468, 'AWD', 5, 'Black', 'Copenhagen', 'Volvo Copenhagen'),
('Ford', 'Kuga', 'PHEV ST-Line', 'Ford Kuga PHEV', 349000, 420000, 2022, 28000, 'Plugin-Hybrid', 'Automatic', 225, 200, 'SUV', 1844, 405, 'FWD', 5, 'Black', 'Esbjerg', 'Ford Esbjerg'),
('Polestar', '2', 'Long Range', 'Polestar 2 Long Range', 289000, 390000, 2023, 25000, 'Electric', 'Automatic', 231, 330, 'Sedan', 2069, 405, 'FWD', 4, 'Grey', 'Odense', 'Polestar Odense'),
('Dacia', 'Sandero', 'Essential', 'Dacia Sandero Essential', 129000, 150000, 2022, 32000, 'Petrol', 'Manual', 90, 160, 'Hatchback', 1100, 328, 'FWD', 5, 'Red', 'Odense', 'Dacia Odense'),
('Kia', 'Picanto', 'Comfort', 'Kia Picanto Comfort', 109000, 135000, 2021, 42000, 'Petrol', 'Manual', 67, 96, 'Hatchback', 940, 255, 'FWD', 5, 'White', 'Aalborg', 'Kia Nord');

-- Sample predictions
INSERT INTO price_predictions (car_id, predicted_price, actual_price, prediction_accuracy, confidence, price_range_min, price_range_max, model_version) 
SELECT id, price * (0.95 + RANDOM() * 0.1), price, 95 + RANDOM() * 4, 88 + RANDOM() * 7, price * 0.9, price * 1.1, 'v1.0.0-xgboost'
FROM cars LIMIT 10;

-- Sample scraping logs
INSERT INTO scraping_logs (source_name, cars_scraped, cars_new, cars_updated, success, started_at, completed_at) VALUES
('bilbasen.dk', 250, 45, 180, true, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '20 minutes'),
('bilbasen.dk', 312, 62, 220, true, NOW() - INTERVAL '12 hours', NOW() - INTERVAL '12 hours' + INTERVAL '25 minutes');

-- Market statistics
INSERT INTO market_statistics (brand, model, year, fuel_type, avg_price, min_price, max_price, avg_mileage, total_listings)
SELECT brand, model, year, fuel_type, AVG(price), MIN(price), MAX(price), AVG(mileage)::INTEGER, COUNT(*)
FROM cars GROUP BY brand, model, year, fuel_type;

-- View
CREATE OR REPLACE VIEW car_listings_with_predictions AS
SELECT c.*, p.predicted_price, p.prediction_accuracy, p.confidence,
    CASE WHEN p.predicted_price IS NOT NULL THEN ((c.price - p.predicted_price) / p.predicted_price * 100)::DECIMAL(5,2) ELSE NULL END as price_difference_percent
FROM cars c
LEFT JOIN LATERAL (SELECT predicted_price, prediction_accuracy, confidence FROM price_predictions WHERE car_id = c.id ORDER BY created_at DESC LIMIT 1) p ON true;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END; $$ language 'plpgsql';

CREATE TRIGGER update_cars_updated_at BEFORE UPDATE ON cars FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DO $$ BEGIN RAISE NOTICE 'Database initialized with % cars', (SELECT COUNT(*) FROM cars); END $$;