import sys
from streamlit_calendar import calendar
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("handle_sql.py 파일을 찾을 수 없습니다.")

# 페이지 전체 배경색 설정
page_bg_color = "#fcfcfb"
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {page_bg_color};
    }}
    .metric-card {{
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
    }}
    .section-header {{
        font-size: 24px;
        font-weight: 700;
        color: #1f1f1f;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e0e0e0;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 카테고리 구조 정의 ---
CATEGORY_STRUCTURE = {
    "식비": ["식자재/장보기", "외식", "배달/야식", "카페/간식", "술/유흥"],
    "주거/통신": ["월세/관리비", "공과금", "통신비", "구독/OTT"],
    "생활/쇼핑": ["생활용품", "패션/미용", "가전/가구", "반려동물"],
    "교통/차량": ["대중교통", "택시/호출", "자차/주유"],
    "건강/운동": ["병원/약국", "운동/헬스"],
    "교육/계발": ["도서/문구", "강의/수강"],
    "관계": ["경조사/선물", "데이트/모임"],
    "문화/취미": ["영화/공연", "여행"],
    "금융": ["보험/세금", "저축/투자"]
}

# ==========================================
# [DB 함수] 추가 / 수정 / 삭제
# ==========================================

def add_expense(date, time, category, reason, cost, memo):
    try:
        query = """
        INSERT INTO card (date, time, category, reason, cost, memo)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        handle_sql.execute_query(query, (date, time, category, reason, cost, memo))
        return True
    except Exception as e:
        st.error(f"데이터 저장 오류: {e}")
        return False

def update_expense(date, time, category, reason, cost, memo, original_date, original_time, original_category, original_reason):
    try:
        # 시간 형식 보정 (HH:MM -> HH:MM:SS)
        if original_time and len(str(original_time).split(':')) == 2:
            original_time = f"{original_time}:00"
        
        query = """
        UPDATE card 
        SET date = %s, time = %s, category = %s, reason = %s, cost = %s, memo = %s
        WHERE date = %s AND TIME(time) = TIME(%s) AND category = %s AND reason = %s
        LIMIT 1
        """
        handle_sql.execute_query(query, (date, time, category, reason, cost, memo, 
                                         original_date, original_time, original_category, original_reason))
        return True
    except Exception as e:
        st.error(f"데이터 수정 오류: {e}")
        return False

def delete_expense(original_date, original_time, category, reason, cost, memo):
    try:
        # 시간 형식 보정
        if original_time and len(str(original_time).split(':')) == 2:
            original_time = f"{original_time}:00"

        query = """
        DELETE FROM card 
        WHERE date = %s AND TIME(time) = TIME(%s) AND category = %s AND reason = %s AND cost = %s
        LIMIT 1
        """
        handle_sql.execute_query(query, (original_date, original_time, category, reason, cost))
        return True
    except Exception as e:
        st.error(f"데이터 삭제 오류: {e}")
        return False

# --- 세션 스테이트 초기화 ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().date()
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now().time()
if 'current_category' not in st.session_state:
    st.session_state.current_category = list(CATEGORY_STRUCTURE.keys())[0]
if 'current_reason' not in st.session_state:
    st.session_state.current_reason = CATEGORY_STRUCTURE[st.session_state.current_category][0]
if 'current_cost' not in st.session_state:
    st.session_state.current_cost = 0
if 'current_memo' not in st.session_state:
    st.session_state.current_memo = ""

if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_item' not in st.session_state:
    st.session_state.edit_item = None
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()

# ==========================================
# [콜백 함수] 버튼 클릭 시 로직 처리
# ==========================================

# 0. 월 이동 콜백 (수정된 부분)
def change_month_callback(amount):
    """
    amount: -1 (이전 달), 1 (다음 달)
    """
    curr = st.session_state.current_date
    # 월 계산 로직
    new_year = curr.year + (curr.month + amount - 1) // 12
    new_month = (curr.month + amount - 1) % 12 + 1
    
    # 날짜를 1일로 설정하여 '31일' 같은 날짜 오류 방지
    try:
        st.session_state.current_date = curr.replace(year=new_year, month=new_month, day=1)
    except ValueError:
        # 혹시라도 날짜 문제 발생 시 1일로 강제 설정
        st.session_state.current_date = curr.replace(year=new_year, month=new_month, day=1)

# 1. 폼 초기화 콜백
def reset_form_callback():
    st.session_state.current_date = datetime.now().date()
    st.session_state.current_time = datetime.now().time()
    st.session_state.current_cost = 0
    st.session_state.current_memo = ""
    first_cat = list(CATEGORY_STRUCTURE.keys())[0]
    st.session_state.current_category = first_cat
    st.session_state.current_reason = CATEGORY_STRUCTURE[first_cat][0]
    st.session_state.edit_mode = False
    st.session_state.edit_item = None

# 2. 저장(Insert) 콜백
def submit_add_callback():
    success = add_expense(
        st.session_state.current_date.strftime("%Y-%m-%d"),
        st.session_state.current_time.strftime("%H:%M:%S"),
        st.session_state.current_category,
        st.session_state.current_reason,
        int(st.session_state.current_cost),
        st.session_state.current_memo
    )
    if success:
        st.toast("✅ 저장 완료!", icon="💾")
        st.cache_data.clear()
        reset_form_callback()

# 3. 수정(Update) 콜백
def submit_update_callback():
    item = st.session_state.edit_item
    success = update_expense(
        st.session_state.current_date.strftime("%Y-%m-%d"),
        st.session_state.current_time.strftime("%H:%M:%S"),
        st.session_state.current_category,
        st.session_state.current_reason,
        int(st.session_state.current_cost),
        st.session_state.current_memo,
        item['original_date'],
        item['original_time'],
        item['category'],
        item['reason']
    )
    if success:
        st.toast("✅ 수정 완료!", icon="✏️")
        reset_form_callback()

# 4. 삭제(Delete) 콜백
def delete_expense_callback(item):
    success = delete_expense(
        item['original_date'],
        item['original_time'],
        item['category'],
        item['reason'],
        int(item['cost']),
        item['memo']
    )
    if success:
        st.toast("🗑️ 삭제 완료!", icon="✅")
        if st.session_state.edit_mode and st.session_state.edit_item == item:
            reset_form_callback()

# 5. 수정 데이터 불러오기 콜백
def load_edit_data_callback(item):
    try:
        st.session_state.edit_mode = True
        st.session_state.edit_item = item
        
        st.session_state.current_date = datetime.strptime(item['original_date'], '%Y-%m-%d').date()
        
        time_parts = item['original_time'].split(':')
        st.session_state.current_time = datetime.now().replace(
            hour=int(time_parts[0]), 
            minute=int(time_parts[1]) if len(time_parts) > 1 else 0
        ).time()
        
        st.session_state.current_category = item['category']
        st.session_state.current_reason = item['reason']
        st.session_state.current_cost = int(item['cost'])
        st.session_state.current_memo = item['memo']
    except Exception as e:
        print(f"Error loading edit data: {e}")

# ==========================================
# [사이드바] 입력 및 수정 폼
# ==========================================
st.sidebar.header("✏️ 소비 내역 수정" if st.session_state.edit_mode else "📝 소비 내역 입력")

# 여기서 key="current_date"가 바인딩되어 있어서 외부에서 직접 수정 시 에러가 났던 것임
date = st.sidebar.date_input("날짜", key="current_date")
time = st.sidebar.time_input("시간", key="current_time")

category_options = list(CATEGORY_STRUCTURE.keys())
category = st.sidebar.selectbox("대분류", options=category_options, key="current_category")

reason_options = CATEGORY_STRUCTURE.get(category, [])
reason = st.sidebar.selectbox("중분류", options=reason_options, key="current_reason")

cost = st.sidebar.number_input("금액 (원)", min_value=0, step=1000, key="current_cost")
memo = st.sidebar.text_input("메모", placeholder="상세 내용을 입력하세요", max_chars=50, key="current_memo")

col_save, col_cancel = st.sidebar.columns(2)

with col_save:
    if st.session_state.edit_mode:
        st.button("💾 수정 저장", on_click=submit_update_callback, use_container_width=True)
    else:
        st.button("💾 저장", on_click=submit_add_callback, use_container_width=True)

with col_cancel:
    st.button("❌ 취소", on_click=reset_form_callback, use_container_width=True)


# ==========================================
# [메인 화면] 캘린더 및 리스트 조회
# ==========================================
st.markdown("""
<div style="text-align: center; padding: 20px 0; margin-bottom: 30px;">
    <h1 style="color: #1f1f1f; font-size: 36px; font-weight: 700; margin: 0;">
        📊 소비 내역 조회
    </h1>
    <p style="color: #666; font-size: 16px; margin-top: 10px;">
        캘린더로 날짜를 선택하고 지출 내역을 확인하세요
    </p>
</div>
""", unsafe_allow_html=True)

# 월 이동 버튼 (수정된 부분)
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    # on_click으로 변경하여 콜백 함수 호출
    st.button("◀ 지난 달", on_click=change_month_callback, args=(-1,), use_container_width=True)

with col2:
    st.markdown(
        f"<h3 style='text-align: center;'>{st.session_state.current_date.year}년 {st.session_state.current_date.month}월</h3>", 
        unsafe_allow_html=True
    )

with col3:
    # on_click으로 변경하여 콜백 함수 호출
    st.button("다음 달 ▶", on_click=change_month_callback, args=(1,), use_container_width=True)

current_year = st.session_state.current_date.year
current_month = st.session_state.current_date.month

start_date = f"{current_year}-{current_month:02d}-01"
if current_month == 12:
    end_date = f"{current_year + 1}-01-01"
else:
    end_date = f"{current_year}-{current_month + 1:02d}-01"

calendar_events = []
monthly_total = 0
daily_stats = {}

try:
    query = f"""
    SELECT date, time, category, reason, cost, memo
    FROM card
    WHERE date >= '{start_date}' AND date < '{end_date}'
    ORDER BY date, time
    """
    
    df = handle_sql.get_data(query)
    
    if not df.empty:
        results = df.to_dict('records')
        
        for row in results:
            date_val = row['date']
            if isinstance(date_val, (datetime, pd.Timestamp)):
                event_date = date_val.strftime('%Y-%m-%d')
            else:
                event_date = str(date_val)

            cost_val = row.get('cost', 0) or 0
            
            if event_date not in daily_stats:
                daily_stats[event_date] = {'total': 0, 'items': []}
            
            daily_stats[event_date]['total'] += cost_val
            
            time_value = row.get('time', '')
            time_str = ''
            original_time_db = ''
            
            if time_value is not None:
                if hasattr(time_value, 'total_seconds'):
                    total_seconds = int(time_value.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                    original_time_db = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    time_str = str(time_value)
                    if ':' in time_str:
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            original_time_db = f"{parts[0]}:{parts[1]}:00"
                        else:
                            original_time_db = time_str
                    else:
                        original_time_db = time_str

            daily_stats[event_date]['items'].append({
                'category': row.get('category', ''),
                'reason': row.get('reason', ''),
                'cost': cost_val,
                'time': time_str,
                'memo': row.get('memo', ''),
                'original_date': event_date,
                'original_time': original_time_db
            })
            
            monthly_total += cost_val
    
    for date_key, stats in daily_stats.items():
        event = {
            "title": f"{stats['total']:,}원",
            "start": date_key,
            "allDay": True,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "textColor": "#dc3545",
        }
        calendar_events.append(event)
    
except Exception as e:
    st.error(f"❌ 데이터 조회 오류: {e}")

# 메트릭 카드 스타일 함수
def create_metric_card(title, value, value_color="#1f1f1f"):
    return f"""
    <div class="metric-card">
        <div style="font-size: 13px; color: #666; margin-bottom: 8px; font-weight: 500;">
            {title}
        </div>
        <div style="font-size: 28px; font-weight: 700; color: {value_color};">
            {value}
        </div>
    </div>
    """

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; }
    .fc-event-title { font-weight: bold !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
with col_a:
    avg_daily = monthly_total / len(daily_stats) if len(daily_stats) > 0 else 0
    st.markdown(create_metric_card("💰 월 총 소비", f"{monthly_total:,}원"), unsafe_allow_html=True)
with col_b:
    st.markdown(create_metric_card("📅 소비 일수", f"{len(daily_stats)}일"), unsafe_allow_html=True)
with col_c:
    st.markdown(create_metric_card("📊 일평균 소비", f"{avg_daily:,.0f}원"), unsafe_allow_html=True)

st.markdown("---")

calendar_options = {
    "editable": False,
    "selectable": True,
    "headerToolbar": {"left": "", "center": "", "right": ""},
    "initialView": "dayGridMonth",
    "initialDate": f"{current_year}-{current_month:02d}-01",
    "locale": "ko",
    "height": 600,
}

state = calendar(
    events=calendar_events, 
    options=calendar_options, 
    key=f"calendar_{current_year}_{current_month}"
)

if state and state.get('dateClick'):
    clicked_raw = state['dateClick']['date']
    try:
        if 'T' in clicked_raw:
            dt_obj = datetime.fromisoformat(clicked_raw.replace('Z', '+00:00'))
            kst_date = (dt_obj + timedelta(hours=9)).date()
            st.session_state.selected_date = kst_date
        else:
            st.session_state.selected_date = datetime.strptime(clicked_raw[:10], '%Y-%m-%d').date()
    except Exception as e:
        st.error(f"날짜 선택 오류: {e}")

elif state and state.get('eventClick'):
    event_raw = state['eventClick']['event']['start']
    try:
        if 'T' in event_raw:
            dt_obj = datetime.fromisoformat(event_raw.replace('Z', '+00:00'))
            kst_date = (dt_obj + timedelta(hours=9)).date()
            st.session_state.selected_date = kst_date
        else:
            st.session_state.selected_date = datetime.strptime(event_raw[:10], '%Y-%m-%d').date()
    except Exception as e:
        st.error(f"이벤트 선택 오류: {e}")

selected_date_str = st.session_state.selected_date.strftime('%Y-%m-%d')

if selected_date_str in daily_stats:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-header">📅 {selected_date_str} 소비 내역</div>', unsafe_allow_html=True)
    
    stats = daily_stats[selected_date_str]
    st.markdown(f"""
    <div style="background-color: #e7f5ff; padding: 15px; border-radius: 8px; border-left: 4px solid #1c7ed6; margin-bottom: 20px;">
        <h4 style="color: #0b7285; margin: 0;">
            일 총 소비: <span style="color: #1c7ed6; font-weight: 700;">{stats['total']:,}원</span>
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    for idx, item in enumerate(stats['items']):
        with st.container():
            col_info, col_btn = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"""
                <div style="padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9;">
                    <strong>{item['time'] or '-'}</strong> | 
                    <strong>{item['category'] or '-'}</strong> - {item['reason'] or '-'} | 
                    <strong style="color: #dc3545;">{item['cost']:,}원</strong>
                    {f'<br><small style="color: #666;">메모: {item["memo"] or "-"}</small>' if item.get('memo') else ''}
                </div>
                """, unsafe_allow_html=True)
            
            with col_btn:
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                # 버튼을 담을 2개의 작은 컬럼 생성
                btn_edit, btn_del = st.columns(2)
                
                with btn_edit:
                    st.button(
                        "✏️", 
                        key=f"edit_{selected_date_str}_{idx}",
                        on_click=load_edit_data_callback,
                        args=(item,),
                        help="수정",
                        use_container_width=True
                    )
                
                with btn_del:
                    st.button(
                        "🗑️",
                        key=f"del_{selected_date_str}_{idx}",
                        on_click=delete_expense_callback,
                        args=(item,),
                        help="삭제",
                        type="primary", # 빨간색 버튼 강조
                        use_container_width=True
                    )
            
            st.markdown("---")
    
    with st.expander("📋 테이블 보기"):
        detail_data = [{
            '시간': i['time'], '카테고리': i['category'], '내용': i['reason'], 
            '금액': f"{i['cost']:,}원", '메모': i['memo']
        } for i in stats['items']]
        st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)
        
elif selected_date_str:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(f"📆 {selected_date_str}에는 소비 내역이 없습니다.")