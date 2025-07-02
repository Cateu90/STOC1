SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'impressoras' AND COLUMN_NAME = 'printer_name');

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE impressoras ADD COLUMN printer_name VARCHAR(255) AFTER setor',
    'SELECT "Coluna printer_name já existe na tabela impressoras" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
