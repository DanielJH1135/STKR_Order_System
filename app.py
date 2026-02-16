import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙] 반드시 코드 최상단에 위치 ---
st.set_page_config(page_title="주문 시스템", layout="centered")

# --- 1. 담당자 설정 ---
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

# --- 2. 주문코드 보정 (021.0010 형식) ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
        parts = c.split(".", 1)
        prefix = parts[0].zfill(3) if parts[0].isdigit() else parts[0]
        suffix = parts[1].ljust(4, '0') if parts[1].isdigit() else parts[1]
        return f"{prefix}.{suffix}"
    return c

@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    try:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("").apply(lambda x: x.str.strip())
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, str(e)

# --- 3. 담당자 및 거래처 판별 ---
try:
    rep_key = st.query_params.get("rep", "lee")
    url_cust = st.query_params.get("cust", "")
except:
    rep_key = "lee"
    url_cust = ""

current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# --- 4. 세션 초기화 ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로드 실패: {load_msg}"); st.stop()

# --- 5. 최종 확인 팝업창 (교환 체크 및 딸깍 문구 포함) ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    # [사용성 개선] 교환주문 체크박스
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown("교환 보내실 제품은 **유효기간 1년 이상** 남은 제품만 가능합니다.")
    
    st.divider()
    # 팝업 내 규격 확인용 리스트
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['g']}** ({item['sz']} x {item['ln']}) : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        # 1. 주문 리스트 생성
        order_list = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        
        # 2. 하단 문구 결정 (교환 여부에 따라)
        footer_action = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        
        # 3. 사장님 요청 '딸깍 복붙'용 메시지 포맷
        # 리스트 -> 거래처명 -> 문구 순서
        full_msg = f"{order_list}\n{cust_name}\n{footer_action}"
        
        # 전송 실행
        ok, res = send_telegram(full_msg, current_rep['id'])
        if ok:
            st.success("전송 완료!")
            st.balloons()
            st.session_state['cart'] = {}
            st.rerun()
        else:
            st.error(f"전송 실패: {res}")

# --- 6. 메인 UI 및 리스트 ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.sidebar.header("🏢 주문 정보 입력")
# 고유 링크 사용 시 거래처명 고정
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df['제품군 대그룹 (Product Group)'].unique()))
mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df['재질/표면처리'].unique()))

# 사이드바 장바구니
st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")
if st.session_state['cart']:
    display_items = [f"• {v['g']}.. / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(display_display_items) if 'display_display_items' in locals() else "\n".join(display_items))
    
    if st.sidebar.button(f"🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input:
            st.sidebar.error("⚠️ 업체명과 담당자명을 확인하세요!")
        else:
            confirm_order_dialog(cust_name_input, mgr_name_input)
else:
    st.sidebar.warning("🛒 수량을 입력하세요.")

# 메인 카드 목록
f_df = df.copy()
if cat != "전체": f_df = f_df[f_df['제품군 대그룹 (Product Group)'] == cat]
if mat != "전체": f_df = f_df[f_df['재질/표면처리'] == mat]

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    with st.container(border=True):
        st.markdown(f"**{row['제품군 대그룹 (Product Group)']}**")
        st.code(row['주문코드'])
        st.caption(f"📍 규격: {row['직경']} x {row['길이']} | {row['재질/표면처리']}")
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("주문 수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_q))
        if q > 0:
            st.session_state['cart'][item_key] = {'c': row['주문코드'], 'q': q, 'g': row['제품군 대그룹 (Product Group)'], 'sz': row['직경'], 'ln': row['길이'], 'm': row['재질/표면처리']}
        else:
            st.session_state['cart'].pop(item_key, None)
