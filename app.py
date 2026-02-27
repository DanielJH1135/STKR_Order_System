import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v6.2", layout="centered")

# --- 0. 데이터 및 영업사원 로드 ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        def format_code(c):
            c = str(c).strip()
            if not c or c.lower() == "nan": return ""
            if "." in c:
                parts = c.split(".")
                prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
                return f"{prefix}.{parts[1]}"
            return c.zfill(3) if c.isdigit() else c
        df['주문코드'] = df['주문코드'].apply(format_code)
        
        bio = pd.DataFrame([
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.3ml', '주문코드': '075.101w', '직경': '-', '길이': '-', '구분': ''},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '재질/표면처리': 'Emdogain 0.7ml', '주문코드': '075.102w', '직경': '-', '길이': '-', '구분': ''}
        ])
        df = pd.concat([df, bio], ignore_index=True)
    except: df = pd.DataFrame()

    # 영업사원 데이터 (reps.xlsx)
    reps_dict = {"lee": "이정현 과장", "park": "박성배 소장", "jang": "장세진 차장"}
    reps_id_dict = {"lee": "1781982606", "park": "8613810133", "jang": "8254830024"}
    
    try:
        if os.path.exists("reps.xlsx"):
            reps_df = pd.read_excel("reps.xlsx", dtype=str)
            reps_dict.update(reps_df.set_index('코드')['이름'].to_dict())
            reps_id_dict.update(reps_df.set_index('코드')['텔레그램ID'].to_dict())
    except: pass

    return df, reps_dict, reps_id_dict

df, reps_dict, reps_id_dict = load_master_data()

# --- 1. 담당자 및 파라미터 ---
p = st.query_params
rep_code = str(p.get("rep", "lee")).lower()
url_cust = p.get("cust", "")
rep_name = reps_dict.get(rep_code, "담당자 미지정")
rep_telegram_id = reps_id_dict.get(rep_code, reps_id_dict["lee"])

# --- 2. 사이드바 (공지사항 + 주문정보) ---
st.sidebar.markdown("### 📢 공지사항")
with st.sidebar.expander("💰 가격 인상 안내 (필독)", expanded=True):
    if os.path.exists("notice.jpg"): st.image("notice.jpg")
    st.info("**2026년 3월 1일부로 일부 품목 가격 인상**")

st.sidebar.divider()
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자 성함 (필수)")

# --- 3. 텔레그램 및 팝업 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

@st.dialog("📋 주문 내역 확인")
def confirm_order_dialog(c_n, m_n):
    is_ex = st.checkbox("🔄 교환 주문인가요?")
    st.markdown(":red[**※ 유효기간 1년이상 제품만 가능**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• {item['display_name']} : {item['q']}개")
    if st.button("✅ 주문 전송", use_container_width=True, type="primary"):
        items = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        msg = f"🔔 [{rep_name}] 주문접수\n🏢 {c_n}\n👤 {m_n}\n\n{items}\n\n{c_n} {action}"
        if send_telegram(msg, rep_telegram_id)[0]:
            st.success("완료!"); st.session_state['cart'] = {}; st.rerun()

# --- 4. 메인 화면 & 필터링 (핵심 수정 파트) ---
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    img = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
    if os.path.exists(img): st.image(img, use_container_width=True)

st.title(f"🛒 [{rep_name}] 주문채널")

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

# [STEP 1] 시스템
st.write("### 1️⃣ 시스템 선택")
r1, r2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c_rows = [st.columns(3), st.columns(3)]
for idx, row_cats in enumerate([r1, r2]):
    for i, cat in enumerate(row_cats):
        with c_rows[idx][i]:
            if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
                st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
                st.rerun()

# [STEP 2] 재질 (현재 시스템에서 가능한 재질만 추출)
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c_m = st.columns(3)
    for i, m in enumerate(mats):
        with c_m[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [STEP 3] 상세 규격 (데이터가 있는 것만 버튼으로 생성)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    mat = st.session_state.selected_mat
    
    # [핵심] 현재 선택된 시스템+재질에 실제로 존재하는 데이터만 필터링
    temp_df = df[df['제품군 대그룹 (Product Group)'].str.contains(cur, na=False)]
    if mat == "Ti-SLA":
        temp_df = temp_df[~temp_df['재질/표면처리'].str.contains("Roxolid", na=False) & temp_df['재질/표면처리'].str.contains("SLA", na=False)]
    elif mat == "Roxolid SLA":
        temp_df = temp_df[temp_df['재질/표면처리'].str.contains("Roxolid", na=False) & ~temp_df['재질/표면처리'].str.contains("SLActive", na=False)]
    else: # SLActive
        temp_df = temp_df[temp_df['재질/표면처리'].str.contains("SLActive", na=False)]

    # [수정] TL도 BL처럼 직경(숫자) 버튼을 보여주되, 구분(S, SP) 정보를 병기
    if "TL" in cur:
        # 데이터가 있는 '직경' 목록 추출
        available_specs = sorted(temp_df['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
        s_cols = st.columns(len(available_specs) if available_specs else 1)
        for i, s in enumerate(available_specs):
            with s_cols[i]:
                # 해당 직경의 첫 번째 행에서 '구분' 값을 가져와 라벨에 표시 (예: 3.3 (S))
                gubun = temp_df[temp_df['직경'] == s]['구분'].iloc[0] if '구분' in temp_df.columns else ""
                label = f"Ø {s} ({gubun})" if gubun else f"Ø {s}"
                if st.button(label, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s; st.rerun()
    else:
        # BL 계열 동적 버튼
        available_specs = sorted(temp_df['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
        s_cols = st.columns(len(available_specs) if available_specs else 1)
        for i, s in enumerate(available_specs):
            with s_cols[i]:
                if st.button(f"Ø {s}", use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s; st.rerun()

st.divider()

# --- 5. 데이터 필터링 및 출력 ---
f_df = df.copy()
# (기존 필터 로직 유지...)
if st.session_state.selected_cat != "전체":
    c = st.session_state.selected_cat
    if c == "BL": f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("BL", na=False) & ~f_df['제품군 대그룹 (Product Group)'].str.startswith("BLT", na=False) & ~f_df['제품군 대그룹 (Product Group)'].str.startswith("BLX", na=False)]
    elif c == "TL": f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("TL", na=False) & ~f_df['제품군 대그룹 (Product Group)'].str.startswith("TLX", na=False)]
    else: f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(c, na=False)]

if st.session_state.selected_mat != "전체":
    mt = st.session_state.selected_mat
    if mt == "Ti-SLA": f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mt == "Roxolid SLA": f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mt == "Roxolid SLActive": f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

if st.session_state.selected_spec != "전체":
    f_df = f_df[f_df['직경'] == st.session_state.selected_spec]

# 결과 출력
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

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader(f"🛒 담은 품목 ({len(st.session_state['cart'])}건)")
    for v in st.session_state['cart'].values(): st.sidebar.caption(f"• {v['display_name']} / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_in or not mgr_in: st.sidebar.error("정보 입력 필수!")
        else: confirm_order_dialog(cust_in, mgr_in)
