CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    impressora_id INT,
    FOREIGN KEY (impressora_id) REFERENCES impressoras(id)
);
