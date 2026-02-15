import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙] 반드시 코드 최상단에 위치 ---
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

# --- 3. 담당자 판별 ---
try:
    rep_key = st.query_params.get("rep", "lee")
except:
    rep_key = "lee"
current_rep = SALES_REPS.get(rep_key, SALES_REPS["lee"])

# --- 4. 세션 초기화 ---
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로드 실패: {load_msg}")
    st.stop()

# --- 5. 최종 확인 팝업창 (Dialog) ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(full_msg_for_telegram):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    # [고객 확인용] 제품명, 규격, 그리고 요청하신 '표면처리'까지 보여줍니다.
    for item in st.session_state['cart'].values():
        st.write(f"**{item['g']}** ({item['sz']} x {item['ln']})")
        st.caption(f"✨ 표면처리: {item['m']} | 수량: {item['q']}개")
    
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        # [사장님 전송] 주문코드와 수량만 포함된 깔끔한 메시지 발송
        ok, res = send_telegram(full_msg_for_telegram, current_rep['id'])
        if ok:
            st.success("주문이 전송되었습니다!")
            st.balloons()
            st.session_state['cart'] = {}
            st.rerun()
        else:
            st.error(f"전송 실패: {res}")

# --- 6. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문채널")

# 사이드바 설정
st.sidebar.header("🏢 주문 정보 입력")
cust_name = st.sidebar.text_input("거래처명 (필수)")
mgr_name = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
st.sidebar.header("🔍 품목 필터")
c_group_col = '제품군 대그룹 (Product Group)'
c_mat_col = '재질/표면처리'

cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[c_group_col].unique()))
mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df[c_mat_col].unique()))

# 사이드바 장바구니
st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")
if st.session_state['cart']:
    sidebar_display = [f"• {v['g']}.. / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(sidebar_display))
    
    if st.sidebar.button(f"🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name or not mgr_name:
            st.sidebar.error("⚠️ 업체명과 담당자명을 입력하세요!")
        else:
            # [사장님용 전송 메시지] 복사하기 좋게 주문코드 / 수량만 구성
            order_only_codes = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
            full_msg = f"🔔 [{current_rep['name']}] 주문 접수\n🏢 {cust_name}\n👤 {mgr_name}\n----\n{order_only_codes}"
            
            confirm_order_dialog(full_msg)
    
    if st.sidebar.button("🗑️ 전체 삭제", use_container_width=True):
        st.session_state['cart'] = {}
        st.rerun()
else:
    st.sidebar.warning("🛒 수량을 입력하세요.")

# --- 7. 메인 리스트 (카드형) ---
f_df = df.copy()
if cat != "전체": f_df = f_df[f_df[c_group_col] == cat]
if mat != "전체": f_df = f_df[f_df[c_mat_col] == mat]

st.write(f"조회된 품목: **{len(f_df)}** 건")

for idx, row in f_df.iterrows():
    item_key = f"row_{idx}"
    with st.container(border=True):
        st.markdown(f"**{row[c_group_col]}**")
        st.code(row['주문코드'])
        st.caption(f"📍 규격: {row['직경']} x {row['길이']} | {row[c_mat_col]}")
        
        prev_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
        q = st.number_input("주문 수량(개)", 0, 1000, key=f"qty_{idx}", value=int(prev_q))

        if q > 0:
            # 팝업창 노출을 위해 'm'(표면처리/재질) 정보 추가 저장
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 
                'q': q, 
                'g': row[c_group_col], 
                'sz': row['직경'], 
                'ln': row['길이'],
                'm': row[c_mat_col]
            }
        else:
            if item_key in st.session_state['cart']:
                del st.session_state['cart'][item_key]
