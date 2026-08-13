# Finance Data Reconciliation Automation

An end-to-end finance data reconciliation system that validates, cleans,
compares, stores, reports, and automatically alerts on discrepancies
between two transaction datasets.

The project combines **Python + Pandas + MySQL + YAML + JSON + n8n +
Gmail** to turn a manual reconciliation task into a repeatable automated
workflow.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Problem Statement](#problem-statement)
-   [Solution](#solution)
-   [Architecture](#architecture)
-   [Features](#features)
-   [Tech Stack](#tech-stack)
-   [Project Structure](#project-structure)
-   [Reconciliation Logic](#reconciliation-logic)
-   [Discrepancy Types](#discrepancy-types)
-   [Data Validation and Cleaning](#data-validation-and-cleaning)
-   [Database Design](#database-design)
-   [Reports](#reports)
-   [n8n Automation](#n8n-automation)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Database Setup](#database-setup)
-   [Running the Reconciliation
    Engine](#running-the-reconciliation-engine)
-   [n8n Setup](#n8n-setup)
-   [Testing](#testing)
-   [Example Workflow](#example-workflow)
-   [Error Handling and Logging](#error-handling-and-logging)
-   [Design Decisions](#design-decisions)
-   [Limitations](#limitations)
-   [Future Improvements](#future-improvements)
-   [Key Interview Talking Points](#key-interview-talking-points)

------------------------------------------------------------------------

## Overview

Financial data often exists in multiple systems, such as a source
ledger, payment processor, accounting system, or reporting system. These
systems can contain differences caused by missing transactions,
duplicate records, incorrect amounts, different dates, or inconsistent
descriptions.

This project automates the reconciliation process by comparing a
**source dataset** against a **target dataset** using `transaction_id`
as the primary business key.

The system:

1.  Loads source and target CSV/Excel files.
2.  Validates the input schema and transaction records.
3.  Cleans and standardizes the data.
4.  Stores cleaned transactions in MySQL.
5.  Reconciles source and target records.
6.  Detects duplicates, missing records, and field-level mismatches.
7.  Stores reconciliation results and summaries in MySQL.
8.  Generates a human-readable report.
9.  Generates a structured JSON report for automation.
10. Uses n8n to schedule and orchestrate the process.
11. Sends a Gmail success notification when no discrepancies exist.
12. Sends a Gmail alert when discrepancies are detected.
13. Archives reconciliation reports for historical tracking.

------------------------------------------------------------------------

## Problem Statement

Manual reconciliation becomes difficult and error-prone when transaction
datasets grow or when the process has to be repeated regularly.

Typical problems include:

-   Transactions present in one system but missing from another.
-   Duplicate transaction IDs.
-   Amount differences.
-   Date differences.
-   Description differences.
-   Invalid or incomplete transaction records.
-   Lack of historical reconciliation records.
-   Manual checking and notification.

The goal of this project is to automate these tasks while maintaining an
auditable record of each reconciliation run.

------------------------------------------------------------------------

## Solution

The project follows a separation-of-concerns approach:

  Component   Responsibility
  ----------- ------------------------------------------------------
  Python      Core reconciliation and data-processing logic
  Pandas      Data loading, cleaning, validation, and comparison
  NumPy       Missing-value handling
  MySQL       Persistent storage and audit history
  YAML        External configuration
  JSON        Machine-readable reconciliation output
  n8n         Scheduling, orchestration, branching, and automation
  Gmail       Success and discrepancy notifications

------------------------------------------------------------------------

## Architecture

``` text
                    ┌─────────────────────┐
                    │   Source CSV/XLSX   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │                     │
                    │   Python Engine     │
                    │                     │
                    │  Load → Validate    │
                    │  → Clean → Compare  │
                    │                     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Target CSV/XLSX   │
                    └─────────────────────┘

                               │
                               ▼
                    ┌─────────────────────┐
                    │ Reconciliation      │
                    │                     │
                    │ transaction_id      │
                    │ amount              │
                    │ date                │
                    │ description         │
                    │ duplicates          │
                    │ missing records     │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌─────────────────┐        ┌─────────────────┐
        │      MySQL      │        │   JSON Report   │
        │                 │        │                 │
        │ Transactions    │        │ Summary         │
        │ Results         │        │ Matches         │
        │ Summary         │        │ Run ID          │
        │ Error Log       │        └────────┬────────┘
        └─────────────────┘                 │
                                            ▼
                                  ┌────────────────────┐
                                  │        n8n         │
                                  │                    │
                                  │ Schedule           │
                                  │ Execute Python     │
                                  │ Read JSON          │
                                  │ Check discrepancies│
                                  └─────────┬──────────┘
                                            │
                               ┌────────────┴────────────┐
                               ▼                         ▼
                      Discrepancies > 0          Discrepancies = 0
                               │                         │
                               ▼                         ▼
                         Gmail Alert              Gmail Success
                               │                         │
                               └────────────┬────────────┘
                                            ▼
                                         Archive
```

------------------------------------------------------------------------

## Features

### Data Validation

Checks:

-   Required columns.
-   Empty datasets.
-   Missing transaction IDs.
-   Missing dates.
-   Invalid date formats.
-   Missing amounts.
-   Invalid amount values.
-   Invalid transaction statuses.
-   Duplicate transaction IDs.

### Data Cleaning

The system:

-   Normalizes column names.
-   Strips whitespace.
-   Standardizes dates.
-   Converts amounts to numeric values.
-   Normalizes string fields.
-   Standardizes transaction statuses.
-   Removes rows missing required fields.

### Reconciliation

Transactions are aligned using:

``` text
transaction_id
```

The system compares:

-   Transaction existence.
-   Duplicate records.
-   Amount.
-   Date.
-   Description.

### Configurable Tolerance

Amount and date comparison thresholds can be configured instead of being
hard-coded.

Default configuration:

``` text
amount_tolerance = 0.01
date_tolerance_days = 0
```

### Persistent Storage

MySQL stores:

-   Source transactions.
-   Target transactions.
-   Reconciliation results.
-   Reconciliation summaries.
-   Processing errors.

### Automated Reporting

Every run produces:

-   Human-readable reconciliation output.
-   Run-specific JSON report.
-   Latest JSON report for downstream automation.

### Automated Notifications

n8n evaluates the JSON result and sends:

-   A success email when there are no discrepancies.
-   An alert email when discrepancies are found.

### Historical Archiving

Reconciliation reports can be archived so previous runs can be reviewed
later.

------------------------------------------------------------------------

## Tech Stack

### Programming

-   Python 3.x

### Data Processing

-   Pandas
-   NumPy

### Database

-   MySQL
-   `mysql-connector-python`

### Configuration and Serialization

-   YAML
-   JSON

### Automation

-   n8n

### Notifications

-   Gmail integration through n8n

### Development

-   Git
-   GitHub
-   Python virtual environment (`venv`)
-   PowerShell / Windows command line

------------------------------------------------------------------------

## Project Structure

``` text
finance-reconciliation/
│
├── .venv/
│
├── data/
│   ├── source_transactions.csv
│   ├── target_transactions.csv
│   └── target_transactions_backup.csv
│
├── scripts/
│   ├── reconcile.py
│   └── test_reconcile.py
│
├── sql/
│   └── schema.sql
│
├── n8n/
│   └── workflow.json
│
├── reports/
│   ├── latest_reconciliation.json
│   └── reconciliation_<run_id>.json
│
├── archive/
│   └── archived reconciliation reports
│
├── config.yaml
├── requirements.txt
├── reconciliation.log
└── README.md
```

> Do not commit real financial data, credentials, database passwords, or
> private email information to GitHub.

------------------------------------------------------------------------

## Reconciliation Logic

The reconciliation engine uses `transaction_id` as the primary key.

Conceptually:

``` python
source_dict = {
    transaction_id: source_row
}

target_dict = {
    transaction_id: target_row
}

all_keys = source_keys UNION target_keys
```

Each transaction ID is then evaluated.

### Case 1: Exists in both datasets

The system compares:

``` text
Amount
Date
Description
```

### Case 2: Exists only in source

Result:

``` text
missing_in_target
```

### Case 3: Exists only in target

Result:

``` text
missing_in_source
```

### Case 4: Appears multiple times

Result:

``` text
duplicate_source
```

or:

``` text
duplicate_target
```

------------------------------------------------------------------------

## Amount Comparison

The system calculates the absolute difference:

``` text
amount_diff = abs(source_amount - target_amount)
```

The difference is compared against the configured tolerance.

For example:

``` text
Source amount = 100.00
Target amount = 100.005

Difference = 0.005
```

If:

``` text
amount_tolerance = 0.01
```

the amount difference is within tolerance.

------------------------------------------------------------------------

## Date Comparison

Dates are converted to datetime values and compared in days:

``` text
date_diff_days = abs(source_date - target_date)
```

For example:

``` text
Source = 2026-01-10
Target = 2026-01-11

Difference = 1 day
```

If:

``` text
date_tolerance_days = 0
```

this is classified as a date mismatch.

------------------------------------------------------------------------

## Description Comparison

Descriptions are normalized using:

-   Whitespace stripping.
-   Lowercase conversion.

Example:

``` text
"Amazon Payment"
```

and:

``` text
" amazon payment "
```

are normalized before comparison.

If amount and date are within tolerance but descriptions differ, the
transaction is classified as:

``` text
description_mismatch
```

------------------------------------------------------------------------

## Discrepancy Types

The system supports the following reconciliation results:

  -----------------------------------------------------------------------
  Type                                Meaning
  ----------------------------------- -----------------------------------
  `matched`                           Source and target records agree

  `duplicate_source`                  Duplicate transaction exists in
                                      source

  `duplicate_target`                  Duplicate transaction exists in
                                      target

  `missing_in_target`                 Source transaction is absent from
                                      target

  `missing_in_source`                 Target transaction is absent from
                                      source

  `amount_mismatch`                   Transaction amounts differ beyond
                                      tolerance

  `date_mismatch`                     Transaction dates differ beyond
                                      tolerance

  `description_mismatch`              Descriptions differ while other
                                      matching conditions pass
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Data Validation and Cleaning

Required columns:

``` text
transaction_id
date
amount
```

Optional columns:

``` text
description
category
account
reference
status
```

Valid transaction statuses:

``` text
pending
cleared
failed
```

Validation errors stop processing when the input data is not valid.

Warnings are logged for non-fatal issues such as duplicate transaction
IDs or invalid statuses.

------------------------------------------------------------------------

## Database Design

The application uses MySQL for persistent storage.

### `source_transactions`

Stores cleaned source transaction records.

Typical fields include:

``` text
transaction_id
date
amount
description
category
account
reference
status
source_file
```

### `target_transactions`

Stores cleaned target transaction records using the same transaction
structure.

### `reconciliation_results`

Stores the result of comparing individual source and target records.

Important fields include:

``` text
run_id
source_transaction_id
target_transaction_id
match_type
source_amount
target_amount
difference
details
```

### `reconciliation_summary`

Stores run-level statistics such as:

``` text
total_source_records
total_target_records
matched_count
duplicate_source_count
duplicate_target_count
missing_in_target_count
missing_in_source_count
amount_mismatch_count
date_mismatch_count
description_mismatch_count
status
completed_at
```

### `error_log`

Stores processing and database errors for troubleshooting and audit
purposes.

------------------------------------------------------------------------

## Reports

The Python engine produces a human-readable reconciliation report
containing:

``` text
FINANCE RECONCILIATION REPORT

Run ID
Date
Source File
Target File

SUMMARY

Total Source Records
Total Target Records
Matched
Duplicate in Source
Duplicate in Target
Missing in Target
Missing in Source
Amount Mismatch
Date Mismatch
Description Mismatch
Total Discrepancies
```

The report also contains detailed discrepancy information.

------------------------------------------------------------------------

## JSON Output

The JSON report contains structured information similar to:

``` json
{
  "run_id": "unique-run-id",
  "timestamp": "2026-08-12T10:00:00",
  "summary": {
    "total_source_records": 20,
    "total_target_records": 20,
    "matched_count": 20,
    "total_discrepancies": 0
  },
  "matches": []
}
```

The JSON format is used as the integration point between the Python
engine and n8n.

------------------------------------------------------------------------

## n8n Automation

The n8n workflow is responsible for orchestration rather than the core
reconciliation logic.

Typical workflow:

``` text
Daily Schedule
      ↓
Execute Command
      ↓
Check Result
      ↓
Read latest_reconciliation.json
      ↓
Extract JSON
      ↓
Check total_discrepancies
      ↓
   ┌──┴──┐
   │     │
  > 0    = 0
   │     │
   ▼     ▼
Alert   Success
Gmail   Gmail
   │     │
   └──┬──┘
      ▼
   Archive
```

### Why separate Python and n8n?

The architecture intentionally separates responsibilities:

**Python**

-   Data processing.
-   Validation.
-   Cleaning.
-   Reconciliation.
-   Database operations.
-   Report generation.

**n8n**

-   Scheduling.
-   Workflow orchestration.
-   Conditional branching.
-   File handling.
-   Email notifications.
-   Archiving.

This makes the Python reconciliation engine reusable independently from
the automation workflow.

------------------------------------------------------------------------

## Installation

### 1. Clone the repository

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd finance-reconciliation
```

### 2. Create a virtual environment

Windows:

``` powershell
python -m venv .venv
```

Activate it:

``` powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

The Python application requires packages including:

``` text
pandas
numpy
mysql-connector-python
PyYAML
openpyxl
```

`openpyxl` is required when Excel `.xlsx` files are used.

------------------------------------------------------------------------

## Configuration

Create or update `config.yaml`.

Example:

``` yaml
source_file: "data/source_transactions.csv"
target_file: "data/target_transactions.csv"

database:
  host: "localhost"
  port: 3306
  user: "root"
  password: "YOUR_PASSWORD"
  database: "finance_reconciliation"

amount_tolerance: 0.01
date_tolerance_days: 0

key_columns:
  - transaction_id
```

### Important

Never commit real database credentials.

For a public GitHub repository, use a placeholder configuration such as:

``` yaml
password: "YOUR_PASSWORD"
```

and keep the real configuration local or use environment
variables/secrets.

------------------------------------------------------------------------

## Database Setup

Create the database:

``` sql
CREATE DATABASE finance_reconciliation;
```

Then execute the SQL schema:

``` bash
mysql -u root -p finance_reconciliation < sql/schema.sql
```

The schema should create the tables required by the reconciliation
engine.

------------------------------------------------------------------------

## Running the Reconciliation Engine

The default execution is:

``` bash
python scripts/reconcile.py
```

The script reads:

``` text
config.yaml
```

by default.

### Custom configuration

``` bash
python scripts/reconcile.py --config config.yaml
```

### Override source file

``` bash
python scripts/reconcile.py --source data/source_transactions.csv
```

### Override target file

``` bash
python scripts/reconcile.py --target data/target_transactions.csv
```

### Save human-readable report

``` bash
python scripts/reconcile.py --output reports/reconciliation.txt
```

------------------------------------------------------------------------

## Execution Flow

Internally, the application follows this sequence:

``` text
Load Configuration
        ↓
Setup Logging
        ↓
Connect to MySQL
        ↓
Load Source Data
        ↓
Validate Source
        ↓
Clean Source
        ↓
Load Target Data
        ↓
Validate Target
        ↓
Clean Target
        ↓
Save Transactions to MySQL
        ↓
Reconcile Source vs Target
        ↓
Save Reconciliation Results
        ↓
Generate Summary
        ↓
Save Summary to MySQL
        ↓
Generate Human-Readable Report
        ↓
Generate JSON Report
        ↓
Close Database Connection
```

------------------------------------------------------------------------

## n8n Setup

Install and run n8n locally if required:

``` bash
n8n
```

The local editor is normally available at:

``` text
http://localhost:5678
```

Import the workflow JSON from:

``` text
n8n/workflow.json
```

Configure the workflow according to your local project path.

The `Execute Command` node must point to the Python interpreter in the
project's virtual environment and the reconciliation script.

Example on Windows:

``` powershell
C:\path\to\finance-reconciliation\.venv\Scripts\python.exe C:\path\to\finance-reconciliation\scripts\reconcile.py
```

Configure Gmail credentials in n8n before enabling email notifications.

------------------------------------------------------------------------

## Testing

The project should be tested using both successful and
failure/discrepancy scenarios.

### Test Case 1: No discrepancies

Expected:

``` text
total_discrepancies = 0
```

Expected automation:

``` text
Success Gmail notification
```

### Test Case 2: Discrepancies exist

Modify the target data to introduce differences.

Expected results may include:

``` text
duplicate_target
missing_in_source
amount_mismatch
date_mismatch
description_mismatch
```

Expected automation:

``` text
Discrepancy Gmail alert
```

### Why test both paths?

Testing both paths verifies that the workflow correctly handles:

-   The happy path.
-   The alert path.
-   JSON generation.
-   n8n conditional branching.
-   Gmail notification logic.

------------------------------------------------------------------------

## Example Workflow

Suppose the source contains:

``` text
TXN001 | 100.00
TXN002 | 200.00
TXN003 | 300.00
```

and the target contains:

``` text
TXN001 | 100.00
TXN002 | 250.00
TXN004 | 400.00
```

The reconciliation result becomes:

``` text
TXN001 → matched

TXN002 → amount_mismatch
           Source: 200.00
           Target: 250.00

TXN003 → missing_in_target

TXN004 → missing_in_source
```

Therefore:

``` text
Total discrepancies = 3
```

n8n detects that the discrepancy count is greater than zero and sends an
alert.

------------------------------------------------------------------------

## Error Handling and Logging

The application uses Python's `logging` module.

Logs contain:

-   Timestamp.
-   Logger name.
-   Log level.
-   Message.

Example levels:

``` text
INFO
WARNING
ERROR
```

The application also handles exceptions around the main reconciliation
workflow and ensures the database connection is closed in the cleanup
stage.

Database insertion errors can also be recorded in the `error_log` table.

------------------------------------------------------------------------

## Design Decisions

### 1. Why Pandas?

The input is structured tabular data, so Pandas provides convenient
DataFrame operations for:

-   Loading.
-   Cleaning.
-   Validation.
-   Duplicate detection.
-   Transformation.
-   Comparison.

### 2. Why MySQL?

CSV files are useful as input files but are not ideal for persistent
storage and historical auditing.

MySQL provides:

-   Persistent storage.
-   Querying.
-   Historical records.
-   Structured reconciliation results.
-   Auditability.

### 3. Why YAML?

Configuration is kept separate from application logic.

This allows file paths, database settings, key columns, and tolerances
to be changed without modifying Python code.

### 4. Why JSON?

JSON provides a structured machine-readable interface between the Python
engine and n8n.

### 5. Why n8n?

n8n handles orchestration tasks such as:

-   Scheduling.
-   Running the Python process.
-   Reading reports.
-   Conditional branching.
-   Sending notifications.
-   Archiving.

This keeps automation concerns separate from reconciliation business
logic.

------------------------------------------------------------------------

## Limitations

The current implementation is designed around Pandas DataFrames and
in-memory reconciliation.

For very large datasets, the complete dataset may not fit efficiently in
memory.

The current reconciliation strategy also maps transaction IDs to rows,
while duplicate IDs are detected separately. A more advanced
implementation could explicitly support one-to-many and many-to-many
transaction matching.

------------------------------------------------------------------------

## Future Improvements

Potential improvements include:

### API Layer

Expose reconciliation through FastAPI:

``` text
POST /reconcile
GET /reports/{run_id}
```

### Containerization

Dockerize:

``` text
Python application
MySQL
n8n
```

### Scalable Processing

For larger datasets:

-   Chunked Pandas processing.
-   SQL-side reconciliation.
-   Batch processing.
-   Distributed processing where appropriate.

### Monitoring

Add:

-   Prometheus.
-   Grafana.
-   Application health metrics.
-   Reconciliation success/failure metrics.

### Security

Improve credential management using:

-   Environment variables.
-   Secret managers.
-   n8n credentials.
-   Role-based database access.

### Dashboard

Build a dashboard showing:

-   Total reconciled transactions.
-   Match rate.
-   Discrepancy rate.
-   Amount mismatches.
-   Missing transactions.
-   Duplicate transactions.
-   Historical reconciliation trends.

------------------------------------------------------------------------

## Key Interview Talking Points

This project demonstrates experience with:

-   Python automation.
-   Pandas data processing.
-   Data validation.
-   Data cleaning.
-   SQL and MySQL.
-   ETL-style pipelines.
-   Reconciliation logic.
-   Duplicate detection.
-   Tolerance-based comparison.
-   JSON-based integration.
-   Workflow automation.
-   Conditional notifications.
-   Error handling.
-   Logging.
-   Auditability.
-   Git/GitHub.

### 30-Second Project Explanation

> I built an automated finance data reconciliation system that compares
> source and target transaction datasets using transaction IDs. The
> Python engine validates and cleans the data, detects duplicates,
> missing transactions, amount mismatches, date mismatches, and
> description mismatches, and stores the results in MySQL. It generates
> both human-readable and JSON reports. I integrated the engine with n8n
> so the process can run on a schedule, evaluate the discrepancy count,
> send Gmail alerts when issues are found, send success notifications
> when everything matches, and archive reports for historical tracking.

------------------------------------------------------------------------

## License

This project is intended for educational, portfolio, and demonstration
purposes.

If you reuse or extend the project, update this section with the license
you choose.
