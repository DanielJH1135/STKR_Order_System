import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v3.1", layout="centered")

# --- 최상단 로고 중앙 배치 ---
if os.path.exists("logo.png") or os.path.exists("logo.jpg"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        img_path = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
        st.image(img_path, use_container_width=True)

# --- 1. 담당자 및 텔레그램 설정 ---
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
    except Exception as e: return False, str(e)

# --- 2. 데이터 보정 및 로드 ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c and any(char.isdigit() for char in c):
        parts = c.split(".", 1)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1]
        if suffix.isdigit(): suffix = suffix.ljust(4, '0')
        return f"{prefix}.{suffix}"
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        new_items = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        df = pd.concat([df, pd.DataFrame(new_items)], ignore_index=True)
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. 정밀 필터링 함수 (핵심 수정) ---
def is_exact_match(val, target):
    if target == "전체": return True
    val, target = str(val).strip().upper(), str(target).strip().upper()
    # 1. 완전 일치 여부 확인
    if val == target: return True
    # 2. "BL (Bone Level)" 처럼 괄호가 포함된 경우를 위한 정규식 (BLX와 구분)
    pattern = rf'(?:^|[^A-Z0-9]){re.escape(target)}(?:[^A-Z0-9]|$)'
    return bool(re.search(pattern, val))

# --- 5. 최종 확인 팝업창 ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown(":red[**※ 교환 보내실 제품은 유효기간 1년 이상 남은 제품만 가능합니다.**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        msg = f"🔔 [주문접수]\n🏢 {cust_name}\n👤 {mgr_name}\n\n{order_list}\n\n{cust_name} {action}"
        if send_telegram(msg, SALES_REPS["lee"]["id"])[0]:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()

# --- 6. 메인 UI ---
st.title("🛒 임플란트 퀵 주문")

# 1단계: 시스템 선택
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

# 2단계: 재질/표면처리 (고정된 버튼으로 필터링)
if st.session_state.selected_cat != "전체" and st.session_state.selected_cat != "Biomaterial":
    st.write("### 2️⃣ 재질/표면처리 선택")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c3 = st.columns(3)
    for i, m in enumerate(mats):
        with c3[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# 3단계: 상세 규격
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur_cat = st.session_state.selected_cat
    specs = ["3.3", "4.1", "4.8"] if cur_cat in ["BL", "BLT"] else ["S (Standard)", "SP (Standard Plus)"]
    c4 = st.columns(len(specs))
    for i, s in enumerate(specs):
        with c4[i]:
            if st.button(s, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                st.session_state.selected_spec = s
                st.rerun()

if st.button("🔄 검색 조건 초기화", use_container_width=True):
    st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = "전체", "전체", "전체"
    st.rerun()

st.divider()

# --- 7. 데이터 필터링 로직 (초정밀 매핑) ---
f_df = df.copy()

# 1단계: 시스템 필터
if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'].apply(lambda x: is_exact_match(x, st.session_state.selected_cat))]

# 2단계: 재질 필터 (Exact Match 원칙 적용)
if st.session_state.selected_mat != "전체":
    target_mat = st.session_state.selected_mat
    # Ti-SLA 인 경우 데이터에서 "Ti SLA" 혹은 "SLA"를 찾되 SLActive는 배제
    if target_mat == "Ti-SLA":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif target_mat == "Roxolid SLA":
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif target_mat == "Roxolid SLActive":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3단계: 규격 필터
if st.session_state.selected_spec != "전체":
    s = st.session_state.selected_spec
    if st.session_state.selected_cat in ["BL", "BLT"]:
        f_df = f_df[f_df['직경'] == s]
    else:
        target_type = s.split("(")[0].strip() # "S" 또는 "SP"
        f_df = f_df[f_df['재질/표면처리'].str.contains(target_type, na=False)]

st.write(f"🔍 검색 결과: **{len(f_df)}건**")

# 사이드바 입력창
st.sidebar.header("🏢 주문 정보")
cust_name = st.sidebar.text_input("거래처명", value=url_cust)
mgr_name = st.sidebar.text_input("담당자명")

# 제품 리스트 출력
for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_bio = row['제품군 대그룹 (Product Group)'] == 'Biomaterial'
    with st.container(border=True):
        title = f"{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}" if not is_bio else row['재질/표면처리']
        st.markdown(f"#### {title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}" if not is_bio else "📍 Biomaterial")
        
        prev = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("수량", 0, 100, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][item_key] = {'c': row['주문코드'], 'q': q, 'display_name': title}
        else: st.session_state['cart'].pop(item_key, None)
