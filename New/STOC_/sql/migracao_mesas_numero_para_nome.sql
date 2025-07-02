
SET @column_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mesas' AND COLUMN_NAME = 'nome');

SET @sql = IF(@column_exists = 0, 
    'ALTER TABLE mesas ADD COLUMN nome VARCHAR(255)',
    'SELECT "Coluna nome já existe na tabela mesas" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @numero_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mesas' AND COLUMN_NAME = 'numero');

SET @sql = IF(@numero_exists > 0, 
    'UPDATE mesas SET nome = CONCAT("Mesa ", numero) WHERE nome IS NULL AND numero IS NOT NULL',
    'SELECT "Coluna numero não existe, pulando migração de dados" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @numero_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mesas' AND COLUMN_NAME = 'numero');

SET @empty_names = (SELECT COUNT(*) FROM mesas WHERE nome IS NULL OR nome = '');

SET @sql = IF(@numero_exists > 0 AND @empty_names = 0, 
    'ALTER TABLE mesas DROP COLUMN numero',
    'SELECT "Coluna numero não pode ser removida (não existe ou nomes não preenchidos)" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_nullable = (SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mesas' AND COLUMN_NAME = 'nome');

SET @sql = IF(@column_nullable = 'YES', 
    'ALTER TABLE mesas MODIFY COLUMN nome VARCHAR(255) NOT NULL',
    'SELECT "Coluna nome já é NOT NULL" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @column_type = (SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mesas' AND COLUMN_NAME = 'status');

SET @sql = IF(@column_type NOT LIKE '%disponivel%' OR @column_type NOT LIKE '%ocupada%' OR @column_type NOT LIKE '%reservada%', 
    'ALTER TABLE mesas MODIFY COLUMN status ENUM("disponivel", "ocupada", "reservada") NOT NULL DEFAULT "disponivel"',
    'SELECT "Coluna status já tem o tipo correto" as message');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
