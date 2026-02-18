import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v2.0", layout="centered")

# --- 1. 담당자 및 텔레그램 설정 ---
SALES_REPS = {
    "lee": {"name": "이정현 과장", "id": "1781982606"},
    "park": {"name": "박성배 소장", "id": "여기에_박소장님_ID_입력"}, 
    "jang": {"name": "장세진 차장", "id": "여기에_장차장님_ID_입력"}
}
TOKEN = "7990356470:AAFeLyeK-8V4Misqb0SDutxa6zpYx_abnGw"

# 구글 시트 모듈 (에러 방지용)
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    conn = None

def send_telegram(msg, chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

# --- 2. 데이터 보정 및 유연한 열 매핑 (강화된 버전) ---
def format_order_code(c):
    c = str(c).strip()
    if not c or c.lower() == "nan": return ""
    if "." in c:
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
        # 열 이름을 대문자로 바꾸고 공백 제거해서 비교 (에러 방지 핵심)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("").apply(lambda x: x.str.strip())
        
        # 실제 엑셀 열 이름 중 키워드와 가장 비슷한 것 찾기
        def find_col(keywords):
            for k in keywords:
                for col in df.columns:
                    if k.lower() in col.lower(): return col
            return None

        # 매핑된 실제 열 이름들
        m = {
            'cat': find_col(['제품군', 'Group', '대그룹']),
            'code': find_col(['코드', 'Code', '품번']),
            'mat': find_col(['재질', '표면', 'Material']),
            'dia': find_col(['직경', 'Dia', 'D']),
            'len': find_col(['길이', 'Len', 'L'])
        }
        
        # 만약 열 이름을 하나라도 못 찾으면 기본값 설정
        m = {k: (v if v else k) for k, v in m.items()}

        # Biomaterial 수동 추가 (매핑된 열 이름 사용)
        bio_data = [
            {m['cat']: 'Biomaterial', m['code']: '075.101w', m['mat']: 'Emdogain 0.3ml', m['dia']: '-', m['len']: '-'},
            {m['cat']: 'Biomaterial', m['code']: '075.102w', m['mat']: 'Emdogain 0.7ml', m['dia']: '-', m['len']: '-'}
        ]
        df = pd.concat([df, pd.DataFrame(bio_data)], ignore_index=True)
        
        # 주문코드 정규화
        if m['code'] in df.columns:
            df[m['code']] = df[m['code']].apply(format_order_code)
            
        return df, m, "성공"
    except Exception as e:
        return None, None, f"데이터 처리 중 오류: {str(e)}"

# --- 3. URL 파라미터 및 담당자 설정 (52번 라인 오류 해결) ---
query_params = st.query_params
rep_key = query_params.get("rep", "lee")
if isinstance(rep_key, list): rep_key = rep_key[0] # 리스트 방지 로직

url_cust = query_params.get("cust", "")
if isinstance(url_cust, list): url_cust = url_cust[0]

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

# 상태 유지
if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}

df, info, status = load_data()
if df is None:
    st.error(status)
    st.stop()

# --- 4. 최종 확인 팝업 (9:41 PM 형식 적용) ---
@st.dialog("📋 주문 내역 최종 확인")
def confirm_dialog(cust, mgr):
    st.write("주문 품목과 수량을 확인해 주세요.")
    is_ex = st.checkbox("🔄 교환 주문 (선납)")
    st.markdown("교환 제품은 **유효기간 1년 이상** 필수입니다.")
    st.divider()
    
    for item in st.session_state['cart'].values():
        st.write(f"• {item['name']} : **{item['q']}개**")
    
    st.divider()
    if st.button("✅ 주문 전송", use_container_width=True, type="primary"):
        # 사장님 딸깍용 메시지 구성
        items_msg = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
        action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
        
        full_msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {cust}\n👤 {mgr}\n\n{items_msg}\n\n{cust} {action}"
        
        if send_telegram(full_msg, current_rep['id'])[0]:
            st.success("전송 성공!"); st.balloons()
            st.session_state['cart'] = {}; st.rerun()
        else: st.error("전송 실패. 네트워크를 확인하세요.")

# --- 5. 메인 UI ---
st.title(f"🛒 {current_rep['name']} 주문")

# 상단 시스템 내비게이션
st.write("### 📂 품목군 선택")
cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, c in enumerate(cats):
    with cols[i % 3]:
        if st.button(c, use_container_width=True, type="primary" if st.session_state.selected_cat == c else "secondary"):
            st.session_state.selected_cat = c

if st.button("🔄 전체 초기화/보기", use_container_width=True):
    st.session_state.selected_cat = "전체"; st.session_state['cart'] = {}; st.rerun()

# 사이드바 주문 정보
st.sidebar.header("🏢 주문자 정보")
c_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
m_name = st.sidebar.text_input("담당자 성함 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 담은 품목")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"{v['name'][:10]}.. {v['q']}개")
    if st.sidebar.button("🚀 최종 주문하기", use_container_width=True, type="primary"):
        if not c_name or not m_name: st.sidebar.error("거래처 정보를 입력하세요!")
        else: confirm_dialog(c_name, m_name)
else:
    st.sidebar.warning("수량을 입력하면 담깁니다.")

# --- 6. 제품 리스트 필터링 (가장 안전한 필터 로직) ---
cat_col = info['cat']
f_df = df.copy()

if st.session_state.selected_cat != "전체":
    # 엑셀 데이터의 공백을 지우고 검색어와 비교
    target = st.session_state.selected_cat.strip().upper()
    if target in ["BL", "TL"]: # 정확히 일치해야 하는 카테고리
        f_df = f_df[f_df[cat_col].str.strip().str.upper() == target]
    else: # BLX, TLX, Biomaterial 등 포함 검색
        f_df = f_df[f_df[cat_col].str.strip().str.upper().str.contains(target, na=False)]

st.write(f"현재: **{st.session_state.selected_cat}** ({len(f_df)}건)")

for idx, row in f_df.iterrows():
    k = f"row_{idx}"
    is_bio = str(row[cat_col]).strip().upper() == "BIOMATERIAL"
    
    with st.container(border=True):
        # Biomaterial은 제품 이름을 제목으로, 나머지는 제품군을 제목으로
        title = row[info['mat']] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[info['code']])
        
        if is_bio: st.caption("📍 분류: Biomaterial")
        else: st.caption(f"📍 {row[info['dia']]} x {row[info['len']]} | {row[info['mat']]}")
        
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량", 0, 1000, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][k] = {
                'c': row[info['code']], 'q': q, 'name': title + (f" ({row[info['dia']]}x{row[info['len']]})" if not is_bio else "")
            }
        else:
            if k in st.session_state['cart']: del st.session_state['cart'][k]
