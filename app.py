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
    except Exception as e: return False, str(e)

# --- 2. 데이터 로드 (캐시 제거 - 메모리 오류 방지) ---
def load_data():
    file_path = "order_database.xlsx"
    if not os.path.exists(file_path):
        return None, "엑셀 파일을 찾을 수 없습니다."
    try:
        df = pd.read_excel(file_path, dtype=str)
        # 열 이름 공백 제거
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("").astype(str).apply(lambda x: x.str.strip())
        
        # 기본 열 이름 직접 지정 (자동 매핑 빼고 제일 단순하게)
        cat_col = '제품군 대그룹 (Product Group)'
        code_col = '주문코드'
        mat_col = '재질/표면처리'
        dia_col = '직경'
        len_col = '길이'

        # Biomaterial 수동 추가
        bio_data = [
            {cat_col: 'Biomaterial', code_col: '075.101w', mat_col: 'Emdogain 0.3ml', dia_col: '-', len_col: '-'},
            {cat_col: 'Biomaterial', code_col: '075.102w', mat_col: 'Emdogain 0.7ml', dia_col: '-', len_col: '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio_data)], ignore_index=True)
        
        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 담당자 및 파라미터 판별 ---
rep_key = st.query_params.get("rep", "lee") if hasattr(st, "query_params") else "lee"
url_cust = st.query_params.get("cust", "") if hasattr(st, "query_params") else ""

if isinstance(rep_key, list): rep_key = rep_key[0]
if isinstance(url_cust, list): url_cust = url_cust[0]

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, status = load_data()
if df is None:
    st.error(f"❌ 데이터 로드 실패: {status}")
    st.stop()

# 사용하는 열 이름 명시
cat_col = '제품군 대그룹 (Product Group)'
code_col = '주문코드'
mat_col = '재질/표면처리'
dia_col = '직경'
len_col = '길이'

# --- 4. 메인 UI 및 사이드바 ---
st.title(f"🛒 {current_rep['name']} 전용 주문")

st.sidebar.header("🏢 주문자 정보")
c_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
m_name = st.sidebar.text_input("담당자 성함 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 담은 품목")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['name'][:10]}.. {v['q']}개")
    
    st.sidebar.divider()
    is_ex = st.sidebar.checkbox("🔄 교환 주문 (선납)")
    if st.sidebar.button("🚀 최종 전송하기", use_container_width=True, type="primary"):
        if not c_name or not m_name: 
            st.sidebar.error("거래처 정보를 입력하세요!")
        else:
            items_msg = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
            action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
            full_msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{items_msg}\n\n{c_name} {action}"
            
            if send_telegram(full_msg, current_rep['id'])[0]:
                st.sidebar.success("전송 성공!")
                st.session_state['cart'] = {}
                st.rerun()
            else: 
                st.sidebar.error("전송 실패")

# --- 5. 카테고리 메뉴 ---
st.write("### 📂 품목군 선택")
cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, c in enumerate(cats):
    with cols[i % 3]:
        btn_label = f"✨ {c}" if st.session_state.selected_cat == c else c
        if st.button(btn_label, use_container_width=True):
            st.session_state.selected_cat = c

if st.button("🔄 전체 보기 / 초기화", use_container_width=True):
    st.session_state.selected_cat = "전체"
    st.session_state['cart'] = {}
    st.rerun()

st.divider()

# --- 6. 제품 리스트 필터링 및 출력 ---
f_df = df.copy()

if st.session_state.selected_cat != "전체":
    target = st.session_state.selected_cat.strip().upper()
    if target in ["BL", "TL"]:
        f_df = f_df[f_df[cat_col].astype(str).str.strip().str.upper() == target]
    else:
        f_df = f_df[f_df[cat_col].astype(str).str.strip().str.upper().str.contains(target, na=False)]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    is_bio = str(row[cat_col]).strip().upper() == "BIOMATERIAL"
    with st.container(border=True):
        title = row[mat_col] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[code_col])
        if is_bio: 
            st.caption("📍 분류: Biomaterial")
        else: 
            st.caption(f"📍 {row[dia_col]} x {row[len_col]} | {row[mat_col]}")
        
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량", 0, 1000, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][k] = {
                'c': row[code_col], 'q': q, 
                'name': title + (f" ({row[dia_col]}x{row[len_col]})" if not is_bio else "")
            }
        else:
            if k in st.session_state['cart']: del st.session_state['cart'][k]
