# Finance Data Reconciliation Automation

Automated reconciliation system for comparing transaction records from two CSV/Excel files, with MySQL storage, n8n workflow automation, and detailed reporting.

## Features

- **Data Ingestion**: Load CSV/Excel files with transaction records
- **Data Validation**: Comprehensive validation with detailed error reporting
- **Data Cleaning**: Standardize formats, handle missing values, parse dates/amounts
- **Reconciliation Engine**: Identify matches, duplicates, missing records, and mismatches
- **MySQL Storage**: Persistent storage of transactions, results, and audit logs
- **n8n Automation**: Scheduled workflow with email notifications
- **Reporting**: Human-readable and JSON reports with summary statistics
- **Error Handling**: Robust error handling with database error logging

## Project Structure

```
finance-reconciliation/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── sql/
│   └── schema.sql          # MySQL database schema
├── data/
│   ├── source_transactions.csv   # Sample source data
│   └── target_transactions.csv   # Sample target data
├── scripts/
│   └── reconcile.py        # Main reconciliation script
├── n8n/
│   └── workflow.json       # n8n workflow definition
└── reports/                # Generated reports (auto-created)
```

## Quick Start

### 1. Install Dependencies

```bash
cd finance-reconciliation
pip install -r requirements.txt
```

### 2. Set Up MySQL Database

```bash
# Create database and tables
mysql -u root -p < sql/schema.sql
```

### 3. Configure Database Connection

Edit `config.yaml` with your MySQL credentials:

```yaml
database:
  host: "localhost"
  port: 3306
  user: "your_username"
  password: "your_password"
  database: "finance_reconciliation"
```

### 4. Run Reconciliation

```bash
# Using default config files
python scripts/reconcile.py

# Override source/target files
python scripts/reconcile.py --source data/file1.csv --target data/file2.csv

# Custom output report
python scripts/reconcile.py --output reports/my_report.txt
```

### 5. View Results

Reports are saved to:
- `reports/reconciliation_<run_id>.txt` - Human readable
- `reports/reconciliation_<run_id>.json` - Machine readable

## n8n Workflow Setup

1. Import `n8n/workflow.json` into n8n
2. Update file paths in the workflow nodes
3. Configure SMTP credentials for email notifications
4. Activate the workflow for daily automated runs

The workflow:
- Runs daily at 2 AM
- Checks for new CSV/Excel files in data directory
- Executes reconciliation
- Sends success/failure email notifications
- Archives processed files

## Reconciliation Logic

### Match Types

| Type | Description |
|------|-------------|
| `matched` | Amount, date, and description match within tolerance |
| `amount_mismatch` | Same transaction_id but different amounts |
| `date_mismatch` | Same transaction_id but different dates |
| `description_mismatch` | Same transaction_id, amount, date but different descriptions |
| `missing_in_target` | Transaction exists in source but not target |
| `missing_in_source` | Transaction exists in target but not source |
| `duplicate_source` | Duplicate transaction_id in source file |
| `duplicate_target` | Duplicate transaction_id in target file |

### Tolerance Settings

- `amount_tolerance`: Default 0.01 (1 cent)
- `date_tolerance_days`: Default 0 (exact match)

## Data Format

Required columns in CSV/Excel:
- `transaction_id` - Unique identifier
- `date` - Transaction date (YYYY-MM-DD)
- `amount` - Transaction amount

Optional columns:
- `description` - Transaction description
- `category` - Category classification
- `account` - Account name
- `reference` - Reference number
- `status` - pending/cleared/failed

## Sample Output

```
================================================================================
FINANCE RECONCILIATION REPORT
================================================================================
Run ID: a1b2c3d4
Date: 2024-01-15 10:30:45
Source File: data/source_transactions.csv
Target File: data/target_transactions.csv

SUMMARY
----------------------------------------
Total Source Records:        20
Total Target Records:        25
Matched:                     17
Duplicate in Source:          0
Duplicate in Target:          2
Missing in Target:            0
Missing in Source:            5
Amount Mismatch:              1
Date Mismatch:                1
Description Mismatch:         0
Total Discrepancies:          9

DETAILED DISCREPANCIES
----------------------------------------

DUPLICATE IN TARGET (2):
  TXN: TXN003
    Amount: $3,200.50 | Date: 2024-01-17
  TXN: TXN010
    Amount: $1,800.00 | Date: 2024-01-24

MISSING IN SOURCE (5):
  TXN: TXN021
    Amount: $1,250.00 | Date: 2024-02-04
  TXN: TXN022
    Amount: $500.00 | Date: 2024-02-05
  ...

AMOUNT MISMATCH (1):
  TXN: TXN010
    Source: $1,800.00 | Target: $1,850.00 | Diff: $-50.00

DATE MISMATCH (1):
  TXN: TXN015
    Source Date: 2024-01-29 | Target Date: 2024-01-30 | Diff: 1 days

================================================================================
```

## Database Tables

- `source_transactions` - Cleaned source file transactions
- `target_transactions` - Cleaned target file transactions
- `reconciliation_results` - Detailed match results per transaction
- `reconciliation_summary` - Summary statistics per run
- `error_log` - Validation and processing errors

## Error Handling

- Invalid rows are logged to `error_log` table with full context
- Validation warnings don't stop processing
- Database errors are caught and logged
- Script returns exit code 1 on failure for automation integration

## Customization

### Add New Validation Rules

Extend `DataValidator._validate_row()` in `scripts/reconcile.py`

### Modify Matching Logic

Adjust `ReconciliationEngine._compare_rows()` for custom matching

### Add New Report Formats

Extend `ReconciliationEngine.generate_report()` method

## License

MIT