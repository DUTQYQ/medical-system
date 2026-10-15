-- v2 additive extension. Existing v1 tables must already exist.

-- No DROP, ALTER, data reset or production demo inventory.

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS care_equipment (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	total INTEGER NOT NULL, 
	available INTEGER NOT NULL, 
	damaged INTEGER NOT NULL, 
	description TEXT, 
	enabled INTEGER NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_service_catalog (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	category VARCHAR(30) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(500), 
	enabled INTEGER NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_activity (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	title VARCHAR(100) NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	start_at DATETIME NOT NULL, 
	end_at DATETIME NOT NULL, 
	location VARCHAR(150) NOT NULL, 
	capacity INTEGER NOT NULL, 
	reserved_count INTEGER NOT NULL, 
	description TEXT, 
	status VARCHAR(20) NOT NULL, 
	creator_id BIGINT NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(creator_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS advice_card (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	created_by BIGINT NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	mode VARCHAR(10) NOT NULL, 
	content JSON NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(created_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_activity_registration (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	activity_id BIGINT NOT NULL, 
	profile_id BIGINT NOT NULL, 
	creator_id BIGINT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	recorded_by BIGINT, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (activity_id, profile_id), 
	FOREIGN KEY(activity_id) REFERENCES care_activity (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(creator_id) REFERENCES user (id), 
	FOREIGN KEY(recorded_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_service_notification (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	recipient_id BIGINT NOT NULL, 
	profile_id BIGINT NOT NULL, 
	ref_type VARCHAR(30) NOT NULL, 
	ref_id BIGINT NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	content TEXT, 
	read_status VARCHAR(10) NOT NULL, 
	read_at DATETIME, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(recipient_id) REFERENCES user (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_service_request (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	creator_id BIGINT NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	location VARCHAR(150) NOT NULL, 
	requested_at DATETIME, 
	priority INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	assigned_to BIGINT, 
	accepted_at DATETIME, 
	completed_at DATETIME, 
	escalated_at DATETIME, 
	result TEXT, 
	active_call_key VARCHAR(30), 
	equipment_id BIGINT, 
	quantity INTEGER, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(creator_id) REFERENCES user (id), 
	FOREIGN KEY(assigned_to) REFERENCES user (id), 
	UNIQUE (active_call_key), 
	FOREIGN KEY(equipment_id) REFERENCES care_equipment (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS consultation_intake (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	template_version VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	answers JSON NOT NULL, 
	created_by BIGINT NOT NULL, 
	confirmed_by BIGINT, 
	confirmed_at DATETIME, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_intake_profile_template UNIQUE (profile_id, template_version), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(created_by) REFERENCES user (id), 
	FOREIGN KEY(confirmed_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS profile_threshold_version (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	indicator VARCHAR(30) NOT NULL, 
	config_id BIGINT, 
	restore_default INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	proposed_by BIGINT NOT NULL, 
	reviewed_by BIGINT, 
	review_note VARCHAR(500), 
	reviewed_at DATETIME, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(config_id) REFERENCES sys_config (id), 
	FOREIGN KEY(proposed_by) REFERENCES user (id), 
	FOREIGN KEY(reviewed_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_profile_threshold_version_indicator ON profile_threshold_version (indicator);

CREATE INDEX ix_profile_threshold_version_profile_id ON profile_threshold_version (profile_id);

CREATE INDEX ix_profile_threshold_version_status ON profile_threshold_version (status);

CREATE TABLE IF NOT EXISTS care_equipment_loan (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	request_id BIGINT NOT NULL, 
	equipment_id BIGINT NOT NULL, 
	profile_id BIGINT NOT NULL, 
	quantity INTEGER NOT NULL, 
	issued_by BIGINT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	returned_at DATETIME, 
	returned_by BIGINT, 
	return_note TEXT, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (request_id), 
	FOREIGN KEY(request_id) REFERENCES care_service_request (id), 
	FOREIGN KEY(equipment_id) REFERENCES care_equipment (id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(issued_by) REFERENCES user (id), 
	FOREIGN KEY(returned_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS care_service_event (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	request_id BIGINT NOT NULL, 
	actor_id BIGINT, 
	from_status VARCHAR(20), 
	to_status VARCHAR(20) NOT NULL, 
	note TEXT, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES care_service_request (id), 
	FOREIGN KEY(actor_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS health_record_void (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	record_id BIGINT NOT NULL, 
	voided_by BIGINT NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (record_id), 
	FOREIGN KEY(record_id) REFERENCES health_record (id), 
	FOREIGN KEY(voided_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS profile_fact (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	fact_key VARCHAR(50) NOT NULL, 
	label VARCHAR(100) NOT NULL, 
	value JSON NOT NULL, 
	version INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	source_intake_id BIGINT, 
	reported_by BIGINT NOT NULL, 
	confirmed_by BIGINT NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	valid_until DATETIME, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_fact_profile_key UNIQUE (profile_id, fact_key), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(source_intake_id) REFERENCES consultation_intake (id), 
	FOREIGN KEY(reported_by) REFERENCES user (id), 
	FOREIGN KEY(confirmed_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS health_assessment (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	profile_id BIGINT NOT NULL, 
	record_id BIGINT, 
	warning_id BIGINT, 
	risk_level INTEGER NOT NULL, 
	thresholds JSON NOT NULL, 
	`values` JSON NOT NULL, 
	create_time DATETIME NOT NULL, 
	update_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (record_id), 
	UNIQUE (warning_id), 
	FOREIGN KEY(profile_id) REFERENCES elder_profile (id), 
	FOREIGN KEY(record_id) REFERENCES health_record (id) ON DELETE SET NULL, 
	FOREIGN KEY(warning_id) REFERENCES health_warning (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX ix_health_assessment_profile_id ON health_assessment (profile_id);

CREATE TABLE IF NOT EXISTS profile_fact_revision (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	fact_id BIGINT NOT NULL, 
	version INTEGER NOT NULL, 
	value JSON NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	changed_by BIGINT NOT NULL, 
	change_reason VARCHAR(100) NOT NULL, 
	source_intake_id BIGINT, 
	reported_by BIGINT, 
	valid_until DATETIME, 
	create_time DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_fact_revision_version UNIQUE (fact_id, version), 
	FOREIGN KEY(fact_id) REFERENCES profile_fact (id), 
	FOREIGN KEY(changed_by) REFERENCES user (id), 
	FOREIGN KEY(source_intake_id) REFERENCES consultation_intake (id), 
	FOREIGN KEY(reported_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
