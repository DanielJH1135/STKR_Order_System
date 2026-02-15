import streamlit as st
import pandas as pd
import requests
import os

# --- 1. 담당자 설정 ---
SALES_REPS = {
    "lee": {"name": "사장님", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

# --- 2. 데이터 보정 및 로딩 ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".", 1)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1].ljust(4, '0') if parts[1].isdigit() else parts[1]
        return f"{prefix}.{suffix}"
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, str(e)

# --- 3. URL 파라미터 판별 ---
query_params = st.query_params
rep_key = query_params.get("rep", "lee")
current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# --- 4. 페이지 구성 (모바일 최적화) ---
# 레이아웃을 'centered'로 설정하여 모바일에서 더 보기 좋게 만듭니다.
st.set_page_config(page_title=f"주문- {current_rep['name']}", layout="centered")

df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로딩 실패: {load_msg}")
    st.stop()

if '
