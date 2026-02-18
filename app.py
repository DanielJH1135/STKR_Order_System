import streamlit as st
import pandas as pd
import requests
import os
import re

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 최상단 회사 로고 송출 (logo.png 또는 logo.jpg) ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=250)
elif os.path.exists("logo.jpg"):
    st.image("logo.jpg", width=250)

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
    except Exception as e:
        return False, str(e)

# --- 2. 데이터 보정 및 로드 ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c and any(char.isdigit() for char in c):
        parts = c.split(".", 1)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1]
        if suffix.isdigit():
            suffix = suffix.ljust(4, '0')
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
    except Exception as e:
        return None, str(e)

# --- 3. URL 파라미터 및 상태 관리 ---
try:
    rep_key = st.query_params.get("rep", "lee")
    url_cust = st.query_params.get("cust", "")
except:
    rep_key = "lee"
    url_cust = ""

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. 최종 확인 팝업창 (안내 문구 보강) ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    # [복구 완료] 교환 시 주의사항 문구
    st.markdown(":red[**※ 교환 보내실 제품은 유효기간 1년 이상 남은 제품만 가능합니다.**]")
    
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['display_name']}** : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action_text = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        
        full_msg = (
            f"🔔 [{current_rep['name']}] 주문접수\n"
            f"🏢 {cust_name}\n"
            f"👤 {mgr_name}\n\n"
            f"{order_list}\n\n"
            f"{cust_name} {action_text}"
        )
        
        ok, res = send_telegram(full_msg, current_rep['id'])
        if ok:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error(f"실패: {res}")

# --- 5. 메인 UI (버튼 배열 및 로직) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.write("### 📂 시스템 선택")

# 버튼 배치 (BL, BLT, TL / BLX, TLX, Biomaterial)
row1 = ["BL", "BLT", "TL"]
row2 = ["BLX", "TLX", "Biomaterial"]

c1 = st.columns(3)
for i, cat in enumerate(row1):
    with c1[i]:
        if st.button(cat, use_container_width=True, key=f"btn_{cat}", type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat
            st.rerun()

c2 = st.columns(3)
for i, cat in enumerate(row2):
    with c2[i]:
        if st.button(cat, use_container_width=True, key=f"btn_{cat}", type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat
            st.rerun()

if st.button("🔄 전체 초기화 / 모두 보기", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state['cart'] = {}; st.rerun()

st.divider()

# 사이드바
st.sidebar.header("🏢 주문 정보 입력")
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:10]}.. / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input: st.sidebar.error("정보를 입력하세요!")
        else: confirm_order_dialog(cust_name_input, mgr_name_input)

# --- 6. 제품 리스트 필터링 ---
c_group_col = '제품군 대그룹 (Product Group)'
f_df = df.copy()

def is_exact_match(val, target):
    val, target = str(val).upper(), target.upper()
    if val.strip() == target: return True
    pattern = rf'(?:^|[^A-Z0-9]){target}(?:[^A-Z0-9]|$)'
    return bool(re.search(pattern, val))

if st.session_state.selected_cat != "전체":
    f_df = f_df[f_df[c_group_col].apply(lambda x: is_exact_match(x, st.session_state.selected_cat))]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_bio = row[c_group_col] == 'Biomaterial'
    with st.container(border=True):
        title = row['재질/표면처리'] if is_bio else row[c_group_col]
        st.markdown(f"### {title}")
        st.code(row['주문코드'])
        st.caption(f"📍 {row['직경']} x {row['길이']} | {row['재질/표면처리']}" if not is_bio else "📍 Biomaterial")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("주문 수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_q))
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 'q': q, 
                'display_name': title + (f" ({row['직경']}x{row['길이']})" if not is_bio else "")
            }
        else: st.session_state['cart'].pop(item_key, None)
