import sqlite3
import pandas as pd

# اتصال به دیتابیس
conn = sqlite3.connect("insurance_data.db")

# دیدن لیست جدول‌ها
#tables = pd.read_sql("""
#SELECT name
#FROM sqlite_master #
#WHERE type='table';
#""", conn)

#print("Tables in database:")
#print(tables)

# خواندن داده‌های جدول
df = pd.read_sql("""
SELECT *
FROM InsuranceReports
LIMIT 19 OFFSET 280;
""", conn)

print(df)


conn.close()
