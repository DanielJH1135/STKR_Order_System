import streamlit as st
import pandas as pd
import requests

# --- [설정] 본인의 정보로 수정하세요 ---
TELEGRAM_TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"
CHAT_ID = 1781982606 # 예: 12345678 (따옴표 없이 숫자만)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            return True, "성공"
        else:
            # 상세 에러 메시지 반환 (디버깅용)
            return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# 1. 데이터 불러오기 및 코드 보정
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("")

        # [핵심] 정교한 코드 보정 함수
        def fix_order_code(code):
            code = str(code).strip()
            if not code or code.lower() == "nan": return ""
            
            # 점(.)이 포함된 경우의 처리
            if "." in code:
                prefix, suffix = code.split(".", 1)
                
                # 1. 점 앞자리 (prefix): 숫자라면 3자리로 맞춤 (앞에 0 채우기)
                if prefix.isdigit():
                    prefix = prefix.zfill(3)
                
                # 2. 점 뒷자리 (suffix): 숫자와 문자를 분리
                # 예: "001" -> "0010" (4자리), "906s" -> "906s" (문자있으면 그대로)
                match = re.match(r"(\d+)([a-zA-Z]*)", suffix)
                if match:
                    num_part = match.group(1)
                    char_part = match.group(2)
                    
                    if char_part: # 문자가 있으면 (예: s)
                        # 보통 3자리+문자 형식이 많으므로 그대로 두거나 3자리 보정
                        return f"{prefix}.{num_part}{char_part}"
                    else: # 순수 숫자면 4자리로 맞춤 (뒤에 0 채우기)
                        return f"{prefix}.{num_part.ljust(4, '0')}"
            
            return code

        df['주문코드'] = df['주문코드'].apply(fix_order_code)
        return df
    except Exception as e:
        st.error(f"엑셀 읽기 오류: {e}")
        return pd.DataFrame()

df = load_data()

# 세션 스테이트 초기화
if 'order_data' not in st.session_state:
    st.session_state['order_data'] = {}

if not df.empty:
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("📦 거래처 주문 페이지")

    # --- 사이드바 ---
    st.sidebar.header("🏢 주문자 정보")
    cust_name = st.sidebar.text_input("거래처명")
    mgr_name = st.sidebar.text_input("담당자명")

    st.sidebar.divider()
    st.sidebar.header("🔍 필터")
    cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[col_group].unique()))
    mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df[col_material].unique()))

    filtered_df = df.copy()
    if cat != "전체": filtered_df = filtered_df[filtered_df[col_group] == cat]
    if mat != "전체": filtered_df = filtered_df[filtered_df[col_material] == mat]

    # --- 메인 리스트 ---
    h = st.columns([0.5, 3, 1, 1, 1.5])
    cols_text = ["선택", "품목 정보", "직경", "길이", "수량"]
    for c, t in zip(h, cols_text): c.write(f"**{t}**")
    st.divider()

    for idx, row in filtered_df.iterrows():
        code = row[col_code]
        item_key = f"item_{idx}"
        saved = st.session_state['order_data'].get(item_key, {})
        
        r_cols = st.columns([0.5, 3, 1, 1, 1.5])
        with r_cols[0]:
            sel = st.checkbox("", key=f"c_{idx}", value=(item_key in st.session_state['order_data']))
        with r_cols[1]:
            st.markdown(f"**{row[col_group]}**")
            st.code(code)
            st.caption(row[col_material])
        with r_cols[2]: st.write(row[col_size])
        with r_cols[3]: st.write(row[col_length])
        with r_cols[4]:
            q = st.number_input("수량", 0, 1000, key=f"q_{idx}", value=int(saved.get('qty', 0)), label_visibility="collapsed")

        if sel and q > 0:
            st.session_state['order_data'][item_key] = {'code': code, 'qty': q}
        else:
            st.session_state['order_data'].pop(item_key, None)

    # --- 전송 섹션 ---
    st.sidebar.divider()
    if st.session_state['order_data']:
        sum_list = [f"- {v['code']} / {v['qty']}개" for v in st.session_state['order_data'].values()]
        st.sidebar.text_area("내역", "\n".join(sum_list), height=200)
        
        if st.sidebar.button("🚀 주문 전송"):
            if not cust_name or not mgr_name:
                st.sidebar.error("정보를 입력하세요")
            else:
                msg = f"🔔 [새 주문]\n🏢 {cust_name}\n👤 {mgr_name}\n----\n" + "\n".join(sum_list)
                ok, err = send_telegram_message(msg)
                if ok:
                    st.balloons()
                    st.sidebar.success("발송 성공!")
                else:
                    st.sidebar.error(f"실패: {err}")
                    st.sidebar.info("봇에게 /start 를 보냈는지 확인하세요.")
