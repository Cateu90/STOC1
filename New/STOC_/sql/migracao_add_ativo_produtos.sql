SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'produtos' AND COLUMN_NAME = 'ativo');

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE produtos ADD COLUMN ativo TINYINT(1) NOT NULL DEFAULT 1',
    'SELECT "Coluna ativo já existe na tabela produtos" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE produtos SET ativo = 1 WHERE ativo IS NULL;
