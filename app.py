import streamlit as st
import pandas as pd
import requests
import os

# --- 1. 기본 설정 (가장 안전한 방식) ---
st.set_page_config(page_title="주문 시스템 비상모드", layout="centered")

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

# --- 2. 데이터 로드 (캐시 제거, 가장 단순한 형태) ---
def load_data():
    file_path = "order_database.xlsx"
    if not os.path.exists(file_path):
        return None, "엑셀 파일(order_database.xlsx)이 서버에 없습니다. 파일 이름을 확인해주세요."
    try:
        # 문자열로만 읽어오기
        df = pd.read_excel(file_path, dtype=str)
        # 열 이름 공백 제거
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")
        
        # 필수 열 이름 강제 매핑 (에러 방지 핵심)
        cat_col = '제품군 대그룹 (Product Group)'
        code_col = '주문코드'
        mat_col = '재질/표면처리'
        dia_col = '직경'
        len_col = '길이'

        if code_col not in df.columns or cat_col not in df.columns:
             return None, f"엑셀에 필수 열('{code_col}' 또는 '{cat_col}')이 없습니다."

        return df, "성공"
    except Exception as e: return None, str(e)

# --- 3. 기본 파라미터 ---
rep_key = "lee"  # 파라미터 에러 방지를 위해 강제 고정
url_cust = ""
current_rep = SALES_REPS["lee"]

if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None:
    st.error(f"❌ 비상 모드 데이터 로드 실패: {load_msg}")
    st.stop()

cat_col = '제품군 대그룹 (Product Group)'
code_col = '주문코드'
mat_col = '재질/표면처리'
dia_col = '직경'
len_col = '길이'

# --- 4. 메인 화면 ---
st.title("🛒 주문 전송 시스템 (비상모드)")
st.warning("현재 시스템 안정화 작업 중입니다. 필수 주문만 진행해 주세요.")

st.sidebar.header("🏢 주문 정보 입력")
c_name = st.sidebar.text_input("거래처명 (필수)")
m_name = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[cat_col].unique()))

if st.session_state['cart']:
    st.sidebar.subheader("🛒 현재 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.write(f"- {v['c']} / {v['q']}개")
    if st.sidebar.button("🚀 즉시 주문 전송", type="primary"):
        if not c_name or not m_name:
            st.sidebar.error("거래처/담당자명을 입력하세요!")
        else:
            items_msg = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
            full_msg = f"🔔 비상 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{items_msg}\n\n{c_name} 주문부탁드립니다."
            if send_telegram(full_msg, current_rep['id'])[0]:
                st.sidebar.success("전송 완료!")
                st.session_state['cart'] = {}
                st.rerun()
            else:
                st.sidebar.error("전송 실패!")

# --- 5. 제품 목록 출력 ---
f_df = df.copy()
if cat != "전체": f_df = f_df[f_df[cat_col] == cat]

st.write(f"조회 건수: {len(f_df)}건")

for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    with st.container(border=True):
        st.write(f"**{row[cat_col]}** | {row[code_col]}")
        st.caption(f"{row[dia_col]} x {row[len_col]} | {row[mat_col]}")
        
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량", 0, 100, key=f"q_{idx}", value=int(prev))
        
        if q > 0:
            st.session_state['cart'][k] = {'c': row[code_col], 'q': q}
        else:
            if k in st.session_state['cart']: del st.session_state['cart'][k]
