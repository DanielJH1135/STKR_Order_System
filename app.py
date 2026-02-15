import streamlit as st
import pandas as pd
import requests

# --- [설정] 텔레그램 정보 ---
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

# 1. 데이터 불러오기 (0 누락 방지 처리)
@st.cache_data
def load_data():
    try:
        # 모든 열을 강제로 문자열(str)로 읽어옵니다.
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"엑셀 파일 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

# --- [핵심] 주문 상태를 기억하기 위한 세션 스테이트 초기화 ---
if 'order_data' not in st.session_state:
    # { '주문코드': 수량 } 형태로 저장
    st.session_state['order_data'] = {}

if not df.empty:
    # 엑셀 컬럼명
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("📦 거래처 전용 주문 페이지")

    # --- 사이드바: 정보 입력 및 필터 ---
    st.sidebar.header("🏢 주문자 정보")
    customer_name = st.sidebar.text_input("거래처명 (필수)")
    manager_name = st.sidebar.text_input("담당자명 (필수)")

    st.sidebar.divider()
    st.sidebar.header("🔍 품목 필터")
    categories = sorted(df[col_group].unique())
    category = st.sidebar.selectbox("제품군", ["전체"] + categories)
    
    materials = sorted(df[col_material].unique())
    material = st.sidebar.selectbox("재질", ["전체"] + materials)

    # 필터 적용된 데이터
    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # --- 메인 주문 영역 ---
    st.write(f"총 {len(filtered_df)}개의 품목이 검색되었습니다.")
    
    # 헤더
    h1, h2, h3, h4, h5 = st.columns([0.5, 3, 1, 1, 1.5])
    h1.write("**선택**"); h2.write("**제품명 / 주문코드**"); h3.write("**직경**"); h4.write("**길이**"); h5.write("**수량**")
    st.divider()

    # 품목 리스트 생성
    for index, row in filtered_df.iterrows():
        code = row[col_code]
        
        # 세션 스테이트에 현재 코드가 있는지 확인
        current_qty = int(st.session_state['order_data'].get(code, 0))
        is_checked = code in st.session_state['order_data']
        
        cols = st.columns([0.5, 3, 1, 1, 1.5])
        
        with cols[0]:
            # 체크박스 상태를 세션에서 가져와서 유지
            selected = st.checkbox("", key=f"chk_{code}", value=is_checked)
            
        with cols[1]:
            st.markdown(f"**{row[col_group]}**")
            st.code(code) # 0이 포함된 코드 표시
            st.caption(f"재질: {row[col_material]}")
            
        with
