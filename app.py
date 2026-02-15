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

# 1. 데이터 불러오기
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"엑셀 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

# --- [중요] 세션 스테이트 초기화 ---
# 'order_data'는 실제 장바구니에 담긴 내역을 저장합니다.
if 'order_data' not in st.session_state:
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

    # --- 사이드바 ---
    st.sidebar.header("🏢 주문자 정보")
    customer_name = st.sidebar.text_input("거래처명 (필수)")
    manager_name = st.sidebar.text_input("담당자명 (필수)")

    st.sidebar.divider()
    st.sidebar.header("🔍 품목 필터")
    category = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[col_group].unique()))
    material = st.sidebar.selectbox("재질", ["전체"] + sorted(df[col_material].unique()))

    # 필터 적용
    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # --- 메인 주문 영역 ---
    st.write(f"조회된 품목: {len(filtered_df)}개")
    
    h1, h2, h3, h4, h5 = st.columns([0.5, 3, 1, 1, 1.5])
    h1.write("**선택**"); h2.write("**제품명 / 주문코드**"); h3.write("**직경**"); h4.write("**길이**"); h5.write("**수량**")
    st.divider()

    # 품목 리스트 생성 (인덱스를 사용하여 중복 에러 방지)
    for idx, row in filtered_df.iterrows():
        code = row[col_code]
        # 주문 내역이 있는지 확인 (키를 '인덱스'로 잡아서 중복 주문코드 대응)
        item_key = f"item_{idx}"
        
        saved_qty = st.session_state['order_data'].get(item_key, {}).get('qty', 0)
        is_checked = item_key in st.session_state['order_data']
        
        cols = st.columns([0.5, 3, 1, 1, 1.5])
        
        with cols[0]:
            # 위젯 키에 idx를 포함시켜 절대 중복되지 않게 함
            selected = st.checkbox("", key=f"chk_{idx}", value=is_checked)
            
        with cols[1]:
            st.markdown(f"**{row[col_group]}**")
            st.code(code) 
            st.caption(f"재질: {row[col_material]}")
            
        with cols[2]: st.write(row[col_size])
        with cols[3]: st.write(row[col_length])
        with cols[4]:
            qty = st.number_input("수량", min_value=0, step=1, key=f"q_{idx}", value=int(saved_qty), label_visibility="collapsed")

        # 체크 상태 업데이트
        if selected and qty > 0:
            st.session_state['order_data'][item_key] = {'code': code, 'qty': qty}
        else:
            st.session_state['order_data'].pop(item_key, None)

    # --- 장바구니 및 전송 ---
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")

    if st.session_state['order_data']:
        final_list = []
        for info in st.session_state['order_data'].values():
            final_list.append(f"- {info['code']} / {info['qty']}개")
        
        summary_text = "\n".join(final_list)
        st.sidebar.text_area("주문 내역", value=summary_text, height=200)
        
        if st.sidebar.button("🚀 스트라우만 담당자에게 주문 보내기"):
            if not customer_name or not manager_name:
                st.sidebar.error("거래처명/담당자명을 입력하세요!")
            else:
                full_message = f"🔔 [새 주문]\n🏢 {customer_name}\n👤 {manager_name}\n----\n{summary_text}"
                if send_telegram_message(full_message):
                    st.balloons()
                    st.sidebar.success("전송 완료!")
                else:
                    st.sidebar.error("전송 실패!")
    else:
        st.sidebar.info("상품을 선택하세요.")

    if st.sidebar.button("🗑️ 장바구니 초기화"):
        st.session_state['order_data'] = {}
        st.rerun()

