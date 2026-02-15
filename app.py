import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙 1] set_page_config는 무조건 코드의 맨 처음에 와야 합니다 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 1. 담당자 설정 (아이디 반영) ---
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

# --- 2. 데이터 보정 로직 ---
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

# --- 3. URL 파라미터 판별 (호환성 보강) ---
try:
    # 신버전 방식
    rep_key = st.query_params.get("rep", "lee")
except:
    try:
        # 구버전 방식
        rep_key = st.experimental_get_query_params().get("rep", ["lee"])[0]
    except:
        rep_key = "lee"

current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# --- 4. 세션 초기화 ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

# 데이터 로드
df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로딩 실패: {load_msg}")
    st.stop()

# 모바일용 스타일
st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; }
    .stNumberInput { margin-top: -10px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

st.title(f"📦 {current_rep['name']} 주문채널")

# --- 5. 사이드바 ---
st.sidebar.header("🏢 주문자 정보")
cust_name = st.sidebar.text_input("거래처명 (필수)")
mgr_name = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df['제품군 대그룹 (Product Group)'].unique()))
mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df['재질/표면처리'].unique()))

f_df = df.copy()
if cat != "전체": f_df = f_df[f_df['제품군 대그룹 (Product Group)'] == cat]
if mat != "전체": f_df = f_df[f_df['재질/표면처리'] == mat]

# --- 6. 모바일 최적화 카드 목록 ---
st.write(f"검색 결과: **{len(f_df)}** 건")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    with st.container(border=True):
        st.markdown(f"### {row['제품군 대그룹 (Product Group)']}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']} | {row['재질/표면처리']}")
        
        c1, c2 = st.columns([1, 1.5])
        with c1:
            is_checked = item_key in st.session_state['cart']
            sel = st.checkbox("선택", key=f"chk_{idx}", value=is_checked)
        with c2:
            prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
            q = st.number_input("수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_q))

        if sel and q > 0:
            st.session_state['cart'][item_key] = {'c': row['주문코드'], 'q': q}
        else:
            st.session_state['cart'].pop(item_key, None)

# --- 7. 하단 고정형 전송바 ---
if st.session_state['cart']:
    st.divider()
    st.subheader("🛒 담은 목록")
    items_list = [f"- {v['c']} / {v['q']}개" for v in st.session_state['cart'].values()]
    summary = "\n".join(items_list)
    st.text(summary)
    
    if st.button("🚀 주문 확정 및 전송", use_container_width=True, type="primary"):
        if not cust_name or not mgr_name:
            st.error("사이드바(왼쪽 메뉴)에서 거래처 정보를 먼저 입력해주세요!")
        else:
            full_msg = f"🔔 [{current_rep['name']}] 주문\n🏢 {cust_name}\n👤 {mgr_name}\n----\n{summary}"
            ok, res = send_telegram(full_msg, current_rep['id'])
            if ok:
                st.balloons()
                st.success("담당자에게 주문이 전송되었습니다!")
            else:
                st.error(f"전송 실패: {res}")

if st.sidebar.button("🗑️ 장바구니 초기화", use_container_width=True):
    st.session_state['cart'] = {}
    st.rerun()

