import streamlit as st
import pandas as pd
import requests

# --- [설정] 텔레그램 정보 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = "1781982606"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except Exception as e:
        st.error(f"알림 전송 실패: {e}")
        return False

# 1. 데이터 불러오기 (0 누락 방지 처리 강화)
@st.cache_data
def load_data():
    try:
        # 모든 열을 문자로 읽어 0 누락 방지
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"엑셀 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 엑셀 컬럼명 정의
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("📦 거래처 주문 페이지")

    # --- 사이드바: 정보 입력 및 필터 ---
    st.sidebar.header("🏢 주문자 정보")
    customer_
