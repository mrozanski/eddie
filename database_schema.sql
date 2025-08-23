-- Guitar Registry Database Schema
-- This script creates the necessary tables for the guitar registry database integration

-- Drop tables if they exist (for development purposes)
DROP TABLE IF EXISTS guitars CASCADE;
DROP TABLE IF EXISTS manufacturers CASCADE;

-- Create manufacturers table for reference
CREATE TABLE manufacturers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    country VARCHAR(100),
    founded_year INTEGER,
    website VARCHAR(500),
    status VARCHAR(50) DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create guitars table
CREATE TABLE guitars (
    id SERIAL PRIMARY KEY,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    year INTEGER,
    product_line VARCHAR(255),
    production_type VARCHAR(50) DEFAULT 'mass',
    production_start_date DATE,
    production_end_date DATE,
    estimated_production_quantity INTEGER,
    msrp_original DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    
    -- Specifications
    body_wood VARCHAR(100),
    neck_wood VARCHAR(100),
    fingerboard_wood VARCHAR(100),
    scale_length_inches DECIMAL(4,2),
    num_frets INTEGER,
    nut_width_inches DECIMAL(3,2),
    neck_profile VARCHAR(100),
    bridge_type VARCHAR(100),
    pickup_configuration VARCHAR(50),
    pickup_brand VARCHAR(100),
    pickup_model VARCHAR(200),
    electronics_description TEXT,
    hardware_finish VARCHAR(100),
    body_finish VARCHAR(200),
    weight_lbs DECIMAL(4,2),
    case_included BOOLEAN,
    case_type VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT guitars_year_check CHECK (year >= 1900 AND year <= 2030),
    CONSTRAINT guitars_scale_length_check CHECK (scale_length_inches >= 20 AND scale_length_inches <= 30),
    CONSTRAINT guitars_num_frets_check CHECK (num_frets >= 12 AND num_frets <= 36),
    CONSTRAINT guitars_nut_width_check CHECK (nut_width_inches >= 1.0 AND nut_width_inches <= 2.5),
    CONSTRAINT guitars_weight_check CHECK (weight_lbs >= 1 AND weight_lbs <= 20)
);

-- Create indexes for better performance
CREATE INDEX idx_guitars_manufacturer ON guitars(manufacturer);
CREATE INDEX idx_guitars_model ON guitars(model);
CREATE INDEX idx_guitars_year ON guitars(year);
CREATE INDEX idx_guitars_manufacturer_model_year ON guitars(manufacturer, model, year);
CREATE INDEX idx_manufacturers_name ON manufacturers(name);

-- Insert some sample manufacturers
INSERT INTO manufacturers (name, country, founded_year, website, status) VALUES
    ('Gibson', 'USA', 1902, 'https://www.gibson.com', 'active'),
    ('Fender', 'USA', 1946, 'https://www.fender.com', 'active'),
    ('PRS', 'USA', 1985, 'https://www.prsguitars.com', 'active'),
    ('Martin', 'USA', 1833, 'https://www.martinguitar.com', 'active'),
    ('Taylor', 'USA', 1974, 'https://www.taylorguitars.com', 'active'),
    ('Ibanez', 'Japan', 1957, 'https://www.ibanez.com', 'active'),
    ('ESP', 'Japan', 1975, 'https://www.espguitars.com', 'active'),
    ('Gretsch', 'USA', 1883, 'https://www.gretschguitars.com', 'active'),
    ('Rickenbacker', 'USA', 1931, 'https://www.rickenbacker.com', 'active'),
    ('Epiphone', 'USA', 1873, 'https://www.epiphone.com', 'active');

-- Insert some sample guitars for testing
INSERT INTO guitars (manufacturer, model, year, product_line, description, body_wood, neck_wood, fingerboard_wood, scale_length_inches, num_frets, pickup_configuration) VALUES
    ('Gibson', 'Les Paul Standard', 2020, 'Les Paul', 'Classic Gibson Les Paul with modern appointments', 'Mahogany', 'Mahogany', 'Rosewood', 24.75, 22, 'HH'),
    ('Gibson', 'SG Standard', 2021, 'SG', 'Iconic double-cutaway solid body electric guitar', 'Mahogany', 'Mahogany', 'Rosewood', 24.75, 22, 'HH'),
    ('Fender', 'Stratocaster', 2020, 'Stratocaster', 'Classic American Stratocaster', 'Alder', 'Maple', 'Maple', 25.5, 22, 'SSS'),
    ('Fender', 'Telecaster', 2021, 'Telecaster', 'Original electric guitar design', 'Alder', 'Maple', 'Maple', 25.5, 22, 'SS'),
    ('PRS', 'Custom 24', 2020, 'Core', 'PRS flagship model with 24 frets', 'Mahogany', 'Mahogany', 'Rosewood', 25.0, 24, 'HH'),
    ('Martin', 'D-28', 2020, 'Standard Series', 'Legendary dreadnought acoustic guitar', 'East Indian Rosewood', 'Sitka Spruce', 'East Indian Rosewood', 25.4, 20, NULL),
    ('Taylor', '814ce', 2021, '800 Series', 'Grand Auditorium with Expression System 2', 'East Indian Rosewood', 'Sitka Spruce', 'Ebony', 25.5, 20, NULL),
    ('Ibanez', 'RG550', 2020, 'RG', 'High-performance electric guitar', 'Basswood', 'Maple', 'Bound Rosewood', 25.5, 24, 'HSH'),
    ('ESP', 'Eclipse', 2021, 'Original Series', 'Single-cutaway electric guitar', 'Mahogany', 'Mahogany', 'Ebony', 24.75, 22, 'HH'),
    ('Gretsch', 'White Falcon', 2020, 'Professional Collection', 'Iconic hollow body electric guitar', 'Maple', 'Maple', 'Ebony', 24.6, 22, 'HH');

-- Add some variations of manufacturer names for testing normalization
INSERT INTO guitars (manufacturer, model, year, product_line, description) VALUES
    ('Gibson Corporation', 'Les Paul Studio', 2019, 'Les Paul', 'Affordable Les Paul variant'),
    ('Gibson Corp', 'Flying V', 2020, 'Flying V', 'Iconic V-shaped electric guitar'),
    ('Fender Musical Instruments', 'Jazzmaster', 2021, 'Offset', 'Offset electric guitar'),
    ('Fender Corp', 'Mustang', 2020, 'Offset', 'Short-scale electric guitar'),
    ('PRS Guitars', 'SE Custom 24', 2020, 'SE', 'Import version of Custom 24'),
    ('Paul Reed Smith', 'McCarty 594', 2021, 'Core', 'Vintage-inspired electric guitar');

COMMENT ON TABLE guitars IS 'Main table storing guitar information for the registry';
COMMENT ON TABLE manufacturers IS 'Reference table for guitar manufacturers';
COMMENT ON COLUMN guitars.manufacturer IS 'Manufacturer name (may contain variations that need normalization)';
COMMENT ON COLUMN guitars.pickup_configuration IS 'Pickup layout: H=Humbucker, S=Single-coil (e.g., HH, SSS, HSS)';