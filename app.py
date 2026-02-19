import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 0. 담당자 및 URL 파라미터 설정 (가장 먼저!) ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}

# 변수 초기화 (NameError 방지)
rep_key = "lee"
url_cust = ""

try:
    if hasattr(st, "query_params"):
        rep_key = st.query_params.get("rep", "lee")
        url_cust = st.query_params.get("cust", "")
        if isinstance(rep_key, list): rep_key = rep_key[0]
        if isinstance(url_cust, list): url_cust = url_cust[0]
except:
    pass

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

# --- 최상단 로고 중앙 배치 ---
if os.path.exists("logo.png") or os.path.exists("logo.jpg"):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        img_p = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
        st.image(img_p, use_container_width=True)

# --- 1. 텔레그램 설정 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 로드 및 보정 ---
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

# --- 5. 메인 UI (타이틀 및 3단 버튼) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.write("### 1️⃣ 시스템 선택")
r1, r2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c1 = st.columns(3)
for i, cat in enumerate(r1):
    with c1[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()
c2 = st.columns(3)
for i, cat in enumerate(r2):
    with c2[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()

if st.session_state.selected_cat != "전체" and st.session_state.selected_cat != "Biomaterial":
    st.write("### 2️⃣ 재질/표면처리 선택")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c3 = st.columns(3)
    for i, m in enumerate(mats):
        with c3[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur_cat = st.session_state.selected_cat
    # [수정] TL/TLX 규격 명칭 명확화
    specs = ["3.3", "4.1", "4.8"] if cur_cat in ["BL", "BLT"] else ["S (Standard/2.8mm)", "SP (Plus/1.8mm)"]
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

# --- 6. 사이드바 (정보 입력 및 장바구니 복구) ---
st.sidebar.header("🏢 주문 정보 입력")
cust_name_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_in = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]}.. / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_in or not mgr_name_in: st.sidebar.error("정보를 입력하세요!")
        else: confirm_order_dialog(cust_name_in, mgr_name_in)

# --- 7. 데이터 필터링 (S/SP 정밀 분리 로직) ---
f_df = df.copy()
# 1단계 시스템
if st.session_state.selected_cat != "전체":
    target = st.session_state.selected_cat.upper()
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.upper().str.contains(target, na=False)]

# 2단계 재질
if st.session_state.selected_mat != "전체":
    m = st.session_state.selected_mat
    if "SLActive" in m: f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif "SLA" in m: f_df = f_df[f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3단계 규격 (S/SP 핵심 수정)
if st.session_state.selected_spec != "전체":
    s = st.session_state.selected_spec
    if st.session_state.selected_cat in ["BL", "BLT"]:
        f_df = f_df[f_df['직경'] == s]
    else: # TL, TLX
        if "S (" in s: # S (Standard / 2.8mm)
            # "S"는 포함하되 "SP"나 "Plus"는 절대 포함하면 안 됨
            f_df = f_df[f_df['재질/표면처리'].str.contains(r'\bS\b', regex=True, na=False) & ~f_df['재질/표면처리'].str.contains("SP", na=False)]
        else: # SP (Plus / 1.8mm)
            f_df = f_df[f_df['재질/표면처리'].str.contains("SP", na=False) | f_df['재질/표면처리'].str.contains("Plus", na=False)]

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
