import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 0. 담당자 및 URL 파라미터 설정 (NameError 방지) ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}

# 기본값 설정
rep_key = "lee"
url_cust = ""

try:
    # 최신 버전 스트림릿 파라미터 읽기
    p = st.query_params
    if "rep" in p: rep_key = p["rep"]
    if "cust" in p: url_cust = p["cust"]
except:
    pass

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

# --- 최상단 로고 중앙 배치 ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    elif os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)

# --- 1. 텔레그램 설정 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 로드 ---
@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        # Biomaterial 수동 추가
        bio = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio)], ignore_index=True)
        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. 최종 확인 팝업 ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(c_name, m_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    is_ex = st.checkbox("🔄 교환 주문인가요?")
    st.markdown(":red[**※ 교환 제품은 유효기간 1년 이상 남은 제품만 가능합니다.**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        items = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{items}\n\n{c_name} {action}"
        if send_telegram(msg, current_rep['id'])[0]:
            st.success("전송 완료!"); st.session_state['cart'] = {}; st.rerun()

# --- 5. 메인 UI (타이틀 유지) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.write("### 1️⃣ 시스템 선택")
r1, r2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c_row1 = st.columns(3)
for i, cat in enumerate(r1):
    with c_row1[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()
c_row2 = st.columns(3)
for i, cat in enumerate(r2):
    with c_row2[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()

# 2단계 재질 선택
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c_mat = st.columns(3)
    for i, m in enumerate(mats):
        with c_mat[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# 3단계 규격 선택
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격")
    cur = st.session_state.selected_cat
    specs = ["3.3", "4.1", "4.8"] if cur in ["BL", "BLT"] else ["S (2.8mm)", "SP (1.8mm)"]
    c_spec = st.columns(len(specs))
    for i, s in enumerate(specs):
        with c_spec[i]:
            if st.button(s, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                st.session_state.selected_spec = s
                st.rerun()

if st.button("🔄 검색 초기화", use_container_width=True):
    st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = "전체", "전체", "전체"
    st.rerun()

st.divider()

# --- 6. 사이드바 복구 ---
st.sidebar.header("🏢 주문 정보 입력")
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]}.. / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_in or not mgr_in: st.sidebar.error("정보를 입력하세요!")
        else: confirm_order_dialog(cust_in, mgr_in)

# --- 7. 데이터 필터링 로직 ---
f_df = df.copy()

# 1단계 시스템 필터링
if st.session_state.selected_cat != "전체":
    cat_target = st.session_state.selected_cat.upper()
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.upper().str.contains(cat_target, na=False)]

# 2단계 재질 필터링 (SLA / SLActive 분리)
if st.session_state.selected_mat != "전체":
    m_target = st.session_state.selected_mat
    if "SLActive" in m_target:
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    else: # SLA (Ti-SLA 또는 Roxolid SLA)
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3단계 규격 필터링 (S/SP 핵심 수정)
if st.session_state.selected_spec != "전체":
    spec_target = st.session_state.selected_spec
    if st.session_state.selected_cat in ["BL", "BLT"]:
        f_df = f_df[f_df['직경'] == spec_target]
    else: # TL, TLX
        if "S (2.8mm)" in spec_target:
            # S는 포함하고 SP는 포함하지 않는 것 (유연한 검색)
            f_df = f_df[f_df['재질/표면처리'].str.contains("S", na=False) & ~f_df['재질/표면처리'].str.contains("SP", na=False)]
        else: # SP (1.8mm)
            f_df = f_df[f_df['재질/표면처리'].str.contains("SP", na=False)]

# --- 8. 리스트 출력 ---
st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    is_bio = row['제품군 대그룹 (Product Group)'] == 'Biomaterial'
    with st.container(border=True):
        title = f"{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}" if not is_bio else row['재질/표면처리']
        st.markdown(f"#### {title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']}" if not is_bio else "📍 Biomaterial")
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량", 0, 100, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        if q > 0: st.session_state['cart'][k] = {'c': row['주문코드'], 'q': q, 'display_name': title}
        else: st.session_state['cart'].pop(k, None)
