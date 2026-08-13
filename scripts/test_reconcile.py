#!/usr/bin/env python3
"""
Test script to run reconciliation without database connection.
Useful for testing and demonstration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from reconcile import ReconciliationEngine, ReconciliationConfig, DataValidator
import pandas as pd
from pathlib import Path

def main():
    # Configuration for test (no database)
    config = ReconciliationConfig(
        source_file='data/source_transactions.csv',
        target_file='data/target_transactions.csv',
        db_config={},  # Not used in test
        amount_tolerance=0.01,
        date_tolerance_days=0,
        key_columns=['transaction_id']
    )
    
    # Load data
    source_raw = pd.read_csv(config.source_file)
    target_raw = pd.read_csv(config.target_file)
    
    print(f"Loaded {len(source_raw)} source records")
    print(f"Loaded {len(target_raw)} target records")
    
    # Validate
    validator = DataValidator(config)
    
    source_validation = validator.validate_dataframe(source_raw, 'Source')
    print(f"\nSource Validation: {'PASSED' if source_validation.is_valid else 'FAILED'}")
    for err in source_validation.errors:
        print(f"  ERROR: {err}")
    for warn in source_validation.warnings:
        print(f"  WARNING: {warn}")
    
    target_validation = validator.validate_dataframe(target_raw, 'Target')
    print(f"\nTarget Validation: {'PASSED' if target_validation.is_valid else 'FAILED'}")
    for err in target_validation.errors:
        print(f"  ERROR: {err}")
    for warn in target_validation.warnings:
        print(f"  WARNING: {warn}")
    
    # Clean
    source_clean = validator.clean_dataframe(source_raw, 'Source')
    target_clean = validator.clean_dataframe(target_raw, 'Target')
    
    print(f"\nCleaned Source: {len(source_clean)} records")
    print(f"Cleaned Target: {len(target_clean)} records")
    
    # Reconcile (without DB)
    engine = ReconciliationEngine(config)
    matches = engine.reconcile(source_clean, target_clean)
    
    # Summary
    summary = engine.generate_summary(matches, len(source_clean), len(target_clean))
    
    # Report
    report = engine.generate_report(matches, summary)
    print("\n" + report)
    
    # Save report
    os.makedirs('reports', exist_ok=True)
    with open('reports/test_reconciliation_report.txt', 'w') as f:
        f.write(report)
    print("\nReport saved to reports/test_reconciliation_report.txt")

if __name__ == '__main__':
    main()