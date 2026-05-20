import requests
import os
import csv
import time
from datetime import datetime, timedelta

API_KEY = os.getenv("DART_API_KEY")
URL = "https://opendart.fss.or.kr/api/list.json"
DB_FILE = "DB_DART.csv"

# 기존 DB 로드
def load_existing_DART():
    if not os.path.exists(DB_FILE):
        return set()
    existing = set()
    with open(DB_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row["fund_name"])
    return existing


# DB 저장
def append_new_DART(fund_name):
    file_exists = os.path.exists(DB_FILE)
    with open(DB_FILE, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["fund_name"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "fund_name": fund_name
        })


# 텔레 발송
def send_telegram_DART(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, data=payload)


# ETF 이름 추출
def extract_etf_name(report_nm):
    keyword = "증권상장지수투자신탁"

    if keyword not in report_nm:
        return None

    marker = ")("
    pos = report_nm.find(marker)

    if pos == -1:
        return None

    start = pos + 2
    end = report_nm.find(keyword) + len(keyword)

    name = report_nm[start:end]

    return name.strip()


# DART 신규 공시 체크
def check_new_etf_DART():
    today = datetime.utcnow()
    start_date = today - timedelta(days=50)
    existing = load_existing_DART()
    page_no = 1
    while True:
        params = {
            "crtfc_key": API_KEY,
            "pblntf_ty": "G",
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": today.strftime("%Y%m%d"),
            "page_no": page_no,
            "page_count": 100
        }
        res = requests.get(URL, params=params)
        data = res.json()
        if data.get("status") != "000":
            print("DART API ERROR")
            break
        reports = data.get("list", [])
        if not reports:
            break
        for item in reports:
            report_nm = item.get("report_nm", "")
            rcept_no = item.get("rcept_no", "")
            # 상장지수 포함
            if "상장지수" not in report_nm:
                continue
            # 일괄신고서만
            if "일괄신고서" not in report_nm:
                continue
            # 정정 제외
            if "정정" in report_nm:
                continue
            fund_name = extract_etf_name(report_nm)
            if not fund_name:
                continue
            if fund_name not in existing:
                link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                message = f"[DART 일괄신고서] {fund_name}\n{link}"
                send_telegram_DART(message)
                append_new_DART(fund_name)
                existing.add(fund_name)
                print("NEW:", fund_name)
            else:
                print("EXIST:", fund_name)
        total_page = int(data.get("total_page", 1))
        if page_no >= total_page:
            break
        page_no += 1
        time.sleep(0.2)
