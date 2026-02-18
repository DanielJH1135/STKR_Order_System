import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v2.1", layout="centered")

# --- 1. 담당자 및 텔레그램 설정 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

# 구글 시트 모듈 (없어도 에러 안 나게 처리)
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 보정 로직 ---
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
        return None, None, "엑셀 파일을 찾을 수 없습니다."
    try:
        df = pd.read_excel(file_path, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        # 열 이름 유연하게 찾기
        def find_col(keys):
            for k in keys:
                for col in df.columns:
                    if k.lower() in col.lower(): return col
            return None

        m = {
            'cat': find_col(['제품군', 'Group', '대그룹']) or '제품군',
            'code': find_col(['코드', 'Code', '품번']) or '주문코드',
            'mat': find_col(['재질', '표면', 'Material']) or '재질/표면처리',
            'dia': find_col(['직경', 'Dia', 'D']) or '직경',
            'len': find_col(['길이', 'Len', 'L']) or '길이'
        }

        # Biomaterial 수동 추가 (사장님 요청 사양)
        bio_data = [
            {m['cat']: 'Biomaterial', m['code']: '075.101w', m['mat']: 'Emdogain 0.3ml', m['dia']: '-', m['len']: '-'},
            {m['cat']: 'Biomaterial', m['code']: '075.102w', m['mat']: 'Emdogain 0.7ml', m['dia']: '-', m['len']: '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio_data)], ignore_index=True)
        if m['code'] in df.columns:
            df[m['code']] = df[m['code']].apply(format_order_code)
        return df, m, "성공"
    except Exception as e: return None, None, str(e)

# --- 3. 담당자 및 파라미터 판별 (가장 안전한 방식) ---
try:
    # 최신 Streamlit 방식
    rep_key = st.query_params.get("rep", "lee")
    url_cust = st.query_params.get("cust", "")
except:
    try:
        # 구버전 방식 대비
        rep_key = st.experimental_get_query_params().get("rep", ["lee"])[0]
        url_cust = st.experimental_get_query_params().get("cust", [""])[0]
    except:
        rep_key = "lee"
        url_cust = ""

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, info, status = load_data()
if df is None:
    st.error(f"❌ 시스템 로드 중 오류: {status}")
    st.stop()

# --- 4. 최종 확인 팝업 (정중한 표현 및 복붙 최적화) ---
@st.dialog("📋 주문 내용을 최종 확인해 주세요")
def confirm_dialog(cust, mgr):
    st.write("주문 품목과 수량이 정확한지 확인해 주시기 바랍니다.")
    is_ex = st.checkbox("🔄 교환 주문 (선납 건)")
    st.markdown("교환 제품은 **유효기간 1년 이상** 남은 제품만 가능함을 알려드립니다.")
    st.divider()
    
    for item in st.session_state['cart'].values():
        st.write(f"• {item['name']} : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 확인 및 전송", use_container_width=True, type="primary"):
        # 텔레그램 메시지 구성 (과장님 '딸깍' 복붙 형식)
        items_msg = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        
        # 9:41 PM 형식 유지 + 하단 고정 멘트
        full_msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {cust}\n👤 {mgr}\n\n{items_msg}\n\n{cust} {action}"
        
        if send_telegram(full_msg, current_rep['id'])[0]:
            st.success("주문이 성공적으로 전송되었습니다.")
            st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error("전송에 실패했습니다. 관리자에게 문의 바랍니다.")

# --- 5. 메인 UI 및 제품 목록 ---
st.title(f"🛒 {current_rep['name']} 전용 주문 채널")

# 시스템 선택 버튼
st.write("### 📂 품목군 선택")
cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, c in enumerate(cats):
    with cols[i % 3]:
        if st.button(c, use_container_width=True, type="primary" if st.session_state.selected_cat == c else "secondary"):
            st.session_state.selected_cat = c

if st.button("🔄 전체 초기화 및 새로고침", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state['cart'] = {}; st.rerun()

st.divider()

# 사이드바
st.sidebar.header("🏢 주문자 정보")
c_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
m_name = st.sidebar.text_input("담당자 성함 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 실시간 장바구니")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['name'][:10]}.. {v['q']}개")
    if st.sidebar.button("🚀 최종 주문 전송", use_container_width=True, type="primary"):
        if not c_name or not m_name: st.sidebar.error("거래처 정보를 입력해 주세요!")
        else: confirm_dialog(c_name, m_name)

# 필터링 및 리스트 출력
cat_col = info['cat']
f_df = df.copy()

if st.session_state.selected_cat != "전체":
    target = st.session_state.selected_cat.strip().upper()
    if target in ["BL", "TL"]:
        f_df = f_df[f_df[cat_col].str.strip().str.upper() == target]
    else:
        f_df = f_df[f_df[cat_col].str.strip().str.upper().str.contains(target, na=False)]

st.write(f"현재 선택: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    is_bio = str(row[cat_col]).strip().upper() == "BIOMATERIAL"
    with st.container(border=True):
        title = row[info['mat']] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[info['code']])
        if is_bio: st.caption("📍 분류: Biomaterial")
        else: st.caption(f"📍 {row[info['dia']]} x {row[info['len']]} | {row[info['mat']]}")
        
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량 입력", 0, 1000, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][k] = {
                'c': row[info['code']], 'q': q, 'name': title + (f" ({row[info['dia']]}x{row[info['len']]})" if not is_bio else "")
            }
        else:
            if k in st.session_state['cart']: del st.session_state['cart'][k]
