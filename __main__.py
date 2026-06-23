import requests
import json
import pandas as pd
import re
import time
import logging
from datetime import datetime
from sqlalchemy import create_engine

import jdatetime          # pip install jdatetime


# ---------- تنظیمات لاگ ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("codal_job.log", encoding="utf-8"),
              logging.StreamHandler()]
)

header = {"user-agent": "Mozilla/5.0"}
valid_fields = [
    "درمان", "ثالث - اجباري", "ثالث - مازاد و ديه", "حوادث سرنشين", "بدنه خودرو",
    "آتش سوزي", "باربري", "مسئوليت", "مهندسي", "کشتي", "هواپيما",
    "نفت و انرژي", "حوادث", "اعتباري", "زندگي - اندوخته دار",
    "زندگي - غیر اندوخته دار", "پول", "ساير"
]


# ---------- توابع کمکی (بدون تغییر) ----------
def clean_text(text):
    if not isinstance(text, str): return ""
    mapping = {"ي": "ی", "ك": "ک", "‌": " "}
    for k, v in mapping.items():
        text = text.replace(k, v)
    return re.sub(r"\s+", " ", text).strip()


def extract_numeric(text):
    if text is None: return 0.0
    text = str(text).strip().replace(",", "")
    if text in [".", "-", "0", "۰", ""]: return 0.0
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    mapping = str.maketrans(persian_digits, english_digits)
    try:
        return float(text.translate(mapping))
    except:
        return 0.0


def clean_column_header(h1, h2, h3):
    h1 = h1.replace('از ابتدای سال مالی تا پایان مورخ', 'تجمعی').replace('دوره یک ماهه منتهی به', 'ماهانه')
    h1 = re.sub(r'\d{4}/\d{2}/\d{2}', '', h1)
    h1 = h1.replace('منتهی به', '').strip()
    combined = f"{h1}_{h2}_{h3}"
    clean_name = re.sub(r'[()| \-]', '_', combined)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    return clean_name


# ---------- محاسبه‌ی پویای بازه‌ی ماه قبل (شمسی) ----------
def get_previous_month_range():
    """
    بازه‌ی اولین روز تا آخرین روز «ماه جاری» شمسی را برمی‌گرداند.
    """
    today = jdatetime.date.today()
    from_date = jdatetime.date(today.year, today.month, 1)

    # محاسبه‌ی اولین روز ماه بعد، سپس یک روز عقب می‌رویم تا آخرین روز ماه جاری به دست آید
    if today.month == 12:
        first_of_next_month = jdatetime.date(today.year + 1, 1, 1)
    else:
        first_of_next_month = jdatetime.date(today.year, today.month + 1, 1)

    to_date = first_of_next_month - jdatetime.timedelta(days=1)

    return from_date.strftime("%Y/%m/%d"), to_date.strftime("%Y/%m/%d")


def build_search_url(from_date, to_date, page_number=1):
    fd = from_date.replace("/", "%2F")
    td = to_date.replace("/", "%2F")
    return (
        "https://search.codal.ir/api/search/v2/q?"
        "Audited=true&AuditorRef=-1&Category=3&Childs=true&CompanyState=-1"
        "&CompanyType=-1&Consolidatable=true"
        f"&FromDate={fd}&IsNotAudited=false&Length=-1&LetterType=-1"
        "&Mains=true&NotAudited=true&NotConsolidatable=true"
        f"&PageNumber={page_number}&Publisher=false&ReportingType=1000006"
        f"&ToDate={td}&TracingNo=-1&search=true"
    )


