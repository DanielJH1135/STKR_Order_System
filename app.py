import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v6.4", layout="centered")

# --- 0. 데이터 로드 ---
@st.cache_data
def load_master_data():
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        def format_code(c):
            c = str(c).strip()
            if not c or c.lower() == "nan" or c == "": return ""
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
        return df
    except: return pd.DataFrame()

df = load_master_data()

# --- 0-1. 영업사원 설정 (이전 히스토리 복구) ---
reps_dict = {"lee": "이정현 과장", "park": "박성배 소장", "jang": "장세진 차장"}
reps_id_dict = {"lee": "6769868107", "park": "8613810133", "jang": "8254830024"} # 아이디 확인 후 수정 필요

try:
    if os.path.exists("reps.xlsx"):
        reps_df = pd.read_excel("reps.xlsx", dtype=str)
        reps_dict.update(reps_df.set_index('코드')['이름'].to_dict())
        reps_id_dict.update(reps_df.set_index('코드')['텔레그램ID'].to_dict())
except: pass

p = st.query_params
rep_code = str(p.get("rep", "lee")).lower()
rep_name = reps_dict.get(rep_code, "담당자 미지정")
rep_telegram_id = reps_id_dict.get(rep_code, reps_id_dict["lee"])
url_cust = p.get("cust", "")

# --- 2. 사이드바 & 다이얼로그 ---
st.sidebar.markdown("### 📢 공지사항")
with st.sidebar.expander("💰 가격 인상 안내", expanded=True):
    if os.path.exists("notice.jpg"): st.image("notice.jpg")
    st.info("**2026년 3월 1일부 일부제품 평균2.5% 가격인상이 있습니다.**")

st.sidebar.divider()
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자 성함 (필수)")

TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

@st.dialog("📋 주문 확인")
def confirm_order_dialog(c_n, m_n):
    is_ex = st.checkbox("🔄 교환 주문")
    st.markdown(":red[**※ 교환 보내실 제품은 유효기간 1년이상 제품만 가능합니다.**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• {item['display_name']} : {item['q']}개")
    if st.button("✅ 주문 전송", use_container_width=True, type="primary"):
        items = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        msg = f"🔔 [{rep_name}] 주문접수\n🏢 {c_n}\n👤 {m_n}\n\n{items}\n\n{c_n} {action}"
        if send_telegram(msg, rep_telegram_id)[0]:
            st.success("완료!"); st.session_state['cart'] = {}; st.rerun()

# --- 4. 메인 UI ---
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

# [STEP 2] 재질
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c_m = st.columns(3)
    for i, m in enumerate(mats):
        with c_m[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [STEP 3] 상세 규격 (BL/TL 필터 수정)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur = st.session_state.selected_cat
    mat = st.session_state.selected_mat
    
    # [수정] 정확한 그룹 필터링
    if cur == "BL":
        temp_df = df[df['제품군 대그룹 (Product Group)'].str.startswith("BL", na=False) & ~df['제품군 대그룹 (Product Group)'].str.startswith(("BLT", "BLX"), na=False)]
    elif cur == "TL":
        temp_df = df[df['제품군 대그룹 (Product Group)'].str.startswith("TL", na=False) & ~df['제품군 대그룹 (Product Group)'].str.startswith("TLX", na=False)]
    else:
        temp_df = df[df['제품군 대그룹 (Product Group)'].str.contains(cur, na=False)]

    # 재질 필터링
    if mat == "Ti-SLA":
        temp_df = temp_df[~temp_df['재질/표면처리'].str.contains("Roxolid", na=False) & temp_df['재질/표면처리'].str.contains("SLA", na=False) & ~temp_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mat == "Roxolid SLA":
        temp_df = temp_df[temp_df['재질/표면처리'].str.contains("Roxolid", na=False) & ~temp_df['재질/표면처리'].str.contains("SLActive", na=False)]
    else: # SLActive
        temp_df = temp_df[temp_df['재질/표면처리'].str.contains("SLActive", na=False)]

    available_specs = sorted(temp_df['직경'].unique(), key=lambda x: float(x) if x.replace('.','').isdigit() else 0)
    
    if available_specs:
        s_cols = st.columns(len(available_specs) if len(available_specs) <= 5 else 5)
        for i, s in enumerate(available_specs):
            with s_cols[i % 5]:
                # gubun (S, SP 등) 가져오기 및 nan 처리
                res = temp_df[temp_df['직경'] == s]['구분']
                gubun = res.iloc[0] if not res.empty else ""
                clean_gubun = "" if (str(gubun).lower() == "nan" or not gubun) else str(gubun)
                label = f"Ø {s} ({clean_gubun})" if clean_gubun else f"Ø {s}"
                
                if st.button(label, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s; st.rerun()

st.divider()

# --- 5. 최종 필터링 로직 ---
f_df = df.copy()
if st.session_state.selected_cat != "전체":
    c = st.session_state.selected_cat
    if c == "BL":
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("BL", na=False) & ~f_df['제품군 대그룹 (Product Group)'].str.startswith(("BLT", "BLX"), na=False)]
    elif c == "TL":
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.startswith("TL", na=False) & ~f_df['제품군 대그룹 (Product Group)'].str.startswith("TLX", na=False)]
    else:
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.contains(c, na=False)]

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
