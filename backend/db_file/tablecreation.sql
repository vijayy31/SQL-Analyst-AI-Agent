CREATE DATABASE OLA;

USE OLA;

CREATE TABLE OLA.RATINGS(
    rating_id Int PRIMARY KEY,
    ride_id Int,
    rider_id Int,
    driver_id Int,
    rating Int,
    comment VARCHAR(1000),
    rated_at VARCHAR(1000)
);

CREATE TABLE IF NOT EXISTS OLA.PAYMENTS(
    payment_id Int PRIMARY KEY,
    ride_id Int,
    user_id Int,
    amount Float,
    payment_method VARCHAR(1000),
    payment_status VARCHAR(1000),
    transaction_id VARCHAR(1000),
    payment_time TIMESTAMP
);


CREATE TABLE IF NOT EXISTS OLA.RIDES(
    ride_id Int PRIMARY KEY,
    rider_id Int,
    driver_id Int,
    requested_at TIMESTAMP,
    pickup_time TIMESTAMP,
    dropoff_time TIMESTAMP,
    pickup_latitude DOUBLE,
    pickup_longitude DOUBLE,
    dropoff_latitude DOUBLE,
    dropoff_longitude DOUBLE,
    distance_km Float,
    fare Float,
    surge_multiplier Float,
    status VARCHAR(1000),
    cancellation_reason VARCHAR(1000)
);

CREATE TABLE IF NOT EXISTS OLA.USERS(
    user_id Int PRIMARY KEY,
    first_name VARCHAR(1000),
    last_name VARCHAR(1000),
    email VARCHAR(1000),
    phone VARCHAR(1000),
    city VARCHAR(1000),
    province VARCHAR(1000),
    user_type VARCHAR(1000),
    signup_date DATE,
    is_active BOOL
);

CREATE TABLE IF NOT EXISTS OLA.VEHICLES(
    vehicle_id Int PRIMARY KEY,
    driver_id Int,
    make VARCHAR(1000),
    model VARCHAR(1000),
    year YEAR,
    license_plate VARCHAR(1000),
    color VARCHAR(1000),
    is_active BOOL
);

CREATE INDEX idx_vehicles_driver_id
ON OLA.vehicles(driver_id);

CREATE INDEX idx_rides_rider_id
ON OLA.rides(rider_id);

CREATE INDEX idx_rides_driver_id
ON OLA.rides(driver_id);

CREATE INDEX idx_rides_requested_at
ON OLA.rides(requested_at);

CREATE INDEX idx_payments_ride_id
ON OLA.payments(ride_id);

CREATE INDEX idx_payments_user_id
ON OLA.payments(user_id);

CREATE INDEX idx_ratings_ride_id
ON OLA.ratings(ride_id);

CREATE INDEX idx_ratings_driver_id
ON OLA.ratings(driver_id);

-- SELECT
--     index_name,
--     column_name,
--     non_unique
-- FROM information_schema.statistics
-- WHERE table_schema = 'OLA';

-- EXPLAIN
-- SELECT * FROM OLA.RATINGS
-- WHERE ride_id = 13870;

-- DROP TABLE RATINGS, PAYMENTS, RIDES, USERS, VEHICLES;

-- SELECT * FROM OLA.RIDES LIMIT 10;