import requests
import json
import pandas as pd
import re
from sqlalchemy import create_engine

header = {"user-agent": "Mozilla/5.0"}
records = []

valid_fields = [
    "درمان", "ثالث - اجباري", "ثالث - مازاد و ديه", "حوادث سرنشين", "بدنه خودرو",
    "آتش سوزي", "باربري", "مسئوليت", "مهندسي", "کشتي", "هواپيما",
    "نفت و انرژي", "حوادث", "اعتباري", "زندگي - اندوخته دار",
    "زندگي - غیر اندوخته دار", "پول", "ساير"
]


def convert_persian_to_english_numbers(text):
    if text is None or not isinstance(text, str):
        return text
    text = text.strip().replace(",", "")
    if text in [".", "-", "0", "۰"]: return "0"

    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    english_digits = "0123456789"
    mapping = str.maketrans(persian_digits, english_digits)
    return text.translate(mapping)


def safe_float_conversion(value):
    try:
        if value is None: return 0.0
        return float(value)
    except:
        return 0.0


def normalize_text(text):
    if not isinstance(text, str):
        return text
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = text.replace("‌", " ")  # حذف نیم فاصله
    text = re.sub(r"\s+", " ", text)
    return text.strip()



page_number = 1
while True:
    print(f"Processing page {page_number}")
    address = f"https://search.codal.ir/api/search/v2/q?Audited=true&AuditorRef=-1&Category=3&Childs=true&CompanyState=-1&CompanyType=-1&Consolidatable=true&FromDate=1405%2F01%2F01&IsNotAudited=false&Length=-1&LetterType=-1&Mains=true&NotAudited=true&NotConsolidatable=true&PageNumber={page_number}&Publisher=false&ReportingType=1000006&ToDate=1405%2F01%2F31&TracingNo=-1&search=true"

    try:
        response = requests.get(address, headers=header)
        data = response.text.split('SuperVision":{')[1:]
    except:
        break

    if len(data) == 0: break

    for a in data:
        try:
            url_report = a.split('Url":"/Reports/Decision.')[1].split('"')[0]
            report_page = requests.get(f'https://www.codal.ir/Reports/Decision.{url_report}', headers=header).text

            company_name = report_page.split('ctl00_txbCompanyName" class="label" style="color:#C04000;">')[1].split('</span>')[0].strip()
            url_report_req = report_page.split('datasource = ')[1].splitlines()[0][:-1]
            date = json.loads(url_report_req).get("publishDateTime")
            sheet = json.loads(url_report_req)['sheets'][0]
            report_period_fa = sheet.get('title_Fa', 'نامشخص')

            for table in sheet['tables']:
                cells = table['cells']
                temp_table_data = {}
                for cell_data in cells:
                    addr = cell_data['address']
                    val = cell_data['value']
                    row_num = int(re.findall(r'\d+', addr)[0])
                    col_char = re.findall(r'[A-Z]+', addr)[0]
                    if row_num not in temp_table_data: temp_table_data[row_num] = {}
                    temp_table_data[row_num][col_char] = val


                header_row_1 = temp_table_data.get(1, {})
                header_row_2 = temp_table_data.get(2, {})
                header_row_3 = temp_table_data.get(3, {})

                column_mapping = {}
                curr_h1, curr_h2 = "", ""

                for col_char_code in range(ord('B'), ord('Z') + 1):
                    col_char = chr(col_char_code)

                    h1 = header_row_1.get(col_char, "").strip()
                    h2 = header_row_2.get(col_char, "").strip()
                    h3 = header_row_3.get(col_char, "").strip()

                    if h1: curr_h1 = h1
                    if h2: curr_h2 = h2

                    if curr_h1 or curr_h2 or h3:
                        clean_h1 = curr_h1.replace('از ابتدای سال مالی تا پایان مورخ', 'تجمعی').replace(
                            'دوره یک ماهه منتهی به', 'ماهانه')
                        full_name = (f"{clean_h1}_{curr_h2}_{h3}".
                                     replace(" | ", "_").
                                     replace("(", "").replace(")","").
                                     replace(" ", "_").replace("-", "_"))
                        column_mapping[col_char] = f"{full_name}"

                        column_mapping[col_char] = full_name

                last_insurance_field = ""

                for row_num in sorted(temp_table_data.keys()):
                    if row_num < 4: continue

                    row_data = temp_table_data[row_num]

                    current_field = row_data.get("A", "").strip()

                    if current_field:
                        last_insurance_field = current_field

                    insurance_field = last_insurance_field

                    if not insurance_field:
                        continue

                    record = {
                        "شرکت": company_name,
                        "تاریخ_انتشار": date,
                        "رشته_بیمه": insurance_field
                    }

                    for col_char, col_name in column_mapping.items():
                        raw_val = row_data.get(col_char)
                        clean_val = convert_persian_to_english_numbers(raw_val)
                        record[col_name] = safe_float_conversion(clean_val)

                    records.append(record)

        except:
            continue
    page_number += 1

# تبدیل به دیتافریم
df = pd.DataFrame(records)

# نرمال سازی ستون رشته بیمه
df["رشته_بیمه"] = df["رشته_بیمه"].apply(normalize_text)

# نرمال سازی valid_fields
normalized_valid_fields = [normalize_text(v) for v in valid_fields]

# نگه داشتن فقط رشته های مورد نظر
df = df[df["رشته_بیمه"].isin(normalized_valid_fields)]

df = df[~df.astype(str).apply(lambda row: row.str.contains("اتکايي", na=False)).any(axis=1)]

for col in df.columns[3:]:
    df[col] = df[col].apply(lambda x: 0.0 if pd.isna(x) or not isinstance(x, (int, float)) else x)
    if df[col].dtype == 'object':
        df[col] = df[col].astype(str).apply(lambda x: safe_float_conversion(x))


protected_columns = ["اصلاحات_خسارت_پرداختی_مبلغ_میلیون_ریال","اصلاحات_حق_بیمه_صادره_شامل_قبولی_اتکایی_مبلغ_میلیون_ریال"]

cols_to_keep = [
    col for col in df.columns
    if col in protected_columns or (df[col] != 0).any()
]

df = df[cols_to_keep]


# ذخیره در دیتابیس
engine = create_engine("sqlite:///insurance_data.db")

df.to_sql(
    name="InsuranceReports",
    con=engine,
    if_exists="replace",
    index=False
)

df.to_excel("insurance_final_report.xlsx", index=False)
print("✅ عملیات با موفقیت پایان یافت.")
