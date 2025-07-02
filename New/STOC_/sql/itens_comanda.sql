CREATE TABLE IF NOT EXISTS itens_comanda (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comanda_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);
