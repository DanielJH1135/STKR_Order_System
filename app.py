import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙] 반드시 최상단 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 1. 담당자 설정 (이정현 과장님 ID 반영) ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

# --- 2. 주문코드 보정 (021.0010 형식) ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".", 1)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1].ljust(4, '0') if parts[1].isdigit() else parts[1]
        return f"{prefix}.{suffix}"
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, str(e)

# --- 3. 담당자 판별 (URL 파라미터) ---
try:
    rep_key = st.query_params.get("rep", "lee")
except:
    rep_key = "lee"
current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# --- 4. 세션 초기화 ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로드 실패: {load_msg}")
    st.stop()

# 모바일 최적화 스타일
st.markdown("""
    <style>
    .stNumberInput { margin-top: -5px; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    .stButton button { font-weight: bold; height: 3rem; }
    </style>
    """, unsafe_allow_html=True)

# 상단 타이틀
st.title(f"🛒 {current_rep['name']} 주문채널")
st.info(f"수신 담당자: {current_rep['name']}")

# --- 5. 사이드바 (정보입력 + 필터 + 장바구니) ---
st.sidebar.header("🏢 주문 정보 입력")
cust_name = st.sidebar.text_input("거래처명 (필수)", placeholder="예: 가나다치과")
mgr_name = st.sidebar.text_input("담당자명 (필수)", placeholder="예: 김철수 실장")

st.sidebar.divider()
st.sidebar.header("🔍 품목 필터")
cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df['제품군 대그룹 (Product Group)'].unique()))
mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df['재질/표면처리'].unique()))

# 사이드바 장바구니 실시간 표시
st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")

if st.session_state['cart']:
    cart_items = [f"• {v['c']} / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(cart_items))
    
    if st.sidebar.button(f"🚀 {current_rep['name']}에게 전송", use_container_width=True, type="primary"):
        if not cust_name or not mgr_name:
            st.sidebar.error("⚠️ 거래처명과 담당자명을 입력하세요!")
        else:
            order_summary = "\n".join([f"- {v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
            full_msg = f"🔔 [{current_rep['name']}] 주문 접수\n🏢 {cust_name}\n👤 {mgr_name}\n----\n{order_summary}"
            
            success, res = send_telegram(full_msg, current_rep['id'])
            if success:
                st.sidebar.success("✅ 전송 성공!")
                st.balloons()
            else:
                st.sidebar.error(f"❌ 실패: {res}")
    
    if st.sidebar.button("🗑️ 장바구니 초기화", use_container_width=True):
        st.session_state['cart'] = {}
        st.rerun()
else:
    st.sidebar.warning("🛒 수량을 입력하면 담깁니다.")

# --- 6. 품목 리스트 (체크박스 제거 버전) ---
f_df = df.copy()
if cat != "전체": f_df = f_df[f_df['제품군 대그룹 (Product Group)'] == cat]
if mat != "전체": f_df = f_df[f_df['재질/표면처리'] == mat]

st.write(f"조회된 품목: **{len(f_df)}** 건")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    with st.container(border=True):
        st.markdown(f"**{row['제품군 대그룹 (Product Group)']}**")
        st.code(row['주문코드'])
        st.caption(f"규격: {row['직경']} x {row['길이']} | {row['재질/표면처리']}")
        
        # 체크박스 없이 바로 수량 입력
        prev_qty = st.session_state['cart'].get(item_key, {}).get('q', 0)
        qty = st.number_input("주문 수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_qty))

        # 0보다 크면 장바구니에 넣고, 0이면 뺌
        if qty > 0:
            st.session_state['cart'][item_key] = {'c': row['주문코드'], 'q': qty}
        else:
            if item_key in st.session_state['cart']:
                del st.session_state['cart'][item_key]
