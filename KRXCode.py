import requests
import os
import csv
from bs4 import BeautifulSoup

# 1) 표준코드 발급 내역

URL_KRXCode = "https://isin.krx.co.kr/corp/corpList.do"
DB_KRXCode = "DB_KRXCode.csv"

# DB 파일 로드
def load_etf_KRXCode():
    if not os.path.exists(DB_KRXCode):
        return set()

    existing = set()
    with open(DB_KRXCode, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row["issuer_code"])

    return existing

# DB 저장
def append_new_etf_KRXCode(code, name):
    file_exists = os.path.exists(DB_KRXCode)

    with open(DB_KRXCode, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["issuer_code", "fund_name"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "issuer_code": code,
            "fund_name": name
        })

# 크롤링
def crawling_KRXCode():
    etf_list = []
    page = 1
    prev_page_data = None

    while True:
        params = {
            "method": "corpInfoList",
            "searchWord": "상장지수",
            "paramSearchWord": "상장지수",
            "isur_cd": "",
            "currentPage": str(page),
            "pageIndex": str(page)
        }

        res = requests.post(URL_KRXCode, data=params)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")

        if not rows:
            break

        current_page_data = []

        for r in rows:
            cols = r.find_all("td")
            if len(cols) > 1:
                code = cols[0].text.strip()
                name = cols[1].text.strip()

                current_page_data.append(code)

                etf_list.append({
                    "issuer_code": code,
                    "fund_name": name
                })

        if current_page_data == prev_page_data:
            break

        prev_page_data = current_page_data
        page += 1

    return etf_list

# 텔레 발송
def send_telegram_KRXCode(message):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(url, data=payload)

# 실행
def check_new_etf_KRXCode():
    existing = load_etf_KRXCode()
    etf_list = crawling_KRXCode()

    for etf in etf_list:
        code = etf["issuer_code"]
        name = etf["fund_name"]

        if code not in existing:
            send_telegram_KRXCode(f"[표준코드 발급] {name}")
            append_new_etf_KRXCode(code, name)
            existing.add(code)

            print("NEW:", name, code)
        else:
            print("EXIST:", name, code)
