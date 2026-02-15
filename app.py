import streamlit as st
import pandas as pd
import requests

# --- [설정] 텔레그램 정보 입력 ---
# 1단계에서 얻은 정보를 여기에 넣으세요.
TELEGRAM_TOKEN = "여기에_API_TOKEN을_넣으세요"
CHAT_ID = "여기에_확인한_숫자_ID를_넣으세요"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"알림 전송 실패: {e}")

# 1. 엑셀 데이터 불러오기
@st.cache_data
def load_data():
    try:
        # 모든 열을 문자열(str)로 읽어 0 누락 방지
        df = pd.read_excel("order_database.xlsx", dtype=str)
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 컬럼명 (사장님 엑셀과 정확히 일치)
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("🛒 거래처 전용 주문 페이지")

    # --- 사이드바 필터 ---
    st.sidebar.header("🔍 품목 필터")
    categories = sorted(df[col_group].dropna().unique())
    materials = sorted(df[col_material].dropna().unique())

    category = st.sidebar.selectbox("제품군 선택", ["전체"] + categories)
    material = st.sidebar.selectbox("재질/표면처리 선택", ["전체"] + materials)

    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # --- 주문 입력 영역 ---
    order_list = []
    c_check, c_info, c_size, c_len, c_qty = st.columns([0.5, 3, 1, 1, 2])
    c_check.write("**선택**")
    c_info.write("**제품명 / 재질**")
    c_size.write("**직경**")
    c_len.write("**길이**")
    c_qty.write("**수량**")
    st.divider()

    for index, row in filtered_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1, 1, 2])
        with c1:
            selected = st.checkbox("", key=f"check_{index}")
        with c2:
            st.write(f"**{row[col_group]}**")
            st.caption(f"{row[col_material]}")
        with c3: st.write(row[col_size])
        with c4: st.write(row[col_length])
        with c5:
            qty = st.number_input("수량", min_value=0, step=1, key=f"qty_{index}", label_visibility="collapsed")

        if selected and qty > 0:
            order_list.append({"code": row[col_code], "qty": qty})

    # --- 결과 출력 및 전송 ---
    st.sidebar.divider()
    st.sidebar.subheader("📋 내 주문 바구니")

    if order_list:
        final_output = "[새로운 주문이 접수되었습니다]\n\n"
        for item in order_list:
            final_output += f"코드: {item['code']} / 수량: {item['qty']}개\n"
        
        st.sidebar.text_area("주문서 미리보기", value=final_output.replace("[새로운 주문이 접수되었습니다]\n\n", ""), height=200)
        
        if st.sidebar.button("📦 이 내용으로 주문 전송하기"):
            send_telegram_message(final_output)
            st.balloons()
            st.sidebar.success("사장님께 주문이 전송되었습니다!")
    else:
        st.sidebar.info("품목을 선택하고 수량을 입력하세요.")
