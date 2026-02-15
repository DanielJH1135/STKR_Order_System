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
            return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# 1. 데이터 불러오기 및 정밀 코드 보정
@st.cache_data
def load_data():
    try:
        # 엑셀을 읽을 때 일단 모든 값을 문자로 가져옵니다.
        df = pd.read_excel("order_database.xlsx", dtype=str)
        df = df.fillna("")

        def fix_order_code(code):
            # 문자가 아니거나 비어있으면 빈값 반환
            code = str(code).strip()
            if not code or code.lower() == "nan": 
                return ""
            
            # 점(.)이 있는 경우 (예: 21.001 -> 021.0010)
            if "." in code:
                parts = code.split(".")
                prefix = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                
                # 점 앞자리: 무조건 3자리로 맞춤 (앞에 0 채우기)
                if prefix.isdigit():
                    prefix = prefix.zfill(3)
                
                # 점 뒷자리: 숫자 부분만 추출해서 뒤에 0을 붙여 4자리로 맞춤
                # 예: "001" -> "0010", "906s" -> "906s" (문자 섞이면 보존)
                nums = re.findall(r'\d+', suffix)
                chars = re.findall(r'[a-zA-Z]+', suffix)
                
                if nums and not chars: # 순수 숫자면 4자리 보정
                    suffix = nums[0].ljust(4, '0')
                elif nums and chars: # 문자 섞여있으면 원래대로 (예: 906s)
                    suffix = suffix
                
                return f"{prefix}.{suffix}"
            
            # 점(.)이 없는 코드인데 숫자로만 된 경우 (예: 615308 -> 0615308)
            # 만약 사장님 코드 중 점 없는 것도 0이 빠진다면 아래 zfill을 활성화하세요.
            # if code.isdigit() and len(code) < 8: return code.zfill(8)
            
            return code

        df['주문코드'] = df['주문코드'].apply(fix_order_code)
        return df
    except Exception as e:
        # 어떤 에러인지 화면에 구체적으로 표시
        st.error(f"❌ 엑셀 읽기 오류 상세: {e}")
        return pd.DataFrame()

df = load_data()

# --- 세션 상태 ---
if 'order_items' not in st.session_state:
    st.session_state['order_items'] = {}

if not df.empty:
    col_group = '제품군 대그룹 (Product Group)'
    col_material = '재질/표면처리'
    col_size = '직경'
    col_length = '길이'
    col_code = '주문코드'

    st.set_page_config(page_title="주문 시스템", layout="wide")
    st.title("🛒 거래처 전용 주문 페이지")

    # --- 사이드바 ---
    st.sidebar.header("🏢 주문자 정보")
    c_name = st.sidebar.text_input("거래처명")
    m_name = st.sidebar.text_input("담당자명")

    st.sidebar.divider()
    st.sidebar.header("🔍 필터")
    cat = st.sidebar.selectbox("제품군", ["전체"] + sorted(df[col_group].unique()))
    mat = st.sidebar.selectbox("재질", ["전체"] + sorted(df[col_material].unique()))

    f_df = df.copy()
    if cat != "전체": f_df = f_df[f_df[col_group] == cat]
    if mat != "전체": f_df = f_df[f_df[col_material] == mat]

    # --- 메인 목록 ---
    h = st.columns([0.5, 3, 1, 1, 1.5])
    labels = ["선택", "품목/주문코드", "직경", "길이", "수량"]
    for c, l in zip(h, labels): c.write(f"**{l}**")
    st.divider()

    for idx, row in f_df.iterrows():
        code = row[col_code]
        item_id = f"item_{idx}"
        
        # 이전 선택 값 불러오기
        saved = st.session_state['order_items'].get(item_id, {})
        
        r = st.columns([0.5, 3, 1, 1, 1.5])
        with r[0]:
            is_sel = st.checkbox("", key=f"cb_{idx}", value=(item_id in st.session_state['order_items']))
        with r[1]:
            st.markdown(f"**{row[col_group]}**")
            st.code(code) # 여기서 021.0010 처럼 보여야 함
            st.caption(row[col_material])
        with r[2]: st.write(row[col_size])
        with r[3]: st.write(row[col_length])
        with r[4]:
            q = st.number_input("수량", 0, 1000, key=f"num_{idx}", value=int(saved.get('qty', 0)), label_visibility="collapsed")

        # 상태 업데이트
        if is_sel and q > 0:
            st.session_state['order_items'][item_id] = {'code': code, 'qty': q}
        else:
            st.session_state['order_items'].pop(item_id, None)

    # --- 장바구니 및 전송 ---
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    
    if st.session_state['order_items']:
        order_texts = [f"- {v['code']} / {v['qty']}개" for v in st.session_state['order_items'].values()]
        full_order_text = "\n".join(order_texts)
        st.sidebar.text_area("내역", full_order_text, height=200)
        
        if st.sidebar.button("🚀 주문 보내기"):
            if not c_name or not m_name:
                st.sidebar.error("거래처/담당자명을 적어주세요.")
            else:
                msg = f"🔔 [새 주문]\n🏢 {c_name}\n👤 {m_name}\n----\n{full_order_text}"
                success, error = send_telegram_message(msg)
                if success:
                    st.balloons()
                    st.sidebar.success("성공적으로 보냈습니다!")
                else:
                    st.sidebar.error(f"실패: {error}")
    else:
        st.sidebar.info("품목을 선택해주세요.")

    if st.sidebar.button("🗑️ 초기화"):
        st.session_state['order_items'] = {}
        st.rerun()
