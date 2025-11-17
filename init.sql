-- init.sql
-- Database initialization script for BPR Car Prediction Platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE fuel_type AS ENUM ('Petrol', 'Diesel', 'Electric', 'Hybrid', 'Plugin-Hybrid');
CREATE TYPE transmission_type AS ENUM ('Manual', 'Automatic', 'Semi-Automatic');
CREATE TYPE body_type AS ENUM ('Sedan', 'Hatchback', 'SUV', 'Coupe', 'Wagon', 'Van', 'Convertible', 'Pickup');

-- Cars table
CREATE TABLE IF NOT EXISTS cars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1),
    mileage INTEGER NOT NULL CHECK (mileage >= 0),
    fuel_type fuel_type NOT NULL,
    transmission transmission_type NOT NULL,
    body_type body_type NOT NULL,
    engine_size DECIMAL(3,1) CHECK (engine_size > 0),
    horsepower INTEGER CHECK (horsepower > 0),
    doors INTEGER CHECK (doors >= 2 AND doors <= 5),
    seats INTEGER CHECK (seats >= 2 AND seats <= 9),
    color VARCHAR(50),
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    listing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT,
    location VARCHAR(100),
    dealer_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price predictions table
CREATE TABLE IF NOT EXISTS price_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    car_id UUID REFERENCES cars(id) ON DELETE SET NULL,
    predicted_price DECIMAL(10,2) NOT NULL,
    actual_price DECIMAL(10,2),
    prediction_accuracy DECIMAL(5,2),
    model_version VARCHAR(50),
    features JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scraping logs table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(100) NOT NULL,
    cars_scraped INTEGER DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Market statistics table
CREATE TABLE IF NOT EXISTS market_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    avg_price DECIMAL(10,2),
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    avg_mileage INTEGER,
    total_listings INTEGER,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX idx_cars_brand ON cars(brand);
CREATE INDEX idx_cars_model ON cars(model);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_price ON cars(price);
CREATE INDEX idx_cars_fuel_type ON cars(fuel_type);
CREATE INDEX idx_cars_listing_date ON cars(listing_date);
CREATE INDEX idx_predictions_car_id ON price_predictions(car_id);
CREATE INDEX idx_predictions_created_at ON price_predictions(created_at);

-- Insert sample data for testing (30 cars with variety)
INSERT INTO cars (brand, model, year, mileage, fuel_type, transmission, body_type, engine_size, horsepower, doors, seats, color, price, location, dealer_name, source_url) VALUES
-- Toyota vehicles
('Toyota', 'Corolla', 2020, 45000, 'Petrol', 'Manual', 'Sedan', 1.8, 132, 4, 5, 'Silver', 189000, 'Copenhagen', 'AutoDanmark', 'https://example.com/car1'),
('Toyota', 'Corolla', 2021, 32000, 'Hybrid', 'Automatic', 'Sedan', 1.8, 122, 4, 5, 'White', 215000, 'Aarhus', 'BilPartner', 'https://example.com/car2'),
('Toyota', 'RAV4', 2019, 67000, 'Hybrid', 'Automatic', 'SUV', 2.5, 218, 5, 5, 'Black', 289000, 'Odense', 'DK Motors', 'https://example.com/car3'),
('Toyota', 'Yaris', 2022, 15000, 'Petrol', 'Manual', 'Hatchback', 1.5, 125, 5, 5, 'Red', 165000, 'Aalborg', 'Nord Biler', 'https://example.com/car4'),

-- Volkswagen vehicles
('Volkswagen', 'Golf', 2020, 52000, 'Diesel', 'Manual', 'Hatchback', 2.0, 150, 5, 5, 'Blue', 195000, 'Copenhagen', 'VW Center', 'https://example.com/car5'),
('Volkswagen', 'Passat', 2019, 78000, 'Diesel', 'Automatic', 'Sedan', 2.0, 190, 4, 5, 'Grey', 245000, 'Aarhus', 'AutoDanmark', 'https://example.com/car6'),
('Volkswagen', 'Tiguan', 2021, 35000, 'Petrol', 'Automatic', 'SUV', 2.0, 190, 5, 5, 'White', 329000, 'Esbjerg', 'Vest Biler', 'https://example.com/car7'),
('Volkswagen', 'ID.4', 2022, 18000, 'Electric', 'Automatic', 'SUV', 0.0, 204, 5, 5, 'Silver', 385000, 'Copenhagen', 'EV Denmark', 'https://example.com/car8'),