# ---------- منطق اصلی استخراج (هسته‌ی کد قبلی) ----------
def extract_reports(from_date, to_date):
    records = []
    page_number = 1

    while True:
        logging.info(f"Processing page {page_number} ({from_date} → {to_date})...")
        current_address = build_search_url(from_date, to_date, page_number)

        try:
            response = requests.get(current_address, headers=header, timeout=30)
            data = response.text.split('SuperVision":{')[1:]
        except Exception as e:
            logging.warning(f"Search request failed: {e}")
            break
        if not data:
            break

        for a in data:
            try:
                url_report = a.split('Url":"/Reports/Decision.')[1].split('"')[0]
                report_page = requests.get(
                    f'https://www.codal.ir/Reports/Decision.{url_report}',
                    headers=header, timeout=15).text

                company_name = report_page.split(
                    'ctl00_txbCompanyName" class="label" style="color:#C04000;">'
                )[1].split('</span>')[0].strip()

                url_report_req = report_page.split('datasource = ')[1].splitlines()[0][:-1]
                report_date = json.loads(url_report_req).get("periodEndToDate")
                sheet = json.loads(url_report_req)['sheets'][0]

                for table in sheet['tables']:
                    cells = table['cells']
                    temp_table_data = {}
                    for cell in cells:
                        addr = cell['address']
                        row_num = int(re.findall(r'\d+', addr)[0])
                        col_char = re.findall(r'[A-Z]+', addr)[0]
                        temp_table_data.setdefault(row_num, {})[col_char] = cell['value']

                    column_mapping = {}
                    h1_row = temp_table_data.get(1, {})
                    h2_row = temp_table_data.get(2, {})
                    h3_row = temp_table_data.get(3, {})
                    curr_h1, curr_h2 = "", ""

                    for col_idx in range(ord('B'), ord('Z') + 1):
                        char = chr(col_idx)
                        h1, h2, h3 = h1_row.get(char, ""), h2_row.get(char, ""), h3_row.get(char, "")
                        if h1: curr_h1 = h1
                        if h2: curr_h2 = h2
                        if curr_h1 or curr_h2 or h3:
                            column_mapping[char] = clean_column_header(curr_h1, curr_h2, h3)

                    last_field = ""
                    for row_idx in sorted(temp_table_data.keys()):
                        if row_idx < 4: continue
                        row_data = temp_table_data[row_idx]

                        field = clean_text(row_data.get("A", ""))
                        if field: last_field = field
                        if not last_field: continue

                        record = {
                            "شرکت": clean_text(company_name),
                            "دوره_گزارش": report_date,
                            "رشته_بیمه": last_field
                        }
                        for col_char, col_name in column_mapping.items():
                            record[col_name] = extract_numeric(row_data.get(col_char))
                        records.append(record)
            except Exception:
                continue
        page_number += 1

    return records


# ---------- پردازش، فیلتر و ذخیره ----------
def process_and_save(records, from_date):
    if not records:
        logging.warning("No records extracted. Skipping save.")
        return 0

    df = pd.DataFrame(records)

    normalized_valid = [clean_text(f) for f in valid_fields]
    df = df[df["رشته_بیمه"].isin(normalized_valid)]
    df = df[~df["رشته_بیمه"].str.contains("اتکایی", na=False)]

    non_data_cols = ["شرکت", "دوره_گزارش", "رشته_بیمه"]
    data_cols = [c for c in df.columns if c not in non_data_cols]
    active_data_cols = [c for c in data_cols if (df[c] != 0).any()]
    df = df[non_data_cols + active_data_cols]

    # برچسب ماه برای جلوگیری از بازنویسی داده‌های قبلی
    month_tag = from_date.replace("/", "_")

    # دیتابیس: داده‌ی هر اجرا append می‌شود (تاریخچه حفظ می‌شود)
    engine = create_engine("sqlite:///insurance_data.db")
    df.to_sql("InsuranceReports", con=engine, if_exists="replace", index=False)

    # اکسل مجزا برای هر ماه
    df.to_excel(f"insurance_report_{month_tag}.xlsx", index=False)

    logging.info(f"✅ Done. {len(df)} rows saved for period {from_date}.")
    return len(df)


# ---------- وظیفه‌ی اصلی که scheduler صدا می‌زند ----------
def monthly_job():
    try:
        from_date, to_date = get_previous_month_range()
        logging.info(f"=== Monthly job started for {from_date} → {to_date} ===")
        records = extract_reports(from_date, to_date)
        process_and_save(records, from_date)
    except Exception as e:
        logging.error(f"Monthly job failed: {e}", exc_info=True)


# ---------- زمان‌بندی ----------
if __name__ == "__main__":
    #if jdatetime.date.today().day == 10:
        monthly_job()
    #else:
        #logging.info("Not the 10th of the Jalali month. Skipping run.")

