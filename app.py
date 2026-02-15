import streamlit as st
import pandas as pd
import requests
import os

# --- 1. 환경 설정 (아이디 반영 완료) ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = "1781982606"  # 사장님 아이디 적용

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

# --- 2. 데이터 보정 로직 (021.0010 형식 맞춤) ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    
    # 점(.)이 있는 경우 처리
    if "." in c:
        parts = c.split(".", 1)
        prefix = parts[0]
        suffix = parts[1]
        
        # 앞자리: 숫자면 3자리로 (21 -> 021)
        if prefix.isdigit():
            prefix = prefix.zfill(3)
        
        # 뒷자리: 숫자면 4자리로 (001 -> 0010)
        # 단, 906s 처럼 문자가 섞여있으면 보존
        if suffix.isdigit():
            suffix = suffix.ljust(4, '0')
            
        return f"{prefix}.{suffix}"
    
    return c

# --- 3. 데이터 로딩 ---
@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    if not os.path.exists(file_path):
        return None, f"❌ '{file_path}' 파일을 찾을 수 없습니다."
    try:
        # 모든 열을 문자로 읽기
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("")
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, f"❌ 데이터 읽기 오류: {str(e)}"

# --- 4. 페이지 구성 ---
st.set_page_config(page_title="주문 시스템", layout="wide")
df, msg = load_data()

if df is None:
    st.error(msg)
    st.stop()

# 장바구니 세션 초기화
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

st.title("📦 거래처 전용 주문 시스템")

# --- 5. 사이드바 (정보입력 및 필터) ---
st.sidebar.header("🏢 주문자 정보")
cust_name = st.sidebar.text_input("거래처명 (필수)", key="customer_input_box")
mgr_name = st.sidebar.text_input("담당자명 (필수)", key="manager_input_box")

st.sidebar.divider()
st.sidebar.header("🔍 품목 필터")

c_group = '제품군 대그룹