-- BMW vehicles
('BMW', '320d', 2020, 61000, 'Diesel', 'Automatic', 'Sedan', 2.0, 190, 4, 5, 'Black', 295000, 'Copenhagen', 'Premium Motors', 'https://example.com/car9'),
('BMW', 'X3', 2019, 72000, 'Diesel', 'Automatic', 'SUV', 2.0, 190, 5, 5, 'White', 349000, 'Aarhus', 'Luxury Cars DK', 'https://example.com/car10'),
('BMW', '530e', 2021, 42000, 'Plugin-Hybrid', 'Automatic', 'Sedan', 2.0, 252, 4, 5, 'Blue', 425000, 'Odense', 'BMW Center', 'https://example.com/car11'),

-- Tesla vehicles
('Tesla', 'Model 3', 2021, 38000, 'Electric', 'Automatic', 'Sedan', 0.0, 283, 4, 5, 'White', 329000, 'Copenhagen', 'Tesla Denmark', 'https://example.com/car12'),
('Tesla', 'Model Y', 2022, 22000, 'Electric', 'Automatic', 'SUV', 0.0, 346, 5, 5, 'Black', 449000, 'Aarhus', 'Tesla Center', 'https://example.com/car13'),

-- Peugeot vehicles
('Peugeot', '208', 2021, 28000, 'Petrol', 'Automatic', 'Hatchback', 1.2, 100, 5, 5, 'Red', 145000, 'Aalborg', 'Peugeot Nord', 'https://example.com/car14'),
('Peugeot', '3008', 2020, 55000, 'Diesel', 'Automatic', 'SUV', 2.0, 177, 5, 5, 'Grey', 259000, 'Esbjerg', 'Auto West', 'https://example.com/car15'),

-- Skoda vehicles
('Skoda', 'Octavia', 2020, 48000, 'Diesel', 'Manual', 'Wagon', 2.0, 150, 5, 5, 'Silver', 189000, 'Copenhagen', 'Skoda DK', 'https://example.com/car16'),
('Skoda', 'Superb', 2021, 36000, 'Petrol', 'Automatic', 'Sedan', 2.0, 190, 4, 5, 'Black', 289000, 'Aarhus', 'Premium Auto', 'https://example.com/car17'),
('Skoda', 'Kodiaq', 2020, 62000, 'Diesel', 'Automatic', 'SUV', 2.0, 190, 5, 7, 'White', 319000, 'Odense', 'Family Cars', 'https://example.com/car18'),

-- Mercedes-Benz vehicles
('Mercedes-Benz', 'C220d', 2020, 58000, 'Diesel', 'Automatic', 'Sedan', 2.0, 194, 4, 5, 'Black', 345000, 'Copenhagen', 'MB Premium', 'https://example.com/car19'),
('Mercedes-Benz', 'GLC', 2021, 41000, 'Petrol', 'Automatic', 'SUV', 2.0, 258, 5, 5, 'Silver', 479000, 'Aarhus', 'Luxury Motors', 'https://example.com/car20'),

-- Audi vehicles
('Audi', 'A4', 2020, 53000, 'Diesel', 'Automatic', 'Sedan', 2.0, 190, 4, 5, 'Grey', 299000, 'Copenhagen', 'Audi Center', 'https://example.com/car21'),
('Audi', 'Q5', 2021, 38000, 'Petrol', 'Automatic', 'SUV', 2.0, 252, 5, 5, 'White', 459000, 'Aarhus', 'Premium SUV', 'https://example.com/car22'),
('Audi', 'e-tron', 2022, 25000, 'Electric', 'Automatic', 'SUV', 0.0, 408, 5, 5, 'Black', 549000, 'Copenhagen', 'Audi Electric', 'https://example.com/car23'),

