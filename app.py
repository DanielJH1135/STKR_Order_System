import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v4.1", layout="centered")

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

# --- 중앙 로고 배치 ---
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    img = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
    if os.path.exists(img): st.image(img, use_container_width=True)

# --- 1. 데이터 로드 및 0 누락 방지 ---
def format_code_strict(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".")
        # 앞자리가 3자리 미만인 숫자일 때만 0을 채움 (예: 21.4110 -> 021.4110)
        prefix = parts[0].zfill(3) if (parts[0].isdigit() and len(parts[0]) < 3) else parts[0]
        return f"{prefix}.{parts[1]}"
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        # 엑셀 로드 (반드시 문자열로 읽기)
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_code_strict)
        
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
cats_layout = [["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]]
for row in cats_layout:
    cols = st.columns(3)
    for i, c in enumerate(row):
        with cols[i]:
            if st.button(c, use_container_width=True, type="primary" if st.session_state.selected_cat == c else "secondary"):
                st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = c, "전체", "전체"
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

# [STEP 3] 상세 규격 (시스템별 자동 매핑)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    
    if "TL" in cur:
        # TL/TLX는 과장님이 만드신 '구분' 열 (S, SP) 사용
        specs = ["S", "SP"]
    else:
        # BL/BLT/BLX는 엑셀 데이터에서 실제 존재하는 '직경' 목록을 중복 없이 가져와 정렬
        # (과장님이 BLX에 3.5~6.5 넣으신 걸 자동으로 버튼화합니다)
        temp_df = df[df['제품군 대그룹 (Product Group)'].str.contains(cur, na=False)]
        specs = sorted(temp_df['직경'].unique(), key=lambda x: (float(x) if x.replace('.','').isdigit() else 99))

    if specs:
        s_cols = st.columns(len(specs))
        for i, s in enumerate(specs):
            with s_cols[i]:
                # 버튼 라벨 예쁘게 다듬기
                label = f"S (2.8mm)" if s == "S" else (f"SP (1.8mm)" if s == "SP" else f"Ø {s}")
                if st.button(label, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s
                    st.rerun()

if st.button("🔄 검색 조건 초기화", use_container_width=True):
    st.session_state.selected_cat = st.session_state.selected_mat = st.session_state.selected_spec = "전체"
    st.rerun()

st.divider()

# --- 4. 정밀 필터링 로직 ---
f_df = df.copy()

# 시스템 필터링
if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(st.session_state.selected_cat, na=False)]

# 재질 필터링
if st.session_state.selected_mat != "전체":
    m_t = st.session_state.selected_mat
    if m_t == "Ti-SLA":
        f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif m_t == "Roxolid SLA":
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif m_t == "Roxolid SLActive":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 규격 필터링 (구분 열 적극 활용)
if st.session_state.selected_spec != "전체":
    spec = st.session_state.selected_spec
    if "TL" in st.session_state.selected_cat:
        # TL 계열은 과장님이 추가한 '구분' 열로 매칭
        if '구분' in f_df.columns:
            f_df = f_df[f_df['구분'] == spec]
    else:
        # BL 계열은 '직경' 열로 매칭
        f_df = f_df[f_df['직경'] == spec]

# --- 5. 사이드바 및 리스트 출력 ---
st.sidebar.header("🏢 주문자 정보")
cust_name = st.sidebar.text_input("거래처명", value=url_cust)
mgr_name = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader(f"🛒 담은 품목 ({len(st.session_state['cart'])}건)")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name']} / {v['q']}개")

st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    with st.container(border=True):
        title = f"{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}"
        st.markdown(f"#### {title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}")
        q = st.number_input("수량", 0, 100, key=f"q_{idx}")
