import streamlit as st
import pandas as pd
import requests
import re

# --- [설정] 본인의 정보로 수정 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = 1781982606 # 본인의 텔레그램 숫자 ID

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return True, "성공"
        else:
            return False, f"에러 {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# 1. 데이터 불러오기 및 코드 보정 (021.0010 형식 맞춤)
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("")

        def fix_code(code):
            code = str(code).strip()
            if not code or code.lower() == "nan": return ""
            
            # 점(.)이 있는 경우 처리 (예: 21.001 -> 021.0010)
            if "." in code:
                parts = code.split(".")
                prefix = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                
                # 점 앞자리: 숫자면 3자리 (21 -> 021)
                if prefix.isdigit(): prefix = prefix.zfill(3)
                
                # 점 뒷자리: 숫자면 4자리 (001 -> 0010)
                if suffix.isdigit(): suffix = suffix.ljust(4, '0')
                
                return f"{prefix}.{suffix}"
            return code

        df['주문코드'] = df['주문코드'].apply(fix_code)
        return df
    except Exception as e:
        st.error(f"엑셀 읽기 오류: {e}")
        return pd.DataFrame()

# 페이지 기본 설정
st.set_page_config(page_title="주문 시스템", layout="wide")
df = load_data()

# 장바구니 세션 초기화
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

if not df.empty:
    col_group = '
