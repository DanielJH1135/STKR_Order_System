import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 0. 담당자 및 URL 파라미터 설정 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}

rep_key = "lee"
url_cust = ""
try:
    p = st.query_params
    rep_key = p.get("rep", "lee")
    url_cust = p.get("cust", "")
    if isinstance(rep_key, list): rep_key = rep_key[0]
    if isinstance(url_cust, list): url_cust = url_cust[0]
except:
    pass

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

# --- [중앙 로고] ---
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    img_path = "logo.png" if os.path.exists("logo.png") else "logo.jpg"
    if os.path.exists(img_path): st.image(img_path, use_container_width=True)

# --- 1. 텔레그램 설정 ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 로드 및 주문코드 '0' 보존 로직 ---
def format_order_code_strict(c):
    """021.1234 형식을 무조건 유지하는 강력한 보정 함수"""
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    # 숫자로만 되어 있거나 점이 포함된 경우 처리
    if "." in c:
        parts = c.split(".")
        # 앞자리를 3자리로 채움 (예: 21 -> 021)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1]
        return f"{prefix}.{suffix}"
    elif c.isdigit():
        return c.zfill(3) # 점이 없어도 최소 3자리는 유지
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        # dtype=str로 읽어야 엑셀이 멋대로 0을 지우는 걸 방지함
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        # Biomaterial 추가
        bio = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio)], ignore_index=True)
        
        # [핵심] 모든 주문코드에 대해 0 누락 방지 처리
        df['주문코드'] = df['주문코드'].apply(format_order_code_strict)
        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 상태 관리 ---
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. 팝업창 ---
@st.dialog("📋 주문 내역 확인")
def confirm_order_dialog(c_name, m_name):
    st.write("주문 내용을 확인해 주세요.")
    is_ex = st.checkbox("🔄 교환 주문 (선납)")
    st.markdown(":red[**※ 유효기간 1년 이상 남은 제품만 교환 가능합니다.**]")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    if st.button("🚀 최종 주문 전송", use_container_width=True, type="primary"):
        items = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{items}\n\n{c_name} {action}"
        if send_telegram(msg, current_rep['id'])[0]:
            st.success("전송 성공!"); st.session_state['cart'] = {}; st.rerun()

# --- 5. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [1단계] 시스템 선택
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

# [2단계] 재질 선택 (Ti vs Roxolid 완벽 분리)
if st.session_state.selected_cat not in ["전체", "Biomaterial"]:
    st.write("### 2️⃣ 재질/표면처리")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c3 = st.columns(3)
    for i, m in enumerate(mats):
        with c3[i]:
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [3단계] 상세 규격 (S=2.8mm, SP=1.8mm 강제 매핑)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격")
    cur = st.session_state.selected_cat
    specs = ["3.3", "4.1", "4.8"] if cur in ["BL", "BLT"] else ["S (2.8mm)", "SP (1.8mm)"]
    c4 = st.columns(len(specs))
    for i, s in enumerate(specs):
        with c4[i]:
            if st.button(s, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                st.session_state.selected_spec = s
                st.rerun()

if st.button("🔄 검색 초기화", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state.selected_mat = "전체"; st.session_state.selected_spec = "전체"
    st.rerun()

# --- 6. 사이드바 ---
st.sidebar.header("🏢 주문자 정보")
cust_in = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_in = st.sidebar.text_input("담당자 성함 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]}.. / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_in or not mgr_in: st.sidebar.error("정보를 입력하세요!")
        else: confirm_order_dialog(cust_in, mgr_in)

# --- 7. [정밀 타격] 데이터 필터링 로직 ---
f_df = df.copy()

# 1) 시스템 필터
if st.session_state.selected_cat != "전체":
    cat_t = st.session_state.selected_cat.upper()
    # BL인 경우 BLT/BLX 제외 로직
    if cat_t in ["BL", "TL"]:
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.upper().apply(lambda x: cat_t in x.split() or x == cat_t)]
    else:
        f_df = f_df[f_df['제품군 대그룹 (Product Group)'].str.upper().str.contains(cat_t, na=False)]

# 2) 재질 필터 (Ti-SLA vs Roxolid SLA 완벽 분리)
if st.session_state.selected_mat != "전체":
    mat_t = st.session_state.selected_mat
    if mat_t == "Ti-SLA":
        # Roxolid는 포함 안 되고 SLA만 있는 것
        f_df = f_df[~f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mat_t == "Roxolid SLA":
        # Roxolid와 SLA가 둘 다 있어야 함 (SLActive 제외)
        f_df = f_df[f_df['재질/표면처리'].str.contains("Roxolid", na=False) & f_df['재질/표면처리'].str.contains("SLA", na=False) & ~f_df['재질/표면처리'].str.contains("SLActive", na=False)]
    elif mat_t == "Roxolid SLActive":
        f_df = f_df[f_df['재질/표면처리'].str.contains("SLActive", na=False)]

# 3) 상세 규격 필터 (S=2.8mm, SP=1.8mm 물리적 필터)
if st.session_state.selected_spec != "전체":
    s_t = st.session_state.selected_spec
    if st.session_state.selected_cat in ["BL", "BLT"]:
        f_df = f_df[f_df['직경'] == s_t]
    else: # TL, TLX
        # 사용자가 선택한 버튼 텍스트에 따라 직경으로 필터링
        if "S (2.8mm)" in s_t:
            f_df = f_df[f_df['직경'].str.contains("2.8", na=False)]
        elif "SP (1.8mm)" in s_t:
            f_df = f_df[f_df['직경'].str.contains("1.8", na=False)]

# --- 8. 리스트 출력 ---
st.write(f"🔍 검색 결과: **{len(f_df)}건**")
for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    is_bio = row['제품군 대그룹 (Product Group)'] == 'Biomaterial'
    with st.container(border=True):
        title = f"{row['제품군 대그룹 (Product Group)']} - {row['재질/표면처리']}" if not is_bio else row['재질/표면처리']
        st.markdown(f"#### {title}")
        st.code(row['주문코드']) # 여기서 021.xxxx 형태가 유지되어야 함
        st.caption(f"📍 {row['직경']} x {row['길이']}" if not is_bio else "📍 Biomaterial")
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량", 0, 100, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        if q > 0: st.session_state['cart'][k] = {'c': row['주문코드'], 'q': q, 'display_name': title}
        else: st.session_state['cart'].pop(k, None)
