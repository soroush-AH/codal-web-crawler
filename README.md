# Codal Insurance Monthly Reports Scraper

This project is a Python script for extracting and transforming **monthly activity reports of insurance companies** from **Codal.ir**.  
The script fetches report listings from Codal's search API, opens each report page, extracts tabular data from the embedded JSON datasource, cleans and normalizes the data, and finally exports the results to both **SQLite** and **Excel** formats.

---

## Features

- Fetches report listings from `search.codal.ir`
- Filters reports using `ReportingType=1000006` (monthly activity reports)
- Iterates through paginated API results using `PageNumber`
- Opens each individual report page and extracts the `datasource` JSON from the HTML
- Parses tables from `sheets[0].tables[*].cells`
- Builds meaningful column names by combining 3 header rows
- Converts Persian digits to English digits
- Safely converts extracted values to numeric format
- Normalizes Persian text (character unification, half-space removal, whitespace cleanup)
- Keeps only selected insurance categories defined in `valid_fields`
- Removes rows containing `اتکايي`
- Drops columns that contain only zeros, except protected columns
- Saves the final result to:
  - `insurance_data.db` (SQLite)
  - `insurance_final_report.xlsx` (Excel)

---

## Outputs

### 1. SQLite
Database file:
- `insurance_data.db`

Table name:
- `InsuranceReports`

Write mode:
- `if_exists="replace"`  
  Each run replaces the previous table.

### 2. Excel
Excel file:
- `insurance_final_report.xlsx`

---

## Data Structure

Each extracted record includes these main fields:

- `شرکت` — Company name
- `تاریخ_انتشار` — Report publish date
- `رشته_بیمه` — Insurance category / field

In addition, multiple numeric columns are generated dynamically from the report table headers, such as issued premium, paid خسارت, and other monthly/cumulative metrics.

---

## Requirements

- Python 3.9+ recommended

### Dependencies

- `requests`
- `pandas`
- `sqlalchemy`

Install them using:
```bash
pip install requests pandas sqlalchemy
