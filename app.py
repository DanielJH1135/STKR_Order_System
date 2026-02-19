import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v5.2", layout="centered")

# --- 0. 담당자 및 URL 파라미터 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}

try:
    p = st.query_params
    rep_key = p.get("rep", "lee")
    url_cust = p.get("cust", "")
    if isinstance(rep_key, list): rep_key = rep_key[0]
    if isinstance(url_cust, list): url_cust = url_cust[0]
except:
    rep_key, url_cust = "lee", ""

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

# --- 중앙 로고 ---
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    img = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
    if os.path.exists(img): st.image(img, use_container_width=True)

# --- 1. 데이터 로드 및 포맷 ---
def format_code_final(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".")
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        return f"{prefix}.{parts[1]}"
    return c.zfill(3) if c.isdigit() else c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_code_final)
        
        bio = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.3ml', '주문코드': '075.101w', '직경': '-', '길이': '-', '구분': ''},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.7ml', '주문코드': '075.102w', '직경': '-', '길이': '-', '구분': ''}
        ]
        return pd.concat([df, pd.DataFrame(bio)], ignore_index=True), "성공"
    except Exception as e: return None, str(e)

df, _ = load_data()

# --- 2. 텔레그램 전송 함수 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 3. [복구] 최종 확인 팝업창 (교환안내 포함) ---
@st.dialog("📋 주문 내역을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    # [요청사항] 교환 안내 문구 (볼드, 레드)
    st.markdown(":red[**※ 교환 보내실 제품은 유효기간 1년이상 남은 제품만 가능합니다.**]")
    
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action_text = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        
        full_msg = (
            f"🔔 [{current_rep['name']}] 주문접수\n"
            f"🏢 {cust_name}\n"
            f"👤 {mgr_name}\n\n"
            f"{order_list}\n\n"
            f"{cust_name} {action_text}"
        )
        
        ok, res = send_telegram(full_msg, current_rep['id'])
        if ok:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error(f"실패: {res}")

# --- 4. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

# --- 5. 메인 UI 및 필터 버튼 (v5.1 유지) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.write("### 1️⃣ 시스템 선택")
r1, r2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c_rows = [st.columns(3), st.columns(3)]
for idx, row_cats in enumerate([r1, r2]):
    for i, cat in enumerate(row_cats):
        with c_rows[idx][i]:
            if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
                st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
                st.rerun()

if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c3 = st.columns(3)
    for i, m in enumerate(mats):
        with c3[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    if cur == "BL": specs = ["3.3", "4.1", "4.8"]
    elif cur == "BLT": specs = ["2.9", "3.3", "4.1", "4.8"]
    elif cur in ["TL", "TLX"]: specs = ["S", "SP"]
    elif cur == "BLX":
        blx_data = df[df['제품군 대그룹 (Product Group)'].str.contains("BLX", na=False)]
        specs = sorted(blx_data['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
    else: specs = []

    if specs:
        s_cols = st.columns(len(specs) if len(specs) <= 5 else 5)
        for i, s in enumerate(specs):
            with s_cols[i % 5]:
                label = f"S (2.8mm)" if s == "S" else (f"SP (1.8mm)" if s == "SP" else f"Ø {s}")
                if st.button(label, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s
                    st.rerun()

if st.button("🔄 검색 조건 초기화", use_container_width=True):
    st.session_state.selected_cat = st.session_state.selected_mat = st.session_state.selected_spec = "전체"
    st.rerun()

st.divider()

# --- 6. [복구] 사이드바 (정보입력 + 장바구니 + 전송버튼) ---
st.sidebar.header("🏢 주문 정보 입력")
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader(f"🛒 실시간 장바구니 ({len(st.session_state['cart'])}건)")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name']} / {v['q']}개")
    
    st.sidebar.divider()
    # [복구] 전송 버튼
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_in or not mgr_in:
            st.sidebar.error("거래처명과 담당자명을 입력하세요!")
        else:
            confirm_order_dialog(cust_in, mgr_in)
    
    if st.sidebar.button("🗑️ 장바구니 비우기", use_container_width=True):
        st.session_state['cart'] = {}; st.rerun()
else:
    st.sidebar.info("🛒 수량을 입력하여 제품을 담아주세요.")

# --- 7. 데이터 필터링 로직 (v5.1 유지) ---
f_df = df.copy()
if st.session_state.selected_cat != "전체":
    c = st.session_state.selected_cat
    if c == "BL":
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("BL", na=False) & 
                    ~f_df['제품군 대그룹 (Product Group)'].str.startswith("BLT", na=False) & 
                    ~f_df['제품군 대그룹 (Product Group)'].str.startswith("BLX", na=False)]
    elif c == "TL":
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("TL", na=False) & 
                    ~f_df['제품군 대그룹 (Product Group)'].str.startswith("TLX", na=False)]
    else:
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(c, na=False)]

if st.session_state.selected_mat != "전체":
    mt = st.session_state.selected_mat
    if mt == "Ti-SLA":
        f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mt == "Roxolid SLA":
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mt == "Roxolid SLActive":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

if st.session_state.selected_spec != "전체":
    sp = st.session_state.selected_spec
    if st.session_state.selected_cat in ["TL", "TLX"]:
        gubun_col = [c for c in f_df.columns if "구분" in c]
        if gubun_col: f_df = f_df[f_df[gubun_col[0]] == sp]
    else:
        f_df = f_df[f_df['직경'] == sp]

# --- 8. 리스트 출력 ---
st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    with st.container(border=True):
        st.write(f"**{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}**")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}")
        q = st.number_input("수량", 0, 100, key=f"q_{idx}")
        if q > 0: st.session_state['cart'][f"row_{idx}"] = {'c': row['주문코드'], 'q': q, 'display_name': row['재질/표면처리']}
        else: st.session_state['cart'].pop(f"row_{idx}", None)
