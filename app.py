import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v3.2", layout="centered")

# --- 0. 담당자 설정 및 URL 파라미터 ---
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

# --- 1. 데이터 로드 (021.xxxx 유지) ---
def format_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".")
        return f"{parts[0].zfill(3)}.{parts[1]}"
    return c.zfill(3) if c.isdigit() else c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    if not os.path.exists(file_path): return None, "파일 없음"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_code)
        
        # Biomaterial 추가
        bio = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        return pd.concat([df, pd.DataFrame(bio)], ignore_index=True), "성공"
    except Exception as e: return None, str(e)

df, _ = load_data()

# --- 2. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

# --- 3. 필터링 UI (단계별) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [STEP 1] 시스템
st.write("### 1️⃣ 시스템 선택")
cats = [["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]]
for row in cats:
    cols = st.columns(3)
    for i, c in enumerate(row):
        with cols[i]:
            if st.button(c, use_container_width=True, type="primary" if st.session_state.selected_cat == c else "secondary"):
                st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = c, "전체", "전체"
                st.rerun()

# [STEP 2] 재질
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질 선택")
    m_cols = st.columns(3)
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    for i, m in enumerate(mats):
        with m_cols[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [STEP 3] 상세 규격 (과장님 요청 반영)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    # BL 계열은 직경 숫자, TL 계열은 S/SP 명칭
    specs = ["3.3", "4.1", "4.8"] if "BL" in cur else ["S (2.8mm)", "SP (1.8mm)"]
    s_cols = st.columns(len(specs))
    for i, s in enumerate(specs):
        with s_cols[i]:
            if st.button(s, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                st.session_state.selected_spec = s
                st.rerun()

st.divider()

# --- 4. 데이터 필터링 로직 (정밀 타격) ---
f_df = df.copy()

# 1단계: 시스템
if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(st.session_state.selected_cat, na=False)]

# 2단계: 재질
if st.session_state.selected_mat != "전체":
    m_target = st.session_state.selected_mat
    if "Ti-SLA" in m_target:
        f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif "Roxolid SLA" in m_target:
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif "SLActive" in m_target:
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3단계: 상세 규격 (과장님 데이터 형식 "TL-SP(1.8mm)" 기반 필터링)
if st.session_state.selected_spec != "전체":
    spec = st.session_state.selected_spec
    if "BL" in st.session_state.selected_cat:
        f_df = f_df[f_df['직경'] == spec]
    else: # TL 계열
        if "SP (1.8mm)" in spec:
            # 재질/표면처리 칸에 'SP(1.8mm)'가 포함된 것 필터링
            f_df = f_df[f_df['재질/표면처리'].str.contains("SP\(1.8mm\)", na=False) | f_df['재질/표면처리'].str.contains("Plus", na=False)]
        else: # S (2.8mm)
            f_df = f_df[f_df['재질/표면처리'].str.contains("S\(2.8mm\)", na=False) & ~f_df['재질/표면처리'].str.contains("SP", na=False)]

# --- 5. 사이드바 및 리스트 출력 ---
st.sidebar.header("🏢 주문 정보")
c_name = st.sidebar.text_input("거래처명", value=url_cust)
m_name = st.sidebar.text_input("담당자명")

st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    with st.container(border=True):
        st.write(f"**{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}**")
        st.code(row['주문코드'])
        q = st.number_input("수량", 0, 100, key=f"q_{idx}")
        if q > 0: st.session_state['cart'][k] = {'c': row['주문코드'], 'q': q, 'display_name': row['재질/표면처리']}
