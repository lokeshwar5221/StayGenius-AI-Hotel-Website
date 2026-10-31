ALTER TABLE bookings
  MODIFY status ENUM('payment_pending','confirmed','checked_in','checked_out','cancelled')
  NOT NULL DEFAULT 'confirmed';

CREATE TABLE IF NOT EXISTS payments (
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