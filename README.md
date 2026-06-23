# Automated Codal Insurance Reports Extraction System

A Python script for automated extraction, processing, and storage of monthly insurance company activity reports from [Codal](https://www.codal.ir). Data is filtered by valid insurance lines and saved to both SQLite database and Excel files.

## Features

- Automated extraction of insurance reports from Codal search API
- Dynamic date range calculation based on Jalali (Solar Hijri) calendar (current month)
- Persian text normalization and Persian numeral conversion
- Data filtering by valid insurance lines and removal of reinsurance rows
- Historical storage in SQLite and separate monthly Excel exports
- Scheduled execution on the 10th of each Jalali month (Task Scheduler compatible)
- Comprehensive operation logging

## Prerequisites

- Python 3.8 or higher

### Installation

```bash
pip install requests pandas sqlalchemy jdatetime openpyxl
```

## Usage

### Manual Execution

To run immediately without date condition, call `monthly_job()` directly:

```python
from codal_job import monthly_job

monthly_job()
```

### Scheduled Execution

```bash
python codal_job.py
```

The script executes only if the current day is the 10th of the Jalali month. Otherwise, it logs `Skipping run` and exits.

## Scheduling with Task Scheduler (Windows)

1. Open Task Scheduler and create a new task.
2. In the Action tab, set Program to `python.exe` and Arguments to the full path of `codal_job.py`.
3. **Important**: Set **Start in (WorkingDirectory)** to the script's folder so output files are created in the correct location.
4. Set the Trigger to run daily; the script's internal logic checks for the 10th day condition.

> **Note**: File paths (`codal_job.log`, `insurance_data.db`, `insurance_report_*.xlsx`) are relative. If WorkingDirectory is not set, files will be created in the default execution path.

## Output Files

| File | Description |
|------|-------------|
| `codal_job.log` | Complete operation log |
| `insurance_data.db` | SQLite database containing `InsuranceReports` table (historical data) |
| `insurance_report_YYYY_MM_DD.xlsx` | Separate Excel file for each monthly run |

## Data Structure

Each output row contains:

- `شرکت` (Company) — Insurance company name
- `دوره_گزارش` (Report Period) — End date of reporting period
- `رشته_بیمه` (Insurance Line) — Insurance line (health, third-party, vehicle body, etc.)
- Numeric columns for premiums and claims (monthly and cumulative)

## Supported Insurance Lines

Health (درمان), Third-Party Mandatory (ثالث - اجباری), Third-Party Excess (ثالث - مازاد و دیه), Passenger Accident (حوادث سرنشین), Vehicle Body (بدنه خودرو), Fire (آتش‌سوزی), Cargo (باربری), Liability (مسئولیت), Engineering (مهندسی), Marine Hull (کشتی), Aviation (هواپیما), Oil & Energy (نفت و انرژی), Accident (حوادث), Credit (اعتباری), Life Savings (زندگی - اندوخته‌دار), Life Non-Savings (زندگی - غیر اندوخته‌دار), Money (پول), Other (سایر).

## SQLite Schema

Data is saved with `append` mode to preserve history. If new column schema conflicts with existing table structure, an `OperationalError` will occur. In this case, delete `insurance_data.db` and re-run the script.

## License

This project is licensed under the MIT License.

---
