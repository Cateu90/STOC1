SET @sql = 'ALTER TABLE comandas ADD COLUMN numero INT UNIQUE AFTER id';
SET @sql = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'comandas' 
     AND COLUMN_NAME = 'numero') = 0,
    @sql,
    'SELECT "Coluna numero já existe" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @index_sql = 'CREATE INDEX idx_comandas_numero ON comandas(numero)';
SET @index_sql = IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS 
     WHERE TABLE_SCHEMA = DATABASE() 
     AND TABLE_NAME = 'comandas' 
     AND INDEX_NAME = 'idx_comandas_numero') = 0,
    @index_sql,
    'SELECT "Índice já existe" as message'
);

PREPARE idx_stmt FROM @index_sql;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;
