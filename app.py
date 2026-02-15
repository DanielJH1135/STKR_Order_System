import streamlit as st
import pandas as pd
import requests
import re

# --- [설정] 본인의 정보로 수정 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
# 텔레그램 ID는 따옴표 없이 숫자만 적거나, 따옴표 안에 적어도 됩니다.
CHAT_ID = 1781982606

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return True, "성공"
        else:
            return False, f"에러코드 {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# 1. 데이터 로드 및 정밀 보정
@st.cache_data
def load_data():
    try:
        # 모든 열을 문자로 읽어오기
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("")

        def fix_order_code(code):
            code = str(code).strip()
            if not code or code.lower() == "nan": 
                return ""
            
            # 점(.)이 있는 경우의 처리 (예: 21.001 -> 021.0010)
            if "." in code:
                parts = code.split(".")
                prefix = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                
                # 점 앞자리: 숫자로만 되어 있으면 3자리로 (21 -> 021)
                if prefix.isdigit():
                    prefix = prefix.zfill(3)
                
                # 점 뒷자리: 순수 숫자면 4자리로 (001 -> 0010)
                # 만약 문자가 섞여있으면(예: 906s) 그대로 둠
                if suffix.isdigit():
                    suffix = suffix.ljust(4, '0')
                
                return f"{prefix}.{suffix}"
            
            return code

        df['주문코드'] = df['주문코드'].apply(fix_order_code)
        return df
    except Exception as e:
        # 에러 발생 시 화면에 상세 원인 표시
        st.error(f"❌ 데이터 로딩 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 페이지 설정
st.set_page_config(page_title="주문 시스템", layout="wide")
df = load_data()

# 장바구니 세션 초기화
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

if not df.empty:
    # 엑셀 컬럼명
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.title("📦 거래처 전용 주문 페이지")

    # --- 사이드바 영역 ---
    st.sidebar.header("🏢 주문자 정보")
    c_name = st.sidebar.text_input("거래처명 (필수)")
    m_name = st.sidebar.text_input("담당자명 (필수)")

    st.sidebar.divider()
    st.sidebar.header
