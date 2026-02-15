import streamlit as st
import pandas as pd

# 1. 엑셀 데이터 불러오기
@st.cache_data
def load_data():
    # 사장님의 엑셀 파일 경로 (파일명: order_database.xlsx)
    # 파일 내 컬럼명: 제품군 대그룹, 재질,표면처리, 직경, 길이, 주문코드
    try:
        df = pd.read_excel("order_database.xlsx")
        return df
    except FileNotFoundError:
        # 테스트용 임시 데이터 (파일이 없을 경우 대비)
        data = {
            '제품군 대그룹': ['볼트', '볼트', '너트', '너트'],
            '재질,표면처리': ['SUS304', '철/아연', 'SUS304', '철/아연'],
            '직경': ['M6', 'M8', 'M6', 'M10'],
            '길이': [20, 30, '-', '-'],
            '주문코드': ['BT-001', 'BT-002', 'NT-001', 'NT-002']
        }
        return pd.DataFrame(data)

df = load_data()

st.set_page_config(page_title="주문 시스템", layout="wide")
st.title("🛒 거래처 전용 주문 페이지")
st.info("카테고리를 선택한 후, 필요한 품목의 체크박스를 누르고 수량을 입력하세요.")

# 2. 사이드바 필터 (품목이 많을 때 찾기 편하게 함)
st.sidebar.header("🔍 품목 필터")
category = st.sidebar.selectbox("제품군 대그룹", ["전체"] + list(df['제품군 대그룹'].unique()))
material = st.sidebar.selectbox("재질/표면처리", ["전체"] + list(df['재질,표면처리'].unique()))

# 필터 적용
filtered_df = df.copy()
if category != "전체":
    filtered_df = filtered_df[filtered_df['제품군 대그룹'] == category]
if material != "전체":
    filtered_df = filtered_df[filtered_df['재질,표면처리'] == material]

# 3. 주문 입력 영역
order_list = []

# 헤더 부분
col1, col2, col3, col4, col5 = st.columns([0.5, 3, 1.5, 1.5, 2])
col1.write("**선택**")
col2.write("**품목 정보**")
col3.write("**직경**")
col4.write("**길이**")
col5.write("**수량**")
st.divider()

# 필터링된 데이터 기반으로 목록 생성
for index, row in filtered_df.iterrows():
    c1, c2, c3, c4, c5 = st.columns([0.5, 3, 1.5, 1.5, 2])
    
    with c1:
        selected = st.checkbox("", key=f"check_{row['주문코드']}")
    with c2:
        st.write(f"**[{row['제품군 대그룹']}]** {row['재질,표면처리']}")
    with c3:
        st.write(row['직경'])
    with c4:
        st.write(row['길이'])
    with c5:
        # 선택된 경우에만 수량 입력창 활성화
        qty = st.number_input("수량", min_value=0, step=1, key=f"qty_{row['주문코드']}", label_visibility="collapsed")

    if selected and qty > 0:
        order_list.append({"code": row['주문코드'], "qty": qty})

# 4. 최종 주문 확인 및 복사 버튼
st.sidebar.divider()
st.sidebar.subheader("🛒 내 주문 바구니")

if order_list:
    final_output = ""
    for item in order_list:
        final_output += f"{item['code']} / {item['qty']}\n"
    
    st.sidebar.text_area("주문 코드 목록 (복사 가능)", value=final_output, height=200)
    
    if st.sidebar.button("주문 확정하기"):
        st.balloons()
        st.success("주문 내용이 생성되었습니다. 위 목록을 복사하여 전달해주세요!")
else:
    st.sidebar.write("선택된 상품이 없습니다.")