-- ============================================================
-- AI SERVICE HUB DATABASE
-- ============================================================

CREATE DATABASE IF NOT EXISTS ai_service_hub;

USE ai_service_hub;

-- ============================================================
-- USERS
-- ============================================================

DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS services;
DROP TABLE IF EXISTS users;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    phone VARCHAR(20),

    password_hash VARCHAR(255) NOT NULL,

    role ENUM(
        'customer',
        'worker',
        'admin'
    ) NOT NULL DEFAULT 'customer',

    city VARCHAR(100),

    location VARCHAR(255),

    latitude DECIMAL(10,7),

    longitude DECIMAL(10,7),

    availability ENUM(
        'Available',
        'Busy',
        'Offline'
    ) NOT NULL DEFAULT 'Available',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- SERVICES
-- Worker adds services/work
-- ============================================================

CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,

    worker_id INT NOT NULL,

    name VARCHAR(150) NOT NULL,

    description TEXT,

    category VARCHAR(100),

    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,

    is_active TINYINT(1) NOT NULL DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (worker_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- BOOKINGS
-- ============================================================

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    customer_id INT NOT NULL,

    worker_id INT NOT NULL,

    service_id INT NOT NULL,

    booking_date DATE NOT NULL,

    booking_time TIME NOT NULL,

    customer_phone VARCHAR(20),

    customer_location VARCHAR(255),

    customer_latitude DECIMAL(10,7),

    customer_longitude DECIMAL(10,7),

    worker_latitude DECIMAL(10,7),

    worker_longitude DECIMAL(10,7),

    status ENUM(
        'Pending',
        'Approved',
        'Rejected',
        'Completed',
        'Cancelled'
    ) NOT NULL DEFAULT 'Pending',

    payment_status ENUM(
        'Pending',
        'Created',
        'Paid',
        'Failed'
    ) NOT NULL DEFAULT 'Pending',

    razorpay_order_id VARCHAR(100),

    razorpay_payment_id VARCHAR(100),

    completed_at DATETIME NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (worker_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (service_id)
        REFERENCES services(id)
        ON DELETE CASCADE
);


-- ============================================================
-- MESSAGES
-- Customer <-> Worker
-- ============================================================

CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,

    booking_id INT NOT NULL,

    sender_id INT NOT NULL,

    receiver_id INT NOT NULL,

    message TEXT NOT NULL,

    is_read TINYINT(1) NOT NULL DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
        ON DELETE CASCADE,

    FOREIGN KEY (sender_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (receiver_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- RATINGS
-- Customer rates worker
-- ============================================================

CREATE TABLE ratings (
    id INT AUTO_INCREMENT PRIMARY KEY,

    booking_id INT NOT NULL,

    customer_id INT NOT NULL,

    worker_id INT NOT NULL,

    rating INT NOT NULL,

    review TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
        ON DELETE CASCADE,

    FOREIGN KEY (customer_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (worker_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT rating_range
        CHECK (rating >= 1 AND rating <= 5),

    UNIQUE KEY unique_booking_rating (booking_id)
);


-- ============================================================
-- PAYMENTS
-- Razorpay
-- ============================================================

CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,

    booking_id INT NOT NULL,

    customer_id INT NOT NULL,

    razorpay_order_id VARCHAR(100),

    razorpay_payment_id VARCHAR(100),

    razorpay_signature VARCHAR(255),

    amount DECIMAL(10,2) NOT NULL,

    currency VARCHAR(10) NOT NULL DEFAULT 'INR',

    status ENUM(
        'created',
        'paid',
        'failed'
    ) NOT NULL DEFAULT 'created',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    paid_at DATETIME NULL,

    FOREIGN KEY (booking_id)
        REFERENCES bookings(id)
        ON DELETE CASCADE,

    FOREIGN KEY (customer_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    title VARCHAR(150) NOT NULL,

    message TEXT NOT NULL,

    notification_type VARCHAR(50) DEFAULT 'general',

    is_read TINYINT(1) NOT NULL DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ============================================================
-- SAMPLE ADMIN
-- ============================================================
-- Password will be created properly from Flask.
-- Do not manually insert a plain password here.


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_services_worker
ON services(worker_id);

CREATE INDEX idx_services_category
ON services(category);

CREATE INDEX idx_bookings_customer
ON bookings(customer_id);

CREATE INDEX idx_bookings_worker
ON bookings(worker_id);

CREATE INDEX idx_bookings_status
ON bookings(status);

CREATE INDEX idx_messages_booking
ON messages(booking_id);

CREATE INDEX idx_notifications_user
ON notifications(user_id);

CREATE INDEX idx_ratings_worker
ON ratings(worker_id);


-- ============================================================
-- CHECK DATABASE
-- ============================================================

SHOW TABLES;