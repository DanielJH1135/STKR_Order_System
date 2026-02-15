import streamlit as st
import pandas as pd
import requests
import os

# 1. 텔레그램 설정
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = 1781982606 # 반드시 숫자만!

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

# 2. 데이터 로딩 (가장 튼튼하게 수정)
@st.cache_data
def load_excel():
    file_name = "order_database.xlsx"
    # 파일 존재 여부 확인
    if not os.path.exists(file_name):
        return None, f"❌ '{file_name}' 파일을 찾을 수 없습니다. 깃허브에 파일이 있는지 확인하세요."
    
    try:
        # 모든 데이터를 문자로 읽기
        df = pd.read_excel(file_name, dtype=str)
        df = df.fillna("")
        
        # [핵심] 021.0010 보정 로직
        def clean_code(c):
            c = str(c).strip()
            if "." in c:
                prefix, suffix = c.split(".", 1)
                # 앞자리 3자리로 (21 -> 021)
                if prefix.isdigit(): prefix = prefix.zfill(3)
                # 뒷자리 4자리로 (001 -> 0010)
                if suffix.isdigit(): suffix = suffix.ljust(4, '0')
                return f"{prefix}.{suffix}"
            return c

        df['주문코드'] = df['주문코드'].apply(clean_code)
        return df, "성공"
    except Exception as e:
        return None, f"❌ 엑셀 읽기 오류: {str(e)}"

# --- 페이지 시작 ---
st.set_page_config(page_title="주문 시스템", layout="wide")

# 세션 초기화 (최상단)
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, msg = load_excel()

# 데이터 로딩 실패 시 에러 메시지 출력 (아무것도 안 뜨는 현상 방지)
if df is None:
    st.error(msg)
    st.info("
