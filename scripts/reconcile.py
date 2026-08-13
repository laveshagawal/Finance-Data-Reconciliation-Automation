"""
Finance Data Reconciliation Automation
Main script for cleaning, validating, and reconciling transaction data from two CSV/Excel files.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import uuid
import json
import logging
import sys
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import yaml


@dataclass
class ReconciliationConfig:
    """Configuration for reconciliation process."""
    source_file: str
    target_file: str
    db_config: Dict[str, Any]
    amount_tolerance: float = 0.01
    date_tolerance_days: int = 0
    key_columns: List[str] = None

    def __post_init__(self):
        if self.key_columns is None:
            self.key_columns = ['transaction_id']


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class ReconciliationMatch:
    """Represents a reconciliation match result."""
    source_id: Optional[int]
    target_id: Optional[int]
    match_type: str
    source_amount: Optional[float]
    target_amount: Optional[float]
    difference: Optional[float]
    details: Dict[str, Any]


class DataValidator:
    """Validates transaction data."""

    REQUIRED_COLUMNS = ['transaction_id', 'date', 'amount']
    OPTIONAL_COLUMNS = [
        'description',
        'category',
        'account',
        'reference',
        'status'
    ]
    VALID_STATUSES = ['pending', 'cleared', 'failed']

    def __init__(self, config: ReconciliationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str
    ) -> ValidationResult:
        """Validate a transaction dataframe."""

        errors = []
        warnings = []

        # Check required columns
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)

        if missing_cols:
            errors.append(
                f"{source_name}: Missing required columns: {missing_cols}"
            )

        # Check for empty dataframe
        if df.empty:
            errors.append(f"{source_name}: DataFrame is empty")
            return ValidationResult(False, errors, warnings)

        # Validate each row
        for idx, row in df.iterrows():
            row_errors, row_warnings = self._validate_row(
                row,
                idx,
                source_name
            )

            errors.extend(row_errors)
            warnings.extend(row_warnings)

        # Check for duplicate transaction_ids
        duplicates = df[
            df.duplicated(
                subset=['transaction_id'],
                keep=False
            )
        ]

        if not duplicates.empty:
            for _, dup_row in duplicates.iterrows():
                warnings.append(
                    f"{source_name}: Row {dup_row.name}: "
                    f"Duplicate transaction_id "
                    f"'{dup_row['transaction_id']}'"
                )

        return ValidationResult(
            len(errors) == 0,
            errors,
            warnings
        )

    def _validate_row(
        self,
        row: pd.Series,
        idx: int,
        source_name: str
    ) -> Tuple[List[str], List[str]]:
        """Validate a single row."""

        errors = []
        warnings = []

        prefix = f"{source_name}: Row {idx}"

        # Validate transaction_id
        if (
            pd.isna(row.get('transaction_id'))
            or str(row['transaction_id']).strip() == ''
        ):
            errors.append(
                f"{prefix}: Missing transaction_id"
            )

        # Validate date
        date_val = row.get('date')

        if pd.isna(date_val):
            errors.append(f"{prefix}: Missing date")
        else:
            try:
                pd.to_datetime(date_val)
            except Exception:
                errors.append(
                    f"{prefix}: Invalid date format: {date_val}"
                )

        # Validate amount
        amount_val = row.get('amount')

        if pd.isna(amount_val):
            errors.append(f"{prefix}: Missing amount")
        else:
            try:
                float(amount_val)
            except Exception:
                errors.append(
                    f"{prefix}: Invalid amount: {amount_val}"
                )

        # Validate status if present
        status = row.get('status')

        if (
            not pd.isna(status)
            and status not in self.VALID_STATUSES
        ):
            warnings.append(
                f"{prefix}: Invalid status '{status}', "
                f"using 'pending'"
            )

        return errors, warnings

    def clean_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str
    ) -> pd.DataFrame:
        """Clean and standardize dataframe."""

        df = df.copy()

        # Standardize column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        # Ensure required and optional columns exist
        for col in self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS:
            if col not in df.columns:
                df[col] = np.nan

        # Clean transaction_id
        df['transaction_id'] = (
            df['transaction_id']
            .astype(str)
            .str.strip()
        )

        # Parse dates
        df['date'] = (
            pd.to_datetime(
                df['date'],
                errors='coerce'
            ).dt.date
        )

        # Clean amounts
        df['amount'] = pd.to_numeric(
            df['amount'],
            errors='coerce'
        )

        # Clean optional string columns
        for col in [
            'description',
            'category',
            'account',
            'reference'
        ]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                )

                df[col] = df[col].replace(
                    'nan',
                    np.nan
                )

        # Standardize status
        if 'status' in df.columns:
            df['status'] = (
                df['status']
                .astype(str)
                .str.strip()
                .str.lower()
            )

            df['status'] = df['status'].apply(
                lambda x:
                    x
                    if x in self.VALID_STATUSES
                    else 'pending'
            )

        # Remove rows with missing required fields
        initial_len = len(df)

        df = df.dropna(
            subset=self.REQUIRED_COLUMNS
        )

        if len(df) < initial_len:
            self.logger.warning(
                f"{source_name}: Removed "
                f"{initial_len - len(df)} rows "
                f"with missing required fields"
            )

        return df.reset_index(drop=True)


class ReconciliationEngine:
    """Core reconciliation logic."""

    def __init__(
        self,
        config: ReconciliationConfig
    ):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self.run_id = str(uuid.uuid4())[:8]

        self.validator = DataValidator(config)

        self.db_connection = None

    def connect_db(self) -> bool:
        """Establish database connection."""

        try:
            self.db_connection = mysql.connector.connect(
                **self.config.db_config
            )

            self.logger.info(
                "Database connection established"
            )

            return True

        except Error as e:
            self.logger.error(
                f"Database connection failed: {e}"
            )

            return False

    def close_db(self):
        """Close database connection."""

        if (
            self.db_connection
            and self.db_connection.is_connected()
        ):
            self.db_connection.close()

            self.logger.info(
                "Database connection closed"
            )

    def load_file(
        self,
        file_path: str
    ) -> pd.DataFrame:
        """Load CSV or Excel file."""

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        if path.suffix.lower() == '.csv':
            return pd.read_csv(file_path)

        elif path.suffix.lower() in [
            '.xlsx',
            '.xls'
        ]:
            return pd.read_excel(file_path)

        else:
            raise ValueError(
                f"Unsupported file format: "
                f"{path.suffix}"
            )

    def save_to_database(
        self,
        df: pd.DataFrame,
        table_name: str,
        source_file: str
    ) -> List[int]:
        """Save cleaned transactions to database."""

        if (
            not self.db_connection
            or not self.db_connection.is_connected()
        ):
            raise Error("Database not connected")

        cursor = self.db_connection.cursor()

        inserted_ids = []

        insert_query = f"""
            INSERT INTO {table_name}
            (
                transaction_id,
                date,
                amount,
                description,
                category,
                account,
                reference,
                status,
                source_file
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                date=VALUES(date),
                amount=VALUES(amount),
                description=VALUES(description),
                category=VALUES(category),
                account=VALUES(account),
                reference=VALUES(reference),
                status=VALUES(status),
                updated_at=CURRENT_TIMESTAMP
        """

        for _, row in df.iterrows():

            try:
                cursor.execute(
                    insert_query,
                    (
                        row['transaction_id'],
                        row['date'],
                        float(row['amount']),
                        (
                            row.get('description')
                            if not pd.isna(
                                row.get('description')
                            )
                            else None
                        ),
                        (
                            row.get('category')
                            if not pd.isna(
                                row.get('category')
                            )
                            else None
                        ),
                        (
                            row.get('account')
                            if not pd.isna(
                                row.get('account')
                            )
                            else None
                        ),
                        (
                            row.get('reference')
                            if not pd.isna(
                                row.get('reference')
                            )
                            else None
                        ),
                        row.get(
                            'status',
                            'pending'
                        ),
                        source_file
                    )
                )

                inserted_ids.append(
                    cursor.lastrowid
                )

            except Error as e:

                self.logger.error(
                    f"Failed to insert row "
                    f"{row['transaction_id']}: {e}"
                )

                self._log_error(
                    self.run_id,
                    source_file,
                    row.name,
                    'database',
                    str(e),
                    row.to_dict()
                )

        self.db_connection.commit()

        cursor.close()

        return inserted_ids

    def _log_error(
        self,
        run_id: str,
        source_file: str,
        row_num: int,
        error_type: str,
        message: str,
        raw_data: Dict
    ):
        """Log error to database."""

        if (
            not self.db_connection
            or not self.db_connection.is_connected()
        ):
            return

        try:
            cursor = self.db_connection.cursor()

            cursor.execute(
                """
                INSERT INTO error_log
                (
                    run_id,
                    source_file,
                    row_number,
                    error_type,
                    error_message,
                    raw_data
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    source_file,
                    row_num,
                    error_type,
                    message,
                    json.dumps(
                        raw_data,
                        default=str
                    )
                )
            )

            self.db_connection.commit()

            cursor.close()

        except Error:
            pass

    def load_from_database(
        self,
        table_name: str,
        source_file: str
    ) -> pd.DataFrame:
        """Load transactions from database."""

        if (
            not self.db_connection
            or not self.db_connection.is_connected()
        ):
            raise Error("Database not connected")

        query = (
            f"SELECT * FROM {table_name} "
            f"WHERE source_file = %s"
        )

        return pd.read_sql(
            query,
            self.db_connection,
            params=(source_file,)
        )

    def reconcile(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame
    ) -> List[ReconciliationMatch]:
        """Perform reconciliation."""

        matches = []

        key_col = self.config.key_columns[0]

        # Create lookup dictionaries
        source_dict = {
            row[key_col]: row
            for _, row in source_df.iterrows()
        }

        target_dict = {
            row[key_col]: row
            for _, row in target_df.iterrows()
        }

        all_keys = (
            set(source_dict.keys())
            | set(target_dict.keys())
        )

        for key in all_keys:

            source_row = source_dict.get(key)

            target_row = target_dict.get(key)

            if (
                source_row is not None
                and target_row is not None
            ):
                # Both exist
                match = self._compare_rows(
                    source_row,
                    target_row,
                    key
                )

                matches.append(match)

            elif source_row is not None:
                # Only in source
                matches.append(
                    ReconciliationMatch(
                        source_id=(
                            int(source_row.name)
                            if hasattr(
                                source_row,
                                'name'
                            )
                            else None
                        ),
                        target_id=None,
                        match_type='missing_in_target',
                        source_amount=float(
                            source_row['amount']
                        ),
                        target_amount=None,
                        difference=None,
                        details={
                            'transaction_id': key,
                            'source_date': str(
                                source_row['date']
                            )
                        }
                    )
                )

            else:
                # Only in target
                matches.append(
                    ReconciliationMatch(
                        source_id=None,
                        target_id=(
                            int(target_row.name)
                            if hasattr(
                                target_row,
                                'name'
                            )
                            else None
                        ),
                        match_type='missing_in_source',
                        source_amount=None,
                        target_amount=float(
                            target_row['amount']
                        ),
                        difference=None,
                        details={
                            'transaction_id': key,
                            'target_date': str(
                                target_row['date']
                            )
                        }
                    )
                )

        # Check duplicates in source
        source_dupes = source_df[
            source_df.duplicated(
                subset=[key_col],
                keep=False
            )
        ]

        for _, row in source_dupes.iterrows():

            matches.append(
                ReconciliationMatch(
                    source_id=(
                        int(row.name)
                        if hasattr(row, 'name')
                        else None
                    ),
                    target_id=None,
                    match_type='duplicate_source',
                    source_amount=float(
                        row['amount']
                    ),
                    target_amount=None,
                    difference=None,
                    details={
                        'transaction_id':
                            row[key_col],
                        'count':
                            source_dupes[
                                source_dupes[key_col]
                                == row[key_col]
                            ].shape[0]
                    }
                )
            )

        # Check duplicates in target
        target_dupes = target_df[
            target_df.duplicated(
                subset=[key_col],
                keep=False
            )
        ]

        for _, row in target_dupes.iterrows():

            matches.append(
                ReconciliationMatch(
                    source_id=None,
                    target_id=(
                        int(row.name)
                        if hasattr(row, 'name')
                        else None
                    ),
                    match_type='duplicate_target',
                    source_amount=None,
                    target_amount=float(
                        row['amount']
                    ),
                    difference=None,
                    details={
                        'transaction_id':
                            row[key_col],
                        'count':
                            target_dupes[
                                target_dupes[key_col]
                                == row[key_col]
                            ].shape[0]
                    }
                )
            )

        return matches

    def _compare_rows(
        self,
        source_row: pd.Series,
        target_row: pd.Series,
        key: str
    ) -> ReconciliationMatch:
        """Compare two rows."""

        source_amount = float(
            source_row['amount']
        )

        target_amount = float(
            target_row['amount']
        )

        amount_diff = abs(
            source_amount - target_amount
        )

        source_date = pd.to_datetime(
            source_row['date']
        )

        target_date = pd.to_datetime(
            target_row['date']
        )

        date_diff = abs(
            (source_date - target_date).days
        )

        source_desc = str(
            source_row.get(
                'description',
                ''
            )
        ).strip().lower()

        target_desc = str(
            target_row.get(
                'description',
                ''
            )
        ).strip().lower()

        # Determine match type
        if (
            amount_diff
            <= self.config.amount_tolerance
            and date_diff
            <= self.config.date_tolerance_days
        ):

            if (
                source_desc == target_desc
                or not source_desc
                or not target_desc
            ):
                match_type = 'matched'

            else:
                match_type = 'description_mismatch'

        elif amount_diff > self.config.amount_tolerance:

            match_type = 'amount_mismatch'

        elif date_diff > self.config.date_tolerance_days:

            match_type = 'date_mismatch'

        else:

            match_type = 'matched'

        return ReconciliationMatch(
            source_id=(
                int(source_row.name)
                if hasattr(
                    source_row,
                    'name'
                )
                else None
            ),
            target_id=(
                int(target_row.name)
                if hasattr(
                    target_row,
                    'name'
                )
                else None
            ),
            match_type=match_type,
            source_amount=source_amount,
            target_amount=target_amount,
            difference=(
                round(
                    source_amount
                    - target_amount,
                    2
                )
                if match_type
                == 'amount_mismatch'
                else None
            ),
            details={
                'transaction_id': key,
                'source_date':
                    str(source_row['date']),
                'target_date':
                    str(target_row['date']),
                'source_description':
                    source_row.get(
                        'description'
                    ),
                'target_description':
                    target_row.get(
                        'description'
                    ),
                'amount_diff':
                    round(
                        amount_diff,
                        2
                    ),
                'date_diff_days':
                    date_diff
            }
        )

    def save_reconciliation_results(
        self,
        matches: List[ReconciliationMatch]
    ):
        """Save reconciliation results."""

        if (
            not self.db_connection
            or not self.db_connection.is_connected()
        ):
            raise Error("Database not connected")

        cursor = self.db_connection.cursor()

        insert_query = """
            INSERT INTO reconciliation_results
            (
                run_id,
                source_transaction_id,
                target_transaction_id,
                match_type,
                source_amount,
                target_amount,
                difference,
                details
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
        """

        for match in matches:

            try:

                cursor.execute(
                    insert_query,
                    (
                        self.run_id,
                        match.source_id,
                        match.target_id,
                        match.match_type,
                        match.source_amount,
                        match.target_amount,
                        match.difference,
                        json.dumps(
                            match.details,
                            default=str
                        )
                    )
                )

            except Error as e:

                self.logger.error(
                    f"Failed to save match result: {e}"
                )

        self.db_connection.commit()

        cursor.close()

    def generate_summary(
        self,
        matches: List[ReconciliationMatch],
        source_count: int,
        target_count: int
    ) -> Dict:
        """Generate reconciliation summary."""

        summary = {
            'run_id': self.run_id,
            'total_source_records': source_count,
            'total_target_records': target_count,
            'matched_count': 0,
            'duplicate_source_count': 0,
            'duplicate_target_count': 0,
            'missing_in_target_count': 0,
            'missing_in_source_count': 0,
            'amount_mismatch_count': 0,
            'date_mismatch_count': 0,
            'description_mismatch_count': 0,
            'total_discrepancies': 0
        }

        for match in matches:

            if match.match_type == 'matched':
                summary['matched_count'] += 1

            elif match.match_type == 'duplicate_source':
                summary['duplicate_source_count'] += 1

            elif match.match_type == 'duplicate_target':
                summary['duplicate_target_count'] += 1

            elif match.match_type == 'missing_in_target':
                summary['missing_in_target_count'] += 1

            elif match.match_type == 'missing_in_source':
                summary['missing_in_source_count'] += 1

            elif match.match_type == 'amount_mismatch':
                summary['amount_mismatch_count'] += 1

            elif match.match_type == 'date_mismatch':
                summary['date_mismatch_count'] += 1

            elif match.match_type == 'description_mismatch':
                summary['description_mismatch_count'] += 1

        summary['total_discrepancies'] = (
            summary['duplicate_source_count']
            + summary['duplicate_target_count']
            + summary['missing_in_target_count']
            + summary['missing_in_source_count']
            + summary['amount_mismatch_count']
            + summary['date_mismatch_count']
            + summary['description_mismatch_count']
        )

        return summary

    def save_summary(
        self,
        summary: Dict
    ):
        """Save reconciliation summary to database."""

        if (
            not self.db_connection
            or not self.db_connection.is_connected()
        ):
            return

        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            INSERT INTO reconciliation_summary
            (
                run_id,
                source_file,
                target_file,
                total_source_records,
                total_target_records,
                matched_count,
                duplicate_source_count,
                duplicate_target_count,
                missing_in_target_count,
                missing_in_source_count,
                amount_mismatch_count,
                date_mismatch_count,
                description_mismatch_count,
                error_count,
                status,
                completed_at
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                total_source_records =
                    VALUES(total_source_records),
                total_target_records =
                    VALUES(total_target_records),
                matched_count =
                    VALUES(matched_count),
                duplicate_source_count =
                    VALUES(duplicate_source_count),
                duplicate_target_count =
                    VALUES(duplicate_target_count),
                missing_in_target_count =
                    VALUES(missing_in_target_count),
                missing_in_source_count =
                    VALUES(missing_in_source_count),
                amount_mismatch_count =
                    VALUES(amount_mismatch_count),
                date_mismatch_count =
                    VALUES(date_mismatch_count),
                description_mismatch_count =
                    VALUES(description_mismatch_count),
                error_count =
                    VALUES(error_count),
                status =
                    VALUES(status),
                completed_at =
                    VALUES(completed_at)
            """,
            (
                summary['run_id'],
                self.config.source_file,
                self.config.target_file,
                summary['total_source_records'],
                summary['total_target_records'],
                summary['matched_count'],
                summary['duplicate_source_count'],
                summary['duplicate_target_count'],
                summary['missing_in_target_count'],
                summary['missing_in_source_count'],
                summary['amount_mismatch_count'],
                summary['date_mismatch_count'],
                summary['description_mismatch_count'],
                0,
                'completed',
                datetime.now()
            )
        )

        self.db_connection.commit()

        cursor.close()

    def generate_report(
        self,
        matches: List[ReconciliationMatch],
        summary: Dict
    ) -> str:
        """Generate human-readable reconciliation report."""

        report_lines = [
            "=" * 80,
            "FINANCE RECONCILIATION REPORT",
            "=" * 80,
            f"Run ID: {self.run_id}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source File: {self.config.source_file}",
            f"Target File: {self.config.target_file}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Source Records:     "
            f"{summary['total_source_records']:>6}",
            f"Total Target Records:     "
            f"{summary['total_target_records']:>6}",
            f"Matched:                  "
            f"{summary['matched_count']:>6}",
            f"Duplicate in Source:      "
            f"{summary['duplicate_source_count']:>6}",
            f"Duplicate in Target:      "
            f"{summary['duplicate_target_count']:>6}",
            f"Missing in Target:        "
            f"{summary['missing_in_target_count']:>6}",
            f"Missing in Source:        "
            f"{summary['missing_in_source_count']:>6}",
            f"Amount Mismatch:          "
            f"{summary['amount_mismatch_count']:>6}",
            f"Date Mismatch:            "
            f"{summary['date_mismatch_count']:>6}",
            f"Description Mismatch:     "
            f"{summary['description_mismatch_count']:>6}",
            f"Total Discrepancies:      "
            f"{summary['total_discrepancies']:>6}",
            "",
            "DETAILED DISCREPANCIES",
            "-" * 40,
        ]

        # Group by match type
        discrepancies = [
            m for m in matches
            if m.match_type != 'matched'
        ]

        if not discrepancies:

            report_lines.append(
                "No discrepancies found. "
                "All transactions matched!"
            )

        else:

            for match_type in [
                'duplicate_source',
                'duplicate_target',
                'missing_in_target',
                'missing_in_source',
                'amount_mismatch',
                'date_mismatch',
                'description_mismatch'
            ]:

                type_matches = [
                    m for m in discrepancies
                    if m.match_type == match_type
                ]

                if type_matches:

                    report_lines.append(
                        f"\n"
                        f"{match_type.upper().replace('_', ' ')} "
                        f"({len(type_matches)}):"
                    )

                    for m in type_matches[:10]:

                        details = m.details

                        report_lines.append(
                            f"  TXN: "
                            f"{details.get('transaction_id', 'N/A')}"
                        )

                        if (
                            m.match_type
                            == 'amount_mismatch'
                        ):

                            report_lines.append(
                                f"    Source: "
                                f"${m.source_amount:,.2f} | "
                                f"Target: "
                                f"${m.target_amount:,.2f} | "
                                f"Diff: "
                                f"${m.difference:,.2f}"
                            )

                        elif (
                            m.match_type
                            == 'date_mismatch'
                        ):

                            report_lines.append(
                                f"    Source Date: "
                                f"{details.get('source_date')} | "
                                f"Target Date: "
                                f"{details.get('target_date')} | "
                                f"Diff: "
                                f"{details.get('date_diff_days')} days"
                            )

                        elif (
                            m.match_type
                            == 'description_mismatch'
                        ):

                            report_lines.append(
                                f"    Source: "
                                f"{details.get('source_description')}"
                            )

                            report_lines.append(
                                f"    Target: "
                                f"{details.get('target_description')}"
                            )

                        else:

                            report_lines.append(
                                f"    Amount: "
                                f"${m.source_amount or m.target_amount:,.2f} "
                                f"| Date: "
                                f"{details.get('source_date') or details.get('target_date')}"
                            )

                    if len(type_matches) > 10:

                        report_lines.append(
                            f"  ... and "
                            f"{len(type_matches) - 10} more"
                        )

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)


def load_config(
    config_path: str
) -> ReconciliationConfig:
    """Load configuration from YAML file."""

    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    return ReconciliationConfig(
        source_file=config_data['source_file'],
        target_file=config_data['target_file'],
        db_config=config_data['database'],
        amount_tolerance=config_data.get(
            'amount_tolerance',
            0.01
        ),
        date_tolerance_days=config_data.get(
            'date_tolerance_days',
            0
        ),
        key_columns=config_data.get(
            'key_columns',
            ['transaction_id']
        )
    )


def setup_logging(
    log_file: str = None
):
    """Setup logging configuration."""

    handlers = [
        logging.StreamHandler(sys.stdout)
    ]

    if log_file:
        handlers.append(
            logging.FileHandler(log_file)
        )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s - '
            '%(name)s - '
            '%(levelname)s - '
            '%(message)s'
        ),
        handlers=handlers
    )


def main():
    """Main reconciliation workflow."""

    import argparse

    parser = argparse.ArgumentParser(
        description='Finance Data Reconciliation'
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file'
    )

    parser.add_argument(
        '--source',
        help='Source file path (overrides config)'
    )

    parser.add_argument(
        '--target',
        help='Target file path (overrides config)'
    )

    parser.add_argument(
        '--output',
        help='Report output file'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(
        args.config
    )

    if args.source:
        config.source_file = args.source

    if args.target:
        config.target_file = args.target

    setup_logging(
        'reconciliation.log'
    )

    logger = logging.getLogger(
        __name__
    )

    logger.info(
        "Starting reconciliation run"
    )

    logger.info(
        f"Source: {config.source_file}"
    )

    logger.info(
        f"Target: {config.target_file}"
    )

    # Initialize engine
    engine = ReconciliationEngine(
        config
    )

    try:

        # Connect to database
        if not engine.connect_db():

            logger.error(
                "Failed to connect to database. "
                "Exiting."
            )

            return 1

        # Load and validate source data
        logger.info(
            "Loading source data..."
        )

        source_raw = engine.load_file(
            config.source_file
        )

        source_validation = (
            engine.validator.validate_dataframe(
                source_raw,
                'Source'
            )
        )

        if not source_validation.is_valid:

            for err in source_validation.errors:

                logger.error(
                    f"Source validation error: {err}"
                )

            logger.error(
                "Source validation failed. "
                "Exiting."
            )

            return 1

        for warn in source_validation.warnings:

            logger.warning(warn)

        # Clean source
        source_clean = (
            engine.validator.clean_dataframe(
                source_raw,
                'Source'
            )
        )

        logger.info(
            f"Source: "
            f"{len(source_clean)} "
            f"valid records after cleaning"
        )

        # Load and validate target data
        logger.info(
            "Loading target data..."
        )

        target_raw = engine.load_file(
            config.target_file
        )

        target_validation = (
            engine.validator.validate_dataframe(
                target_raw,
                'Target'
            )
        )

        if not target_validation.is_valid:

            for err in target_validation.errors:

                logger.error(
                    f"Target validation error: {err}"
                )

            logger.error(
                "Target validation failed. "
                "Exiting."
            )

            return 1

        for warn in target_validation.warnings:

            logger.warning(warn)

        # Clean target
        target_clean = (
            engine.validator.clean_dataframe(
                target_raw,
                'Target'
            )
        )

        logger.info(
            f"Target: "
            f"{len(target_clean)} "
            f"valid records after cleaning"
        )

        # Save to database
        logger.info(
            "Saving to database..."
        )

        engine.save_to_database(
            source_clean,
            'source_transactions',
            config.source_file
        )

        engine.save_to_database(
            target_clean,
            'target_transactions',
            config.target_file
        )

        # Perform reconciliation
        logger.info(
            "Performing reconciliation..."
        )

        matches = engine.reconcile(
            source_clean,
            target_clean
        )

        # Save results
        logger.info(
            "Saving reconciliation results..."
        )

        engine.save_reconciliation_results(
            matches
        )

        # Generate summary
        summary = engine.generate_summary(
            matches,
            len(source_clean),
            len(target_clean)
        )

        engine.save_summary(
            summary
        )

        # Generate human-readable report
        report = engine.generate_report(
            matches,
            summary
        )

        print(report)

        if args.output:

            with open(
                args.output,
                'w'
            ) as f:

                f.write(report)

            logger.info(
                f"Report saved to {args.output}"
            )

        # -------------------------------------------------
        # SAVE JSON REPORTS
        # -------------------------------------------------

        json_report = {
            'run_id': engine.run_id,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'matches': [
                asdict(m)
                for m in matches
            ]
        }

        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # Save unique historical report
        json_file = (
            reports_dir
            / f"reconciliation_{engine.run_id}.json"
        )

        with open(
            json_file,
            'w'
        ) as f:

            json.dump(
                json_report,
                f,
                indent=2,
                default=str
            )

        logger.info(
            f"JSON report saved to {json_file}"
        )

        # Save latest report for n8n
        latest_file = (
            reports_dir
            / "latest_reconciliation.json"
        )

        with open(
            latest_file,
            'w'
        ) as f:

            json.dump(
                json_report,
                f,
                indent=2,
                default=str
            )

        logger.info(
            f"Latest JSON report saved to {latest_file}"
        )

        logger.info(
            "Reconciliation completed successfully!"
        )

        return 0

    except Exception as e:

        logger.exception(
            f"Reconciliation failed: {e}"
        )

        return 1

    finally:

        engine.close_db()


if __name__ == '__main__':
    sys.exit(main())