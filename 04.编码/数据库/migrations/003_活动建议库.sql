-- Additive activity suggestions only. Existing v2 tables must already exist.
-- No DROP, ALTER or demo inventory. Apply normal upgrades through scripts/migrate_v2.py.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS activity (
	id BIGINT NOT NULL AUTO_INCREMENT,
	code VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	category VARCHAR(50),
	intensity VARCHAR(20),
	description TEXT,
	benefits TEXT,
	duration_hint VARCHAR(100),
	rules VARCHAR(1000),
	contraindications VARCHAR(500),
	enabled INTEGER NOT NULL,
	create_time DATETIME NOT NULL,
	update_time DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
