import streamlit as st
import pandas as pd
import requests

# --- [설정] 사장님의 정보 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = "1781982606" # userinfobot에서 확인한 숫자

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        return res.status_code == 200
    except Exception as e:
        st.error(f"알림 전송 실패: {e}")
        return False

# 1. 엑셀 데이터 불러오기 (0 누락 방지)
@st.cache_data
def load_data():
    try:
        # 모든 컬럼을 강제로 '문자열'로 읽어옵니다.
        df = pd.read_excel("order_database.xlsx", dtype=str)
        # 데이터 정제 (빈칸 제거 등)
        df = df.fillna("").apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 컬럼명 설정 (엑셀과 정확히 일치해야 함)
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="거래처 주문 시스템", layout="wide")
    st.title("📦 거래처 전용 주문 페이지")

    # --- 사이드바: 거래처 정보 및 필터 ---
    st.sidebar.header("🏢 주문자 정보")
    customer_name = st.sidebar.text_input("거래처명 (필수)", placeholder="예: 가나다치과")
    manager_name = st.sidebar.text_input("담당자명 (필수)", placeholder="예: 홍길동")

    st.sidebar.divider()
    st.sidebar.header("🔍 품목 필터")
    categories = sorted(df[col_group].unique())
    category = st.sidebar.selectbox("제품군", ["전체"] + categories)
    
    materials = sorted(df[col_material].unique())
    material = st.sidebar.selectbox("재질/표면처리", ["전체"] + materials)

    # 필터 적용
    filtered_df = df.copy()
    if category != "전체":
        filtered_df
