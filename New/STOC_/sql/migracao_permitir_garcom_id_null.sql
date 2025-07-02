
SET @column_nullable = (SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comandas' AND COLUMN_NAME = 'garcom_id');

SET @sql = IF(@column_nullable = 'NO', 
    'ALTER TABLE comandas MODIFY garcom_id INT NULL',
    'SELECT "Coluna garcom_id já permite NULL" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