-- Nissan vehicles
('Nissan', 'Leaf', 2020, 44000, 'Electric', 'Automatic', 'Hatchback', 0.0, 150, 5, 5, 'White', 159000, 'Aalborg', 'EV Nord', 'https://example.com/car24'),
('Nissan', 'Qashqai', 2021, 36000, 'Petrol', 'Manual', 'SUV', 1.3, 140, 5, 5, 'Red', 219000, 'Odense', 'Nissan DK', 'https://example.com/car25'),

-- Ford vehicles
('Ford', 'Focus', 2019, 68000, 'Petrol', 'Manual', 'Hatchback', 1.5, 150, 5, 5, 'Blue', 139000, 'Esbjerg', 'Ford West', 'https://example.com/car26'),
('Ford', 'Kuga', 2020, 52000, 'Hybrid', 'Automatic', 'SUV', 2.5, 225, 5, 5, 'Grey', 249000, 'Aarhus', 'Ford Center', 'https://example.com/car27'),

-- Hyundai vehicles
('Hyundai', 'i30', 2021, 32000, 'Petrol', 'Manual', 'Hatchback', 1.4, 140, 5, 5, 'Silver', 169000, 'Copenhagen', 'Hyundai DK', 'https://example.com/car28'),
('Hyundai', 'Tucson', 2020, 48000, 'Diesel', 'Automatic', 'SUV', 2.0, 185, 5, 5, 'Black', 249000, 'Aalborg', 'Auto Nord', 'https://example.com/car29'),
('Hyundai', 'Ioniq 5', 2022, 18000, 'Electric', 'Automatic', 'SUV', 0.0, 305, 5, 5, 'White', 399000, 'Copenhagen', 'Hyundai Electric', 'https://example.com/car30');

-- Insert some sample predictions
INSERT INTO price_predictions (car_id, predicted_price, actual_price, prediction_accuracy, model_version, features) 
SELECT 
    id,
    price * (0.95 + (RANDOM() * 0.1)), -- Predicted price within ±5% of actual
    price,
    95.0 + (RANDOM() * 4), -- Accuracy between 95-99%
    'v0.1.0-mock',
    jsonb_build_object(
        'brand', brand,
        'model', model,
        'year', year,
        'mileage', mileage,
        'fuel_type', fuel_type::text
    )
FROM cars
LIMIT 20;

-- Insert sample scraping logs
INSERT INTO scraping_logs (source_name, cars_scraped, success, started_at, completed_at) VALUES
('bilbasen.dk', 150, true, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '15 minutes'),
('dba.dk', 89, true, NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day' + INTERVAL '12 minutes'),
('bilbasen.dk', 142, true, NOW() - INTERVAL '12 hours', NOW() - INTERVAL '12 hours' + INTERVAL '14 minutes'),
('autouncle.dk', 0, false, NOW() - INTERVAL '6 hours', NOW() - INTERVAL '6 hours' + INTERVAL '2 minutes');

-- Insert market statistics
INSERT INTO market_statistics (brand, model, year, avg_price, min_price, max_price, avg_mileage, total_listings)
SELECT 
    brand,
    model,
    year,
    AVG(price)::DECIMAL(10,2),
    MIN(price),
    MAX(price),
    AVG(mileage)::INTEGER,
    COUNT(*)
FROM cars
GROUP BY brand, model, year;

-- Create a view for easy querying of car listings with predictions
CREATE OR REPLACE VIEW car_listings_with_predictions AS
SELECT 
    c.*,
    p.predicted_price,
    p.prediction_accuracy,
    CASE 
        WHEN p.predicted_price IS NOT NULL THEN 
            ((c.price - p.predicted_price) / p.predicted_price * 100)::DECIMAL(5,2)
        ELSE NULL
    END as price_difference_percent
FROM cars c
LEFT JOIN LATERAL (
    SELECT predicted_price, prediction_accuracy
    FROM price_predictions
    WHERE car_id = c.id
    ORDER BY created_at DESC
    LIMIT 1
) p ON true;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_cars_updated_at BEFORE UPDATE ON cars
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Display summary
DO $$
DECLARE
    car_count INTEGER;
    prediction_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO car_count FROM cars;
    SELECT COUNT(*) INTO prediction_count FROM price_predictions;
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Cars inserted: %', car_count;
    RAISE NOTICE 'Predictions inserted: %', prediction_count;
    RAISE NOTICE '==============================================';
END $$;
