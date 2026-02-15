import streamlit as st
import pandas as pd

# 1. 엑셀 데이터 불러오기
@st.cache_data
def load_data():
    # 엑셀 파일명과 일치해야 합니다.
    try:
        # 실제 배포 시 엑셀 파일을 읽어옵니다.
        df = pd.read_excel("order_database.xlsx")
        return df
    except Exception:
        # 엑셀 파일이 없을 경우를 대비한 샘플 (파일 이름을 확인해주세요)
        st.error("엑셀 파일을 찾을 수 없습니다. 파일명이 'order_database.xlsx'인지 확인해주세요.")
        return pd.DataFrame()

df = load_data()

# 데이터가 비어있지 않은 경우에만 실행
if not df.empty:
    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("🛒 거래처 전용 주문 페이지")

    # 2. 사이드바 필터 (정확한 컬럼명 반영)
    st.sidebar.header("🔍 품목 필터")
    
    # 컬럼명을 엑셀과 똑같이 맞췄습니다.
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    category = st.sidebar.selectbox("제품군 선택", ["전체"] + list(df[col_group].unique()))
    material = st.sidebar.selectbox("재질/표면처리 선택", ["전체"] + list(df[col_material].unique()))

    # 필터 적용
    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # 3. 주문 입력 영역
    order_list = []

    # 헤더 설정
    c_check, c_info, c_size, c_len, c_qty = st.columns([0.5, 3, 1, 1, 2])
    c_check.write("**선택**")
    c_info.write("**제품군 / 재질**")
    c_size.write("**직경**")
    c_len.write("**길이**")
    c_qty.write("**수량 입력**")
    st.divider()

    # 필터링된 데이터 출력
    for index, row in filtered_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1, 1, 2])
        
        with c1:
            selected = st.checkbox("", key=f"check_{index}")
        with c2:
            st.write(f"**{row[col_group]}**")
            st.caption(f"{row[col_material]}")
        with c3:
            st.write(row[col_size])
        with c4:
            st.write(row[col_length])
        with c5:
            qty = st.number_input("수량", min_value=0, step=1, key=f"qty_{index}", label_visibility="collapsed")

        if selected and qty > 0:
            order_list.append({"code": row[col_code], "qty": qty})

    # 4. 결과 출력 (사이드바)
    st.sidebar.divider()
    st.sidebar.subheader("📋 내 주문 내역")

    if order_list:
        final_output = ""
        for item in order_list:
            final_output += f"{item['code']} / {item['qty']}\n"
        
        st.sidebar.text_area("주문서 (복사해서 전달해주세요)", value=final_output, height=200)
        
        if st.sidebar.button("주문 완료 확인"):
            st.balloons()
            st.sidebar.success("주문 리스트가 생성되었습니다!")
    else:
        st.sidebar.info("품목을 선택하고 수량을 입력하세요.")
