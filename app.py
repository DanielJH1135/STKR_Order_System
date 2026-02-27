import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v6.0", layout="centered")

# --- 0. 데이터 및 영업사원 로드 (reps.xlsx 연동) ---
@st.cache_data
def load_master_data():
    # 1. 제품 데이터 로드 (021.xxxx 유지 로직 포함)
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        def format_code(c):
            c = str(c).strip()
            if not c or c.lower() == "nan": return ""
            if "." in c:
                parts = c.split(".")
                return f"{parts[0].zfill(3)}.{parts[1]}"
            return c.zfill(3) if c.isdigit() else c
        df['주문코드'] = df['주문코드'].apply(format_code)
        
        # Biomaterial 수동 추가
        bio = pd.DataFrame([
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.3ml', '주문코드': '075.101w', '직경': '-', '길이': '-', '구분': ''},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.7ml', '주문코드': '075.102w', '직경': '-', '길이': '-', '구분': ''}
        ])
        df = pd.concat([df, bio], ignore_index=True)
    except: df = pd.DataFrame()

    # 2. 영업사원 데이터 로드 (reps.xlsx)
    try:
        reps_df = pd.read_excel("reps.xlsx", dtype=str)
        reps_df.columns = [c.strip() for c in reps_df.columns]
        reps_dict = reps_df.set_index('코드')['이름'].to_dict()
        reps_id_dict = reps_df.set_index('코드')['텔레그램ID'].to_dict()
    except:
        # 파일이 없을 때를 대비한 기본값 (과장님)
        reps_dict = {"lee": "이정현 과장"}
        reps_id_dict = {"lee": "1781982606"}

    return df, reps_dict, reps_id_dict

df, reps_dict, reps_id_dict = load_master_data()

# --- 1. 담당자 식별 및 파라미터 ---
try:
    p = st.query_params
    rep_code = p.get("rep", "lee")
    url_cust = p.get("cust", "")
    if isinstance(rep_code, list): rep_code = rep_code[0]
    if isinstance(url_cust, list): url_cust = url_cust[0]
except:
    rep_code, url_cust = "lee", ""

rep_name = reps_dict.get(rep_code, "담당자 미지정")
rep_telegram_id = reps_id_dict.get(rep_code, "1781982606")

# --- 2. 사이드바 (공지사항 + 주문정보 + 장바구니) ---
st.sidebar.markdown("### 📢 공지사항")
with st.sidebar.expander("💰 가격 인상 안내 (필독)", expanded=True):
    st.info("**2026년 3월 1일부로 일부 품목의 가격이 평균 2.5% 인상될 예정입니다.**")
    # 공문 사진 (notice.jpg 파일이 깃허브에 있어야 함)
    if os.path.exists("notice.jpg"):
        st.image("notice.jpg", caption="가격 인상 안내 공문")
    elif os.path.exists("notice.png"):
        st.image("notice.png", caption="가격 인상 안내 공문")
    st.caption("자세한 내용은 담당 영업사원에게 문의바랍니다.")

st.sidebar.divider()
st.sidebar.header("🏢 주문 정보 입력")
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자 성함 (필수)")

# --- 3. 텔레그램 전송 & 팝업 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

@st.dialog("📋 주문 내역을 최종 확인합니다")
def confirm_order_dialog(c_name, m_name):
    st.write(f"🏢 **거래처**: {c_name} | 👤 **담당**: {m_name}")
    st.divider()
    is_ex = st.checkbox("🔄 교환 주문인가요?")
    st.markdown(":red[**※ 교환 보내실 제품은 유효기간 1년이상 남은 제품만 가능합니다.**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : {item['q']}개")
    if st.button("✅ 주문 확정 및 전송", use_container_width=True, type="primary"):
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        msg = f"🔔 [{rep_name}] 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{order_list}\n\n{c_name} {action}"
        if send_telegram(msg, rep_telegram_id)[0]:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()

# --- 4. 메인 UI (필터 로직) ---
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    img = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
    if os.path.exists(img): st.image(img, use_container_width=True)

st.title(f"🛒 [{rep_name}] 주문채널")

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

# 시스템/재질/규격 버튼 (기존 로직 유지)
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
    c_m = st.columns(3)
    for i, m in enumerate(mats):
        with c_m[i]:
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
        blx_d = df[df['제품군 대그룹 (Product Group)'].str.contains("BLX", na=False)]
        specs = sorted(blx_d['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
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

# --- 5. 사이드바 장바구니 & 전송 ---
if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader(f"🛒 담은 품목 ({len(st.session_state['cart'])}건)")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name']} / {v['q']}개")
    st.sidebar.divider()
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_in or not mgr_in: st.sidebar.error("정보를 모두 입력하세요!")
        else: confirm_order_dialog(cust_in, mgr_in)
    if st.sidebar.button("🗑️ 비우기", use_container_width=True):
        st.session_state['cart'] = {}; st.rerun()

# --- 6. 데이터 필터링 ---
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
    else: f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(c, na=False)]

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
    else: f_df = f_df[f_df['직경'] == sp]

st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    with st.container(border=True):
        st.write(f"**{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}**")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}")
        q = st.number_input("주문 수량", 0, 100, key=f"q_{idx}", value=int(st.session_state['cart'].get(f"row_{idx}", {}).get('q', 0)))
        if q > 0:
            full_n = f"{row['제품군 대그룹 (Product Group)']} {row['재질/표면처리']} ({row['직경']}x{row['길이']})"
            st.session_state['cart'][f"row_{idx}"] = {'c': row['주문코드'], 'q': q, 'display_name': full_n}
        else: st.session_state['cart'].pop(f"row_{idx}", None)


