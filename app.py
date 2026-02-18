import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- [규칙] 반드시 최상단 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 1. 담당자 및 설정 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

# 구글 스프레드시트 연결 (Secrets 설정 필요)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    conn = None

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

def save_to_google_sheets(cust, mgr, rep_name, cart_items, is_exchange):
    if not conn: return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        existing_data = conn.read(worksheet="Sheet1")
    except:
        existing_data = pd.DataFrame(columns=["주문시간", "거래처", "담당자", "영업담당", "주문코드", "수량", "구분"])
    
    new_entries = []
    for item in cart_items:
        new_entries.append({
            "주문시간": now, "거래처": cust, "담당자": mgr, "영업담당": rep_name,
            "주문코드": item['c'], "수량": item['q'], "구분": "교환(선납)" if is_exchange else "일반주문"
        })
    updated_df = pd.concat([existing_data, pd.DataFrame(new_entries)], ignore_index=True)
    conn.update(worksheet="Sheet1", data=updated_df)

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

# --- 2. 담당자 및 카테고리 상태 관리 ---
def get_param(key, default):
    try:
        val = st.query_params.get(key, default)
        return val[0] if isinstance(val, list) else val
    except: return default

rep_key = get_param("rep", "lee")
url_cust = get_param("cust", "")
current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

if 'selected_cat' not in st.session_state:
    st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"로드 실패: {load_msg}"); st.stop()

# --- 3. 최종 확인 팝업 ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown("교환 보내실 제품은 **유효기간 1년 이상** 남은 제품만 가능합니다.")
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action_text = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        full_msg = (
            f"🔔 [{current_rep['name']}] 주문접수\n🏢 {cust_name}\n👤 {mgr_name}\n\n"
            f"{order_list}\n\n"
            f"{cust_name} {action_text}"
        )
        ok, res = send_telegram(full_msg, current_rep['id'])
        if ok:
            save_to_google_sheets(cust_name, mgr_name, current_rep['name'], st.session_state['cart'].values(), is_exchange)
            st.success("전송 완료!")
            st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error(f"실패: {res}")

# --- 4. 메인 UI (내비게이션 버튼 추가) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [핵심] 상단 카테고리 선택 버튼 (모바일 최적화 2열 배치)
st.write("### 📂 시스템 선택")
main_cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, cat in enumerate(main_cats):
    with cols[i % 3]:
        if st.button(cat, use_container_width=True, type="secondary" if st.session_state.selected_cat != cat else "primary"):
            st.session_state.selected_cat = cat

if st.button("🔄 전체보기", use_container_width=True):
    st.session_state.selected_cat = "전체"

st.divider()

# --- 5. 사이드바 정보 ---
st.sidebar.header("🏢 주문 정보 입력")
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
st.sidebar.subheader("🛒 장바구니 요약")
if st.session_state['cart']:
    summary = [f"• {v['display_name'][:10]}.. / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(summary))
    if st.sidebar.button(f"🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input: st.sidebar.error("⚠️ 업체명/담당자명을 확인하세요!")
        else: confirm_order_dialog(cust_name_input, mgr_name_input)
    if st.sidebar.button("🗑️ 초기화", use_container_width=True):
        st.session_state['cart'] = {}; st.rerun()
else:
    st.sidebar.warning("🛒 품목을 골라주세요.")

# --- 6. 제품 리스트 필터링 ---
f_df = df.copy()
# 상단 버튼으로 선택한 카테고리 필터링
if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df['제품군 대그룹 (Product Group)'] == st.session_state.selected_cat]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_biomaterial = row['제품군 대그룹 (Product Group)'] == 'Biomaterial'
    with st.container(border=True):
        display_title = row['재질/표면처리'] if is_biomaterial else row['제품군 대그룹 (Product Group)']
        st.markdown(f"#### {display_title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']} | {row['재질/표면처리']}" if not is_biomaterial else f"📍 {row['제품군 대그룹 (Product Group)']}")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("주문 수량", 0, 1000, key=f"qty_{idx}", value=int(prev_q), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 'q': q, 
                'display_name': display_title + (f" ({row['직경']}x{row['길이']})" if not is_biomaterial else ""),
                'g': row['제품군 대그룹 (Product Group)'], 'sz': row['직경'], 'ln': row['길이'], 'm': row['재질/표면처리']
            }
        else:
            st.session_state['cart'].pop(item_key, None)
