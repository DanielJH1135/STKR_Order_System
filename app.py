import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- [안전장치] 구글 시트 모듈 ---
try:
    from streamlit_gsheets import GSheetsConnection
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# --- [규칙 1] 반드시 최상단 ---
st.set_page_config(page_title="임플란트 주문 시스템", layout="centered")

# --- 1. 담당자 및 텔레그램 설정 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

conn = None
if HAS_GSHEETS:
    try: conn = st.connection("gsheets", type=GSheetsConnection)
    except: conn = None

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 보정 및 자동 열 인식 로직 ---
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
    if not os.path.exists(file_path):
        return None, "엑셀 파일(order_database.xlsx)이 서버에 없습니다."
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        # 열 이름의 앞뒤 공백 제거 (에러 방지 핵심)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        # 필수 열 매핑 (이름이 조금 달라도 찾아내기)
        col_map = {
            'cat': next((c for c in df.columns if '제품군' in c), '제품군'),
            'code': next((c for c in df.columns if '코드' in c), '주문코드'),
            'mat': next((c for c in df.columns if '재질' in c or '표면' in c), '재질/표면처리'),
            'dia': next((c for c in df.columns if '직경' in c), '직경'),
            'len': next((c for c in df.columns if '길이' in c), '길이')
        }
        
        # Biomaterial 수동 추가
        new_items = [
            {col_map['cat']: 'Biomaterial', col_map['code']: '075.101w', col_map['mat']: 'Emdogain 0.3ml', col_map['dia']: '-', col_map['len']: '-'},
            {col_map['cat']: 'Biomaterial', col_map['code']: '075.102w', col_map['mat']: 'Emdogain 0.7ml', col_map['dia']: '-', col_map['len']: '-'}
        ]
        df = pd.concat([df, pd.DataFrame(new_items)], ignore_index=True)
        df[col_map['code']] = df[col_map['code']].apply(format_order_code)
        
        return df, col_map
    except Exception as e:
        return None, str(e)

# --- 3. 설정 및 상태 관리 ---
def get_param(key, default):
    try:
        val = st.query_params.get(key, default)
        return val[0] if isinstance(val, list) and len(val) > 0 else val
    except: return default

rep_key = get_param("rep", "lee")
url_cust = get_param("cust", "")
current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, info = load_data()
if df is None:
    st.error(f"⚠️ {info}")
    st.stop()

# --- 4. 최종 확인 팝업 ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown("교환 보내실 제품은 **유효기간 1년 이상** 남은 제품만 가능합니다.")
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
        else: st.error("전송에 실패했습니다.")

# --- 5. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.write("### 📂 시스템 선택")
main_cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, cat in enumerate(main_cats):
    with cols[i % 3]:
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat

if st.button("🔄 전체 초기화", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state['cart'] = {}; st.rerun()

st.divider()

# 사이드바
st.sidebar.header("🏢 주문 정보")
cust_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]} / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송", use_container_width=True, type="primary"):
        if not cust_name or not mgr_name: st.sidebar.error("⚠️ 정보를 입력하세요!")
        else: confirm_order_dialog(cust_name, mgr_name)
else: st.sidebar.warning("🛒 수량을 입력하세요.")

# 제품 리스트 출력 (자동 인식된 열 이름 사용)
f_df = df.copy()
cat_col = info['cat']
code_col = info['code']
mat_col = info['mat']
dia_col = info['dia']
len_col = info['len']

if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df[cat_col] == st.session_state.selected_cat]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_bio = row[cat_col] == 'Biomaterial'
    with st.container(border=True):
        title = row[mat_col] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[code_col])
        st.caption(f"📍 {row[dia_col]} x {row[len_col]} | {row[mat_col]}" if not is_bio else "📍 Biomaterial")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("수량", 0, 1000, key=f"qty_{idx}", value=int(prev_q), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row[code_col], 'q': q, 'display_name': title + (f" ({row[dia_col]}x{row[len_col]})" if not is_bio else ""),
                'g': row[cat_col], 'sz': row[dia_col], 'ln': row[len_col], 'm': row[mat_col]
            }
        else: st.session_state['cart'].pop(item_key, None)
