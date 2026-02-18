import streamlit as st
import pandas as pd
import requests
import os

# --- [규칙 1] 반드시 최상단 설정 ---
st.set_page_config(page_title="주문 시스템 v2.2", layout="centered")

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

# --- 2. 데이터 보정 및 자동 매핑 ---
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
        # 모든 열을 문자열로 바꾼 뒤 공백 제거 (에러 완전 차단)
        df = df.fillna("").astype(str).apply(lambda x: x.str.strip())
        
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

        # Biomaterial 수동 추가
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
    rep_key = st.query_params.get("rep", "lee")
    url_cust = st.query_params.get("cust", "")
except:
    try:
        rep_key = st.experimental_get_query_params().get("rep", ["lee"])[0]
        url_cust = st.experimental_get_query_params().get("cust", [""])[0]
    except:
        rep_key = "lee"
        url_cust = ""

current_rep = SALES_REPS.get(str(rep_key).lower(), SALES_REPS["lee"])

if 'selected_cat' not in st.session_state: st.session_state.selected_cat = "전체"
if 'cart' not in st.session_state: st.session_state['cart'] = {}
if 'show_confirm' not in st.session_state: st.session_state.show_confirm = False

df, info, status = load_data()
if df is None:
    st.error(f"❌ 시스템 로드 중 오류: {status}")
    st.stop()

# --- 4. 메인 UI (사이드바 정보) ---
st.title(f"🛒 {current_rep['name']} 전용 채널")

st.sidebar.header("🏢 주문자 정보")
c_name = st.sidebar.text_input("거래처명", value=url_cust, disabled=(url_cust != ""))
m_name = st.sidebar.text_input("담당자 성함 (필수)")

if st.session_state['cart']:
    st.sidebar.divider()
    st.sidebar.subheader("🛒 담은 품목")
    for v in st.session_state['cart'].values():
        st.sidebar.caption(f"• {v['name'][:10]}.. {v['q']}개")
    if st.sidebar.button("🚀 최종 주문 확인", use_container_width=True):
        if not c_name or not m_name: 
            st.sidebar.error("거래처 정보를 입력해 주세요!")
        else:
            # 팝업창 대신 '상태'를 변경하여 확인창을 띄웁니다.
            st.session_state.show_confirm = True
            st.rerun()

# --- 5. [안전한 확인창] 팝업(dialog) 대신 화면 고정 방식 ---
if st.session_state.show_confirm:
    st.warning("📋 주문 내용을 최종 확인해 주세요.")
    with st.container(border=True):
        is_ex = st.checkbox("🔄 교환 주문 (선납 건)")
        st.caption("교환 제품은 **유효기간 1년 이상** 필수입니다.")
        st.divider()
        
        for item in st.session_state['cart'].values():
            st.write(f"• {item['name']} : **{item['q']}개**")
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 전송하기", use_container_width=True):
                items_msg = "\n".join([f"{v['c']} / {v['q']}개" for v in st.session_state['cart'].values()])
                action = "선납주문 부탁드립니다." if is_ex else "주문부탁드립니다."
                full_msg = f"🔔 [{current_rep['name']}] 주문접수\n🏢 {c_name}\n👤 {m_name}\n\n{items_msg}\n\n{c_name} {action}"
                
                if send_telegram(full_msg, current_rep['id'])[0]:
                    st.success("주문이 성공적으로 전송되었습니다.")
                    st.balloons()
                    st.session_state['cart'] = {}
                    st.session_state.show_confirm = False
                    st.rerun()
                else: 
                    st.error("전송에 실패했습니다.")
        with c2:
            if st.button("❌ 취소 및 돌아가기", use_container_width=True):
                st.session_state.show_confirm = False
                st.rerun()
    # 확인창이 떠 있을 때는 아래 제품 목록이 안 보이게 화면 멈춤
    st.stop() 

# --- 6. 카테고리 메뉴 ---
st.write("### 📂 품목군 선택")
cats = ["BL", "TL", "BLX", "TLX", "Biomaterial"]
cols = st.columns(3)
for i, c in enumerate(cats):
    with cols[i % 3]:
        # 구버전 충돌 방지를 위해 버튼 색상(type) 제거
        btn_label = f"✨ {c}" if st.session_state.selected_cat == c else c
        if st.button(btn_label, use_container_width=True):
            st.session_state.selected_cat = c

if st.button("🔄 전체 보기 / 초기화", use_container_width=True):
    st.session_state.selected_cat = "전체"
    st.session_state['cart'] = {}
    st.rerun()

st.divider()

# --- 7. 필터링 및 리스트 출력 ---
cat_col = info['cat']
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
        title = row[info['mat']] if is_bio else row[cat_col]
        st.markdown(f"#### {title}")
        st.code(row[info['code']])
        if is_bio: 
            st.caption("📍 분류: Biomaterial")
        else: 
            st.caption(f"📍 {row[info['dia']]} x {row[info['len']]} | {row[info['mat']]}")
        
        prev = st.session_state['cart'].get(k, {}).get('q', 0)
        q = st.number_input("수량 입력", 0, 1000, key=f"q_{idx}", value=int(prev), label_visibility="collapsed")
        
        if q > 0:
            st.session_state['cart'][k] = {
                'c': row[info['code']], 'q': q, 
                'name': title + (f" ({row[info['dia']]}x{row[info['len']]})" if not is_bio else "")
            }
        else:
            if k in st.session_state['cart']: del st.session_state['cart'][k]
