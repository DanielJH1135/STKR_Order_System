import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v4.5", layout="centered")

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

# --- 1. 데이터 로드 및 021.xxxx 유지 로직 ---
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
        # dtype=str로 읽어 엑셀의 숫자 변환 방지
        df = pd.read_excel(file_path, dtype=str)
        # 열 이름 공백 제거 (매우 중요)
        df.columns = [c.strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_code_final)
        
        # Biomaterial 추가 (구분 열 포함)
        bio = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.3ml', '주문코드': '075.101w', '직경': '-', '길이': '-', '구분': ''},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.7ml', '주문코드': '075.102w', '직경': '-', '길이': '-', '구분': ''}
        ]
        return pd.concat([df, pd.DataFrame(bio)], ignore_index=True), "성공"
    except Exception as e: return None, str(e)

df, _ = load_data()

# --- 2. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

# --- 3. 메인 화면 ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [STEP 1] 시스템 선택
st.write("### 1️⃣ 시스템 선택")
row1, row2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c1 = st.columns(3)
for i, cat in enumerate(row1):
    with c1[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()
c2 = st.columns(3)
for i, cat in enumerate(row2):
    with c2[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()

# [STEP 2] 재질 선택
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    m_cols = st.columns(3)
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    for i, m in enumerate(mats):
        with m_cols[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [STEP 3] 상세 규격 (과장님 요청 100% 반영)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    
    if cur == "BL":
        specs = ["3.3", "4.1", "4.8"] # 2.9 제외
    elif cur == "BLT":
        specs = ["2.9", "3.3", "4.1", "4.8"] # 2.9 포함
    elif cur == "BLX":
        # BLX는 엑셀에 있는 직경 수치를 동적으로 가져오되 3.5 이상만 정렬
        blx_df = df[df['제품군 대그룹 (Product Group)'].str.contains("BLX", na=False)]
        specs = sorted(blx_df['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
    elif "TL" in cur:
        specs = ["S", "SP"] # 구분 열 기반
    else: specs = []

    if specs:
        s_cols = st.columns(len(specs))
        for i, s in enumerate(specs):
            with s_cols[i]:
                # 라벨 표시 보정
                label = f"S (2.8mm)" if s == "S" else (f"SP (1.8mm)" if s == "SP" else f"Ø {s}")
                if st.button(label, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s
                    st.rerun()

if st.button("🔄 검색 조건 초기화", use_container_width=True):
    st.session_state.selected_cat = st.session_state.selected_mat = st.session_state.selected_spec = "전체"
    st.rerun()

st.divider()

# --- 4. 데이터 필터링 로직 ---
f_df = df.copy()

# 1) 시스템 필터 (BL, BLT, BLX 완전 격리)
if st.session_state.selected_cat != "전체":
    c = st.session_state.selected_cat
    if c == "BL":
        # BL만 포함하고 T나 X가 뒤에 붙은 건 제외
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(r'^BL[^TX]', regex=True, na=False) | (f_df['제품군 대그룹 (Product Group)'] == 'BL')]
    else:
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(c, na=False)]

# 2) 재질 필터
if st.session_state.selected_mat != "전체":
    m_t = st.session_state.selected_mat
    if m_t == "Ti-SLA":
        f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif m_t == "Roxolid SLA":
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif m_t == "Roxolid SLActive":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3) 규격 필터 (구분 열 최우선 적용)
if st.session_state.selected_spec != "전체":
    spec = st.session_state.selected_spec
    if "TL" in st.session_state.selected_cat:
        # 새로 추가하신 '구분' 열이 있다면 그 값을 정확히 매칭
        if '구분' in f_df.columns:
            f_df = f_df[f_df['구분'] == spec]
    else:
        # BL 계열은 직경 수치로 매칭
        f_df = f_df[f_df['직경'] == spec]

# --- 5. 사이드바 및 출력 ---
st.sidebar.header("🏢 주문자 정보")
cust_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader(f"🛒 담은 품목 ({len(st.session_state['cart'])}건)")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name']} / {v['q']}개")

st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    with st.container(border=True):
        st.write(f"**{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}**")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}")
        q = st.number_input("수량", 0, 100, key=f"q_{idx}")
        # 장바구니 업데이트 로직 (생략 가능하나 유지를 위해)
        k = f"row_{idx}"
        if q > 0: st.session_state['cart'][k] = {'c': row['주문코드'], 'q': q, 'display_name': row['재질/표면처리']}
        else: st.session_state['cart'].pop(k, None)
