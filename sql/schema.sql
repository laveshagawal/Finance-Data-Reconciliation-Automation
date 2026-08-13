-- Finance Reconciliation Database Schema
CREATE DATABASE IF NOT EXISTS finance_reconciliation;
USE finance_reconciliation;

-- Source transactions table (from file 1)
CREATE TABLE IF NOT EXISTS source_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    description VARCHAR(255),
    category VARCHAR(100),
    account VARCHAR(100),
    reference VARCHAR(100),
    status ENUM('pending', 'cleared', 'failed') DEFAULT 'pending',
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_transaction (transaction_id, source_file)
);

-- Target transactions table (from file 2)
CREATE TABLE IF NOT EXISTS target_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    description VARCHAR(255),
    category VARCHAR(100),
    account VARCHAR(100),
    reference VARCHAR(100),
    status ENUM('pending', 'cleared', 'failed') DEFAULT 'pending',
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_transaction (transaction_id, source_file)
);

-- Reconciliation results table
CREATE TABLE IF NOT EXISTS reconciliation_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    source_transaction_id INT,
    target_transaction_id INT,
    match_type ENUM('matched', 'duplicate_source', 'duplicate_target', 'missing_in_target', 'missing_in_source', 'amount_mismatch', 'date_mismatch', 'description_mismatch') NOT NULL,
    source_amount DECIMAL(15, 2),
    target_amount DECIMAL(15, 2),
    difference DECIMAL(15, 2),
    details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_id (run_id),
    INDEX idx_match_type (match_type)
);

-- Error log table
CREATE TABLE IF NOT EXISTS error_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    source_file VARCHAR(255),
    row_num INT,
    error_type ENUM('validation', 'parsing', 'database', 'reconciliation') NOT NULL,
    error_message TEXT,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_run_id (run_id)
);

-- Reconciliation summary table
CREATE TABLE IF NOT EXISTS reconciliation_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL UNIQUE,
    source_file VARCHAR(255),
    target_file VARCHAR(255),
    total_source_records INT DEFAULT 0,
    total_target_records INT DEFAULT 0,
    matched_count INT DEFAULT 0,
    duplicate_source_count INT DEFAULT 0,
    duplicate_target_count INT DEFAULT 0,
    missing_in_target_count INT DEFAULT 0,
    missing_in_source_count INT DEFAULT 0,
    amount_mismatch_count INT DEFAULT 0,
    date_mismatch_count INT DEFAULT 0,
    description_mismatch_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    status ENUM('running', 'completed', 'failed') DEFAULT 'running'
);
