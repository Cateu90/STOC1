CREATE TABLE IF NOT EXISTS impressora_categorias (
    impressora_id INT NOT NULL,
    categoria_id INT NOT NULL,
    PRIMARY KEY (impressora_id, categoria_id),
    FOREIGN KEY (impressora_id) REFERENCES impressoras(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
);
