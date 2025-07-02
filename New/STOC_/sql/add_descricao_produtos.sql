SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'produtos' AND COLUMN_NAME = 'descricao');

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE produtos ADD COLUMN descricao TEXT',
    'SELECT "Coluna descricao já existe na tabela produtos" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
