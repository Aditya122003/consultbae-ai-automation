-- Database schema definition for ConsultBae Data Ingestion and Automation Platform
-- Creates normalized tables for merged candidates, audio submissions, and audit tracking

CREATE DATABASE IF NOT EXISTS consultbae_db;
USE consultbae_db;

-- Drop existing tables in reverse dependency order to ensure clean initialization
DROP TABLE IF EXISTS data_cleaning_audit;
DROP TABLE IF EXISTS audio_submissions;
DROP TABLE IF EXISTS candidates;

-- Master table storing consolidated worker records merged across all 3 source systems
CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(50) NULL,
    city VARCHAR(100) NULL,
    experience_years DECIMAL(4, 2) NULL,
    current_ctc_lpa DECIMAL(6, 2) NULL,
    applied_date DATE NULL,
    rate_hourly_inr DECIMAL(8, 2) NULL,
    rate_monthly_inr DECIMAL(10, 2) NULL,
    status VARCHAR(50) DEFAULT 'Active',
    skills TEXT NULL,
    skill_category VARCHAR(100) DEFAULT 'General',
    is_verified VARCHAR(20) DEFAULT 'No',
    projects_completed INT DEFAULT 0,
    data_sources VARCHAR(255) DEFAULT 'None',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone (phone),
    INDEX idx_email (email),
    INDEX idx_city (city),
    INDEX idx_status (status),
    INDEX idx_skill_category (skill_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audio submissions table storing recordings and signal processing parameters for Task 3
CREATE TABLE IF NOT EXISTS audio_submissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT NULL,
    worker_name VARCHAR(255) NOT NULL,
    worker_phone VARCHAR(50) NOT NULL,
    audio_filename VARCHAR(255) NOT NULL,
    audio_filepath VARCHAR(500) NOT NULL,
    audio_url VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    duration_seconds DECIMAL(8, 2) NOT NULL,
    sample_rate_hz INT NOT NULL,
    sample_rate_khz DECIMAL(6, 2) NOT NULL,
    bitrate_kbps DECIMAL(8, 2) NOT NULL,
    loudness_db DECIMAL(6, 2) NOT NULL,
    snr_quality_score DECIMAL(6, 2) NOT NULL,
    quality_label VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE SET NULL,
    INDEX idx_worker_phone (worker_phone),
    INDEX idx_quality_label (quality_label),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit logging table tracking anomalies, planted bugs, and automated fixes applied during ingestion
CREATE TABLE IF NOT EXISTS data_cleaning_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    row_index INT NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    raw_data TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
