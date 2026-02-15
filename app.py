import streamlit as st
import pandas as pd
import requests

# --- [설정] 텔레그램 정보 (반드시 입력하세요) ---
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

# 1. 엑셀 데이터 불러오기 (0 누락 방지 강화)
@st.cache_data
def load_data():
    try:
        # dtype=str은 모든 컬럼을 문자로 읽습니다. 
        # 만약 그래도 0이 사라진다면 엔진을 명시하거나 전처리를 추가합니다.
        df = pd.read_excel("order_database.xlsx", dtype=str)
        
        # 혹시 모를 공백이나 Nan 값을 처리합니다.
        df = df.fillna("")
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"엑셀 파일을 읽는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

df = load_data()

# 데이터가 있을 때만 실행
if not df.empty:
    # 엑셀 파일의 컬럼명과 정확히 일치해야 합니다.
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="거래처 주문 시스템", layout="wide")
    st.title("📦 거래처 전용 주문 페이지")
    st.markdown("---")

    # --- 사이드바 필터 ---
    st.sidebar.header("🔍 품목 검색")
    
    # 필터 목록 추출 (0이 포함된 문자열 상태 유지)
    categories = sorted([x for x in df[col_group].unique() if x])
    materials = sorted([x for x in df[col_material].unique() if x])

    category = st.sidebar.selectbox("제품군", ["전체"] + categories)
    material = st.sidebar.selectbox("재질/표면처리", ["전체"] + materials)

    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # --- 주문 리스트 영역 ---
    order_list = []
    
    # 헤더
    h1, h2, h3, h4, h5 = st.columns([0.5, 3, 1, 1, 1.5])
    h1.write("**선택**")
    h2.write("**품목 정보**")
    h3.write("**직경**")
    h4.write("**길이**")
    h5.write("**수량**")
    st.divider()

    # 데이터 행 생성
    for index, row in filtered_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1, 1, 1.5])
        
        with c1:
            # key값에 인덱스를 넣어 중복 방지
            selected = st.checkbox("", key=f"chk_{index}")
        with c2:
            # 주문코드가 0으로 시작해도 이제 문자열로 표시됩니다.
            st.markdown(f"**{row[col_group]}** ({row[col_code]})")
            st.caption(f"재질: {row[col_material]}")
        with c3:
            st.write(row[col_size])
        with c4:
            st.write(row[col_length])
        with c5:
            qty = st.number_input("수량", min_value=0, step=1, key=f"qty_{index}", label_visibility="collapsed")

        if selected and qty > 0:
            order_list.append({"code": row[col_code], "qty": qty})

    # --- 주문 전송 (사이드바) ---
    st.sidebar.divider()
    st.sidebar.subheader("🛒 현재 장바구니")

    if order_list:
        summary_text = ""
        for item in order_list:
            summary_text += f"{item['code']} / {item['qty']}개\n"
        
        st.sidebar.text_area("주문 내역 미리보기", value=summary_text, height=200)
        
        if st.sidebar.button("🚀 사장님께 주문 전송하기"):
            msg = f"🔔 [신규 주문 접수]\n\n
