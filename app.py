import streamlit as st
import pandas as pd
import requests

# --- [설정] 본인의 정보로 수정하세요 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = 1781982606 # 예: 12345678 (따옴표 없이 숫자만)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return True, "성공"
        else:
            return False, res.text # 에러 메시지 반환
    except Exception as e:
        return False, str(e)

@st.cache_data
def load_data():
    try:
        # 1. 일단 모두 문자로 읽기
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("")
        
        # 2. [핵심] 주문코드 0 보정 로직
        # 코드 길이가 짧고 숫자로만(소수점 포함) 되어 있다면 앞에 0을 붙여 8자리로 맞춤
        def fix_code(code):
            code = str(code).strip()
            if not code: return ""
            # 만약 코드가 '0'으로 시작하지 않고, 숫자로 시작하는 형태라면 (예: 61.5308)
            # 사장님 품목 코드의 일반적인 길이(8자리)에 맞춰 앞에 0을 채웁니다.
            if code[0].isdigit() and len(code) < 8:
                return code.zfill(8)
            return code

        df['주문코드'] = df['주문코드'].apply(fix_code)
        return df
    except Exception as e:
        st.error(f"엑셀 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

if 'order_data' not in st.session_state:
    st.session_state['order_data'] = {}

if not df.empty:
    # 컬럼명 (사장님 파일 기준)
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

    filtered_df = df.copy()
    if category != "전체":
        filtered_df = filtered_df[filtered_df[col_group] == category]
    if material != "전체":
        filtered_df = filtered_df[filtered_df[col_material] == material]

    # --- 메인 영역 ---
    h1, h2, h3, h4, h5 = st.columns([0.5, 3, 1, 1, 1.5])
    h1.write("**선택**"); h2.write("**품목 정보**"); h3.write("**직경**"); h4.write("**길이**"); h5.write("**수량**")
    st.divider()

    for idx, row in filtered_df.iterrows():
        code = row[col_code]
        item_key = f"item_{idx}"
        saved_qty = st.session_state['order_data'].get(item_key, {}).get('qty', 0)
        is_checked = item_key in st.session_state['order_data']
        
        cols = st.columns([0.5, 3, 1, 1, 1.5])
        with cols[0]:
            selected = st.checkbox("", key=f"chk_{idx}", value=is_checked)
        with cols[1]:
            st.markdown(f"**{row[col_group]}**")
            st.code(code) # 여기서 0이 붙은 코드가 보여야 합니다.
            st.caption(f"재질: {row[col_material]}")
        with cols[2]: st.write(row[col_size])
        with cols[3]: st.write(row[col_length])
        with cols[4]:
            qty = st.number_input("수량", min_value=0, step=1, key=f"q_{idx}", value=int(saved_qty), label_visibility="collapsed")

        if selected and qty > 0:
            st.session_state['order_data'][item_key] = {'code': code, 'qty': qty}
        else:
            st.session_state['order_data'].pop(item_key, None)

    # --- 장바구니 및 전송 ---
    st.sidebar.divider()
    if st.session_state['order_data']:
        final_list = [f"- {info['code']} / {info['qty']}개" for info in st.session_state['order_data'].values()]
        summary_text = "\n".join(final_list)
        st.sidebar.text_area("주문 내역", value=summary_text, height=200)
        
        if st.sidebar.button("🚀 스트라우만 주문 보내기"):
            if not customer_name or not manager_name:
                st.sidebar.error("이름과 담당자를 입력하세요!")
            else:
                full_message = f"🔔 [새 주문]\n🏢 {customer_name}\n👤 {manager_name}\n----\n{summary_text}"
                success, error_msg = send_telegram_message(full_message)
                if success:
                    st.balloons()
                    st.sidebar.success("전송 완료!")
                else:
                    st.sidebar.error(f"전송 실패! 에러내용: {error_msg}")
    else:
        st.sidebar.info("상품을 선택하세요.")

    if st.sidebar.button("🗑️ 초기화"):
        st.session_state['order_data'] = {}
        st.rerun()
