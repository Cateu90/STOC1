CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    preco DECIMAL(10,2) NOT NULL,
    categoria_id INT NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);
