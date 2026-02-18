import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="임플란트 주문 시스템", layout="centered")

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

# --- 2. 데이터 보정 및 유연한 열 매핑 ---
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
        return None, None, f"파일을 찾을 수 없습니다: {file_path}"
    
    try:
        df = pd.read_excel(file_path, dtype=str)
        df.columns = [str(c).strip() for c in df.columns] # 공백 제거
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        # [핵심] 똑똑한 열 이름 찾기 (Keywords 기반)
        def find_best_col(keywords, default):
            for k in keywords:
                for col in df.columns:
                    if k.lower() in col.lower(): return col
            return default

        mapping = {
            'cat': find_best_col(['제품군', 'Group', '대그룹', '카테고리'], '제품군'),
            'code': find_best_col(['코드', 'Code', '품번', 'Article'], '주문코드'),
            'mat': find_best_col(['재질', '표면', 'Material', 'Surface'], '재질/표면처리'),
            'dia': find_best_col(['직경', 'Dia', 'D'], '직경'),
            'len': find_best_col(['길이', 'Len', 'L'], '길이')
        }
        
        # Biomaterial 수동 추가 (매핑된 열 이름 사용)
        bio_items = [
            {mapping['cat']: 'Biomaterial', mapping['code']: '075.101w', mapping['mat']: 'Emdogain 0.3ml', mapping['dia']: '-', mapping['len']: '-'},
            {mapping['cat']: 'Biomaterial', mapping['code']: '075.102w', mapping['mat']: 'Emdogain 0.7ml', mapping['dia']: '-', mapping['len']: '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio_items)], ignore_index=True)
        
        # 주문코드 포맷팅
        if mapping['code'] in df.columns:
            df[mapping['code']] = df[mapping['code']].apply(format_order_code)
            
        return df, mapping, "성공"
    except Exception as e:
        return None, None, str(e)

# --- 3. 설정 및 파라미터 ---
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

df, info, msg = load_data()

# 에러 발생 시 처리
if df is None:
    st.error(f"❌ 데이터 로드 실패: {msg}")
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
        full_msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {cust_name}\n👤 {mgr_name}\n\n{order_list}\n\n{cust_name} {action}"
        
        if send_telegram(full_msg, current_rep['id'])[0]:
            st.success("전송 완료!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error("전송에 실패했습니다. 텔레그램 설정을 확인하세요.")

# --- 5. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# 카테고리 내비게이션
st.write("### 📂 시스템 선택")
main_cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, cat in enumerate(main_cats):
    with cols[i % 3]:
        active = (st.session_state.selected_cat == cat)
        if st.button(cat, use_container_width=True, type="primary" if active else "secondary"):
            st.session_state.selected_cat = cat

if st.button("🔄 전체 초기화", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state['cart'] = {}; st.rerun()

st.divider()

# 사이드바
st.sidebar.header("🏢 주문 정보")
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['display_name'][:12]} / {v['q']}개")
    if st.sidebar.button("🚀 주문 전송", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input: st.sidebar.error("⚠️ 정보 입력 필요!")
        else: confirm_order_dialog(cust_name_input, mgr_name_input)
else: st.sidebar.warning("🛒 수량을 입력하세요.")

# --- 6. 제품 리스트 필터링 (오류 방지 로직 강화) ---
cat_col = info['cat']
if cat_col not in df.columns:
    st.warning(f"⚠️ '{cat_col}' 열을 찾을 수 없습니다. 엑셀 파일을 확인해주세요.")
    st.stop()

f_df = df.copy()
if st.session_state.selected_cat != "전체":
    # 부분 일치로 더 유연하게 필터링 (BLX에 BL이 걸리지 않게 처리)
    if st.session_state.selected_cat in ["BL", "TL"]: # 정확히 일치해야 하는 경우
        f_df = f_df[f_df[cat_col].str.strip() == st.session_state.selected_cat]
    else: # BLX, TLX 등은 포함 여부로 확인
        f_df = f_df[f_df[cat_col].str.contains(st.session_state.selected_cat, na=False)]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

if len(f_df) == 0:
    st.info(f"검색된 '{st.session_state.selected_cat}' 품목이 없습니다.")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    is_bio = row[cat_col] == 'Biomaterial'
    with st.container(border=True):
        title = row[info['mat']] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[info['code']])
        if is_bio: st.caption("📍 Biomaterial")
        else: st.caption(f"📍 {row[info['dia']]} x {row[info['len']]} | {row[info['mat']]}")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("수량", 0, 1000, key=f"qty_{idx}", value=int(prev_q), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][item_key] = {
                'c': row[info['code']], 'q': q, 'display_name': title,
                'g': row[cat_col], 'sz': row[info['dia']], 'ln': row[info['len']], 'm': row[info['mat']]
            }
        else: st.session_state['cart'].pop(item_key, None)
