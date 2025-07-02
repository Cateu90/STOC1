
SET @column_nullable = (SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'comandas' AND COLUMN_NAME = 'mesa_id');

SET @sql = IF(@column_nullable = 'NO', 
    'ALTER TABLE comandas MODIFY mesa_id INT NULL',
    'SELECT "Coluna mesa_id já permite NULL" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;