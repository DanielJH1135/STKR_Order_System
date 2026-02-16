import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙] 반드시 최상단 배치 ---
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

# --- 3. 담당자 및 거래처 판별 (오류 해결 구간) ---
# URL 파라미터를 안전하게 가져오는 로직입니다.
def get_param(key, default):
    try:
        # 최신 Streamlit 방식
        val = st.query_params.get(key, default)
        return val[0] if isinstance(val, list) else val
    except:
        try:
            # 구버전 Streamlit 방식
            val = st.experimental_get_query_params().get(key, [default])
            return val[0] if isinstance(val, list) else val
        except:
            return default

rep_key = get_param("rep", "lee")
url_cust = get_param("cust", "")

# 52번 라인 근처: 담당자 정보 매칭
current_rep = SALES_REPS.get(rep_key)
if not current_rep:
    current_rep = SALES_REPS["lee"]

# 세션 초기화
if 'cart' not in st.session_state:
    st.session_state['cart'] = {}

df, load_msg = load_data()
if df is None:
    st.error(f"데이터 로드 실패: {load_msg}")
    st.stop()

# --- 4. 최종 확인 팝업창 ---
@st.dialog("📋 주문 내용을 확인해 주세요")
def confirm_order_dialog(cust_name, mgr_name):
    st.write("입력하신 품목과 수량이 맞습니까?")
    st.divider()
    
    is_exchange = st.checkbox("🔄 교환 주문인가요?")
    st.markdown("교환 보내실 제품은 **유효기간 1년 이상** 남은 제품만 가능합니다.")
    
    st.divider()
    for item in st.session_state['cart'].values():
        st.write(f"• **{item['g']}** ({item['sz']} x {item['ln']}) : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 네, 이대로 주문합니다", use_container_width=True, type="primary"):
        # 주문 리스트 (코드만 깔끔하게)
        order_items_text = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action_text = "선납주문 부탁드립니다." if is_exchange else "주문부탁드립니다."
        
        # 9:41 PM 형식 복구 + 딸깍 최적화
        full_msg = (
            f"🔔 [{current_rep['name']}] 주문접수\n"
            f"🏢 {cust_name}\n"
            f"👤 {mgr_name}\n\n"
            f"{order_items_text}\n\n"
            f"{cust_name} {action_text}"
        )
        
        ok, res = send_telegram(full_msg, current_rep['id'])
        if ok:
            st.success("전송 완료!")
            st.balloons()
            st.session_state['cart'] = {}
            st.rerun()
        else:
            st.error(f"전송 실패: {res}")

# --- 5. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문채널")

st.sidebar.header("🏢 주문 정보 입력")
# 고유 링크 사용 시 수정 불가하게 설정
cust_name_input = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
mgr_name_input = st.sidebar.text_input("담당자명 (필수)")

st.sidebar.divider()
cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df['제품군 대그룹 (Product Group)'].unique()))
mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df['재질/표면처리'].unique()))

# 사이드바 장바구니
st.sidebar.divider()
st.sidebar.subheader("🛒 실시간 장바구니")
if st.session_state['cart']:
    summary = [f"• {v['g']}.. / {v['q']}개" for v in st.session_state['cart'].values()]
    st.sidebar.info("\n".join(summary))
    
    if st.sidebar.button(f"🚀 주문 전송하기", use_container_width=True, type="primary"):
        if not cust_name_input or not mgr_name_input:
            st.sidebar.error("⚠️ 업체명과 담당자명을 입력하세요!")
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
            st.session_state['cart'][item_key] = {
                'c': row['주문코드'], 'q': q, 
                'g': row['제품군 대그룹 (Product Group)'], 
                'sz': row['직경'], 'ln': row['길이'], 'm': row['재질/표면처리']
            }
        else:
            if item_key in st.session_state['cart']:
                del st.session_state['cart'][item_key]
