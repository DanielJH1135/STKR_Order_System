import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

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

# --- 2. 데이터 보정 및 로드 (가장 안정적인 기존 로직) ---
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

        # Biomaterial 제품군 수동 추가
        new_items = [
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.101w', '재질/표면처리': 'Emdogain 0.3ml', '직경': '-', '길이': '-'},
            {'제품군 대그룹 (Product Group)': 'Biomaterial', '주문코드': '075.102w', '재질/표면처리': 'Emdogain 0.7ml', '직경': '-', '길이': '-'}
        ]
        manual_df = pd.DataFrame(new_items)
        df = pd.concat([df, manual_df], ignore_index=True)
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, str(e)

# --- 3. URL 파라미터 및 상태 관리 ---
def get_param(key, default):
    try:
        val = st.query_params.get(key, default)
        return val[0] if isinstance(val, list) else val
    except:
        return default

rep_key = get_param("rep", "lee")
url_cust = get_param("cust", "")
current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# [신규] 카테고리 상태 관리 추가
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None: st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 4. 최종 확인 팝업창 (9:41 PM 형식 유지) ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown("교환 보내실 제품은 **유효기간 1년 이상** 남은 제품만 가능합니다.")
    
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

# --- 5. 메인 UI (사이드바 + 상단 카테고리 버튼) ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# [신규] 메인 화면 상단 카드형 버튼 모음
st.write("### 📂 시스템 선택")
main_cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, cat in enumerate(main_cats):
    with cols[i % 3]:
        # 선택된 카테고리는 색상이 강조(primary) 됩니다.
        if st.button(cat, use_container_width=True, type="primary" if st.session_state.selected_cat == cat else "secondary"):
            st.session_state.selected_cat = cat

if st.button("🔄 전체 초기화 / 모두 보기", use_container_width=True):
    st.session_state.selected_cat = "전체"
    st.session_state['cart'] = {}
    st.rerun()

st.divider()

# 사이드바 주문 정보
st.sidebar.header("🏢 주문 정보 입력")
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")
if st.session_state['cart']:
    summary = [f"• {v['display_name'][:10]}.. / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(summary))
    if st.sidebar.button(f"🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input:
            st.sidebar.error("⚠️ 업체명과 담당자명을 입력하세요!")
        else: confirm_order_dialog(cust_name_input, mgr_name_input)
    if st.sidebar.button("🗑️ 전체 삭제", use_container_width=True):
        st.session_state['cart'] = {}; st.rerun()
else:
    st.sidebar.warning("🛒 수량을 입력하세요.")

# --- 6. 제품 리스트 필터링 및 출력 ---
c_group_col = '제품군 대그룹 (Product Group)'
f_df = df.copy()

# [신규] 버튼 클릭 상태에 따른 필터링 (BL과 BLX가 혼동되지 않도록 정확히 일치하는지 확인)
if st.session_state.selected_cat != "전체":
    target = st.session_state.selected_cat
    if target in ["BL", "TL"]:
        f_df = f_df[f_df[c_group_col].str.strip() == target]
    else:
        f_df = f_df[f_df[c_group_col].str.contains(target, na=False)]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_biomaterial = row[c_group_col] == 'Biomaterial'
    
    with st.container(border=True):
        # Biomaterial은 제품명을 제목으로 표시
        display_title = row['재질/표면처리'] if is_biomaterial else row[c_group_col]
        st.markdown(f"### {display_title}")
        st.code(row['주문코드'])
        
        if is_biomaterial:
            st.caption(f"📍 분류: {row[c_group_col]}")
        else:
            st.caption(f"📍 규격: {row['직경']} x {row['길이']} | {row['재질/표면처리']}")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("주문 수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_q))
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 'q': q, 
                'display_name': display_title + (f" ({row['직경']}x{row['길이']})" if not is_biomaterial else ""),
                'g': row[c_group_col], 'sz': row['직경'], 'ln': row['길이'], 'm': row['재질/표면처리']
            }
        else:
            st.session_state['cart'].pop(item_key, None)
