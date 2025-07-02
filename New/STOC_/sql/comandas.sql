CREATE TABLE IF NOT EXISTS comandas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mesa_id INT NULL,
    garcom_id INT NOT NULL,
    status ENUM('aberta', 'fechada') NOT NULL DEFAULT 'aberta',
    total DECIMAL(10,2) NOT NULL DEFAULT 0.0,
    pagamento VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mesa_id) REFERENCES mesas(id),
    FOREIGN KEY (garcom_id) REFERENCES users(id)
);
