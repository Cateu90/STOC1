CREATE TABLE IF NOT EXISTS mesas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    status ENUM('disponivel', 'ocupada', 'reservada') NOT NULL DEFAULT 'disponivel'
);
