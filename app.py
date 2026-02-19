import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v3.0", layout="centered")

# --- [신규] 로고 중앙 배치 ---
if os.path.exists("logo.png") or os.path.exists("logo.jpg"):
    # 컬럼을 3분할하여 가운데 컬럼에 이미지를 배치하는 방식
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
        elif os.path.exists("logo.jpg"): st.image("logo.jpg", use_container_width=True)

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
        # Biomaterial 수동 추가
        new_items = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        df = pd.concat([df, pd.DataFrame(new_items)], ignore_index=True)
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 상태 관리 (단계별 필터 상태 추가) ---
# selected_cat: 시스템(1단계), selected_mat: 재질(2단계), selected_spec: 규격(3단계)
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'selected_mat' not in st.session_state: st.session_state.selected_mat = "전체"
if 'selected_spec' not in st.session_state: st.session_state.selected_spec = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. URL 파라미터 처리 ---
rep_key = st.query_params.get("rep", "lee")
url_cust = st.query_params.get("cust", "")
if isinstance(rep_key, list): rep_key = rep_key[0]
if isinstance(url_cust, list): url_cust = url_cust[0]
current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

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
        msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {cust_name}\n👤 {mgr_name}\n\n{order_list}\n\n{cust_name} {action}"
        if send_telegram(msg, current_rep['id'])[0]:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error("전송 실패")

# --- 6. 메인 UI (단계별 버튼 구성) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [STEP 1] 시스템 선택 (기존 2줄 배열)
st.write("### 1️⃣ 시스템 선택")
row1, row2 = ["BL", "BLT", "TL"], ["BLX", "TLX", "Biomaterial"]
c1 = st.columns(3)
for i, cat in enumerate(row1):
    with c1[i]:
        # 상위 단계 선택 시 하위 단계 초기화
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()
c2 = st.columns(3)
for i, cat in enumerate(row2):
    with c2[i]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = cat, "전체", "전체"
            st.rerun()

# [STEP 2] 재질/표면처리 선택 (시스템이 선택되었고, Biomaterial이 아닐 때만 표시)
if st.session_state.selected_cat != "전체" and st.session_state.selected_cat != "Biomaterial":
    st.write("### 2️⃣ 재질/표면처리 선택")
    mats = ["Ti-SLA", "Roxolid SLA", "Roxolid SLActive"]
    c3 = st.columns(3)
    for i, m in enumerate(mats):
        with c3[i]:
            # 재질 선택 시 상세 규격 초기화
            if st.button(m, use_container_width=True, type="primary" if st.session_state.selected_mat == m else "secondary"):
                st.session_state.selected_mat, st.session_state.selected_spec = m, "전체"
                st.rerun()

# [STEP 3] 상세 규격 선택 (재질까지 선택되었을 때 표시)
if st.session_state.selected_mat != "전체":
    st.write("### 3️⃣ 상세 규격 선택")
    cur_cat = st.session_state.selected_cat
    specs = []
    # 시스템에 따라 보여줄 규격 버튼 결정
    if cur_cat in ["BL", "BLT"]:
        specs = ["3.3", "4.1", "4.8"] # BL/BLT 직경
    elif cur_cat in ["TL", "TLX"]:
        specs = ["S (Standard)", "SP (Standard Plus)"] # TL/TLX 타입

    if specs:
        c4 = st.columns(len(specs))
        for i, s in enumerate(specs):
            with c4[i]:
                if st.button(s, use_container_width=True, type="primary" if st.session_state.selected_spec == s else "secondary"):
                    st.session_state.selected_spec = s
                    st.rerun()

# 초기화 버튼
if st.button("🔄 검색 조건 초기화", use_container_width=True):
    st.session_state.selected_cat, st.session_state.selected_mat, st.session_state.selected_spec = "전체", "전체", "전체"
    st.rerun()

st.divider()

# 사이드바
st.sidebar.header("🏢 주문 정보")
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]}.. / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input: st.sidebar.error("정보를 입력하세요!")
        else: confirm_order_dialog(cust_name_input, mgr_name_input)

# --- 7. 3단 필터링 로직 적용 ---
c_group_col = '제품군 대그룹 (Product Group)'
c_mat_col = '재질/표면처리'
c_dia_col = '직경'
f_df = df.copy()

# 1단계: 시스템 필터 (스마트 매칭)
def is_exact_match(val, target):
    val, target = str(val).upper(), target.upper()
    if val.strip() == target: return True
    pattern = rf'(?:^|[^A-Z0-9]){target}(?:[^A-Z0-9]|$)'
    return bool(re.search(pattern, val))

if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df[c_group_col].apply(lambda x: is_exact_match(x, st.session_state.selected_cat))]

# 2단계: 재질 필터 (선택 시 적용)
if st.session_state.selected_mat != "전체":
    # 버튼명(예: Ti-SLA)에서 핵심 키워드(SLA)만 추출하여 포함 여부 검색
    target_mat_keyword = st.session_state.selected_mat.split()[-1] if " " in st.session_state.selected_mat else st.session_state.selected_mat.split("-")[-1]
    f_df = f_df[f_df[c_mat_col].str.upper().str.contains(target_mat_keyword, na=False)]

# 3단계: 상세 규격 필터 (선택 시 적용)
if st.session_state.selected_spec != "전체":
    spec = st.session_state.selected_spec
    if st.session_state.selected_cat in ["BL", "BLT"]:
        # 직경 필터링 (정확히 일치)
        f_df = f_df[f_df[c_dia_col] == spec]
    elif st.session_state.selected_cat in ["TL", "TLX"]:
        # 타입 필터링 (S 또는 SP가 포함된 경우)
        target_type = spec.split("(")[0].strip() # "S (Standard)" -> "S" 추출
        # 직경 열이나 재질 열 등에서 해당 타입 키워드 검색
        f_df = f_df[f_df[c_mat_col].str.contains(target_type, na=False) | f_df[c_dia_col].astype(str).str.contains(target_type, na=False)]

st.write(f"🔍 검색 결과: **{len(f_df)}건**")

if len(f_df) == 0 and st.session_state.selected_cat != "전체":
    st.info("조건에 맞는 품목이 없습니다. 필터를 조정해 보세요.")

# 리스트 출력
for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_bio = row[c_group_col] == 'Biomaterial'
    with st.container(border=True):
        title = row[c_mat_col] if is_bio else f"{row[c_group_col]} ({row[c_mat_col]})"
        st.markdown(f"### {title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row[c_dia_col]} x {row['길이']}" if not is_bio else "📍 Biomaterial")
        
        prev = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("수량", 0, 1000, key=f"qty_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 'q': q, 
                'display_name': title + (f" ({row[c_dia_col]}x{row['길이']})" if not is_bio else "")
            }
        else: st.session_state['cart'].pop(item_key, None)
