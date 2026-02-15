import streamlit as st
import pandas as pd
import requests
import os

# --- 1. 환경 설정 (아이디 반영 완료) ---
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = "1781982606"  # 사장님 아이디 적용

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e:
        return False, str(e)

# --- 2. 데이터 보정 로직 (021.0010 형식 맞춤) ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    
    # 점(.)이 있는 경우 처리
    if "." in c:
        parts = c.split(".", 1)
        prefix = parts[0]
        suffix = parts[1]
        
        # 앞자리: 숫자면 3자리로 (21 -> 021)
        if prefix.isdigit():
            prefix = prefix.zfill(3)
        
        # 뒷자리: 숫자면 4자리로 (001 -> 0010)
        # 단, 906s 처럼 문자가 섞여있으면 보존
        if suffix.isdigit():
            suffix = suffix.ljust(4, '0')
            
        return f"{prefix}.{suffix}"
    
    return c

# --- 3. 데이터 로딩 ---
@st.cache_data
def load_data():
    file_path = "order_database.xlsx"
    if not os.path.exists(file_path):
        return None, f"❌ '{file_path}' 파일을 찾을 수 없습니다."
    try:
        # 모든 열을 문자로 읽기
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("")
        df['주문코드'] = df['주문코드'].apply(format_order_code)
        return df, "성공"
    except Exception as e:
        return None, f"❌ 데이터 읽기 오류: {str(e)}"

# --- 4. 페이지 구성 ---
st.set_page_config(page_title="주문 시스템", layout="wide")
df, msg = load_data()

if df is None:
    st.error(msg)
    st.stop()

# 장바구니 세션 초기화
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

st.title("📦 거래처 전용 주문 시스템")

# --- 5. 사이드바 (정보입력 및 필터) ---
st.sidebar.header("🏢 주문자 정보")
cust_name = st.sidebar.text_input("거래처명 (필수)", key="customer_input_box")
mgr_name = st.sidebar.text_input("담당자명 (필수)", key="manager_input_box")

st.sidebar.divider()
st.sidebar.header("🔍 품목 필터")

c_group = '제품군 대그룹 (Product Group)'
c_mat = '재질/표면처리'
c_code = '주문코드'

category = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[c_group].unique()), key="filter_cat")
material = st.sidebar.selectbox("재질", ["전체"] + sorted(df[c_mat].unique()), key="filter_mat")

# 필터링 적용
filtered_df = df.copy()
if category != "전체":
    filtered_df = filtered_df[filtered_df[c_group] == category]
if material != "전체":
    filtered_df = filtered_df[filtered_df[c_mat] == material]

# --- 6. 메인 주문 리스트 ---
st.write(f"조회된 품목: {len(filtered_df)}개")
cols = st.columns([0.5, 3, 1, 1, 1.5])
for col, header in zip(cols, ["선택", "품목 / 주문코드", "직경", "길이", "수량"]):
    col.write(f"**{header}**")
st.divider()

# 에러 방지 핵심: original_index를 사용하여 고유 키 부여
for i, (original_idx, row) in enumerate(filtered_df.iterrows()):
    code = row[c_code]
    item_key = f"row_{original_idx}" # 절대 겹치지 않는 고유 키
    
    # 세션에서 현재 상태 불러오기
    is_in_cart = item_key in st.session_state['cart']
    current_q = st.session_state['cart'].get(item_key, {}).get('q', 0)
    
    r = st.columns([0.5, 3, 1, 1, 1.5])
    
    with r[0]:
        # 체크박스 고유 키 설정
        sel = st.checkbox("", key=f"chk_{original_idx}", value=is_in_cart)
    
    with r[1]:
        st.markdown(f"**{row[c_group]}**")
        st.code(code) # 보정된 021.0010 형식 표시
        st.caption(row[c_mat])
        
    with r[2]: st.write(row['직경'])
    with r[3]: st.write(row['길이'])
    
    with r[4]:
        # 수량 입력창 고유 키 설정
        q = st.number_input("수량", 0, 1000, key=f"qty_{original_idx}", value=int(current_q), label_visibility="collapsed")

    # 선택 및 수량 변경 시 장바구니 즉시 반영
    if sel and q > 0:
        st.session_state['cart'][item_key] = {'c': code, 'q': q}
    else:
        st.session_state['cart'].pop(item_key, None)

# --- 7. 장바구니 및 전송 (사이드바) ---
st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")

if st.session_state['cart']:
    cart_items = [f"- {v['c']} / {v['q']}개" for v in st.session_state['cart'].values()]
    summary = "\n".join(cart_items)
    st.sidebar.text_area("내역 확인", summary, height=200, key="cart_summary_area")
    
    if st.sidebar.button("🚀 스트라우만 주문 전송", key="btn_send_order"):
        if not cust_name or not mgr_name:
            st.sidebar.error("거래처명과 담당자명을 입력해주세요!")
        else:
            full_msg = f"🔔 [새 주문 접수]\n🏢 거래처: {cust_name}\n👤 담당자: {mgr_name}\n----\n{summary}"
            success, res_msg = send_telegram(full_msg)
            if success:
                st.balloons()
                st.sidebar.success("성공적으로 보냈습니다!")
                # 전송 후 장바구니 비우기 원하시면 아래 주석 해제
                # st.session_state['cart'] = {}
                # st.rerun()
            else:
                st.sidebar.error(f"전송 실패: {res_msg}")
else:
    st.sidebar.info("품목을 체크하고 수량을 입력하세요.")

if st.sidebar.button("🗑️ 장바구니 초기화", key="btn_clear_cart"):
    st.session_state['cart'] = {}
    st.rerun()


