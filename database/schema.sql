-- StayGenius AI - MySQL schema (run in MySQL Workbench, or let backend/seed.py run it)
CREATE DATABASE IF NOT EXISTS staygenius CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE staygenius;
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS invoices, reviews, service_requests, price_overrides, bookings, rooms, guest_profiles, services, room_types, users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('guest','staff','manager','admin') NOT NULL DEFAULT 'guest',
  language VARCHAR(10) NOT NULL DEFAULT 'en',
  active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guest_profiles (
  user_id INT PRIMARY KEY,
  phone VARCHAR(20) DEFAULT '',
  preferences VARCHAR(255) DEFAULT '',
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE room_types (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(60) NOT NULL UNIQUE,
  description VARCHAR(255) DEFAULT '',
  base_price DECIMAL(10,2) NOT NULL,
  capacity INT NOT NULL DEFAULT 2
);

CREATE TABLE rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  number VARCHAR(10) NOT NULL UNIQUE,
  room_type_id INT NOT NULL,
  floor INT NOT NULL DEFAULT 1,
  status ENUM('vacant','occupied','cleaning','maintenance') NOT NULL DEFAULT 'vacant',
  FOREIGN KEY (room_type_id) REFERENCES room_types(id)
);

CREATE TABLE bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guest_id INT NOT NULL,
  room_id INT NOT NULL,
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  guests INT NOT NULL DEFAULT 1,
  rate DECIMAL(10,2) NOT NULL,          -- average nightly rate
  total DECIMAL(12,2) NOT NULL,         -- room charges for the stay
  status ENUM('payment_pending','confirmed','checked_in','checked_out','cancelled') NOT NULL DEFAULT 'confirmed',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (guest_id) REFERENCES users(id),
  FOREIGN KEY (room_id) REFERENCES rooms(id),
  INDEX idx_room_dates (room_id, check_in, check_out),
  INDEX idx_checkin (check_in),
  INDEX idx_guest (guest_id),
  CONSTRAINT chk_dates CHECK (check_out > check_in)
);

CREATE TABLE payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  guest_id INT NOT NULL,
  razorpay_order_id VARCHAR(64) NOT NULL UNIQUE,
  payment_id VARCHAR(64) NULL UNIQUE,
  amount_paise INT UNSIGNED NOT NULL,
  status ENUM('pending','paid','expired') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paid_at TIMESTAMP NULL,
  FOREIGN KEY (booking_id) REFERENCES bookings(id),
  FOREIGN KEY (guest_id) REFERENCES users(id),
  INDEX idx_payment_expiry (status, created_at)
);

CREATE TABLE services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  category ENUM('housekeeping','food','maintenance') NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0
);

CREATE TABLE service_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  guest_id INT NOT NULL,
  category ENUM('housekeeping','food','maintenance') NOT NULL,
  description VARCHAR(300) NOT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0,
  status ENUM('pending','in_progress','done') NOT NULL DEFAULT 'pending',
  priority ENUM('normal','high') NOT NULL DEFAULT 'normal',
  auto_generated TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id),
  FOREIGN KEY (guest_id) REFERENCES users(id),
  INDEX idx_status (status)
);

CREATE TABLE reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guest_id INT NOT NULL,
  booking_id INT NULL,
  rating TINYINT NOT NULL,
  comment TEXT NOT NULL,
  sentiment ENUM('positive','neutral','negative') NOT NULL,
  themes VARCHAR(200) DEFAULT '',
  reply TEXT NULL,
  replied_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (guest_id) REFERENCES users(id),
  CONSTRAINT chk_rating CHECK (rating BETWEEN 1 AND 5)
);

CREATE TABLE invoices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL UNIQUE,
  room_charges DECIMAL(12,2) NOT NULL,
  service_charges DECIMAL(12,2) NOT NULL DEFAULT 0,
  tax DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- Manager-approved nightly prices (override the room type base price for one date)
CREATE TABLE price_overrides (
  room_type_id INT NOT NULL,
  stay_date DATE NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (room_type_id, stay_date),
  FOREIGN KEY (room_type_id) REFERENCES room_types(id) ON DELETE CASCADE
);
