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

# 카테고리 구조 정의
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

# 데이터 추가 함수
def add_expense(date, time, category, reason, cost, memo):
    try:
        # handle_sql을 사용하여 데이터 삽입 (card 테이블로 변경)
        query = """
        INSERT INTO card (date, time, category, reason, cost, memo)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        handle_sql.execute_query(query, (date, time, category, reason, cost, memo))
        return True
    except Exception as e:
        st.error(f"데이터 저장 오류: {e}")
        return False

# 데이터 수정 함수
def update_expense(date, time, category, reason, cost, memo, original_date, original_time, original_category, original_reason):
    try:
        # handle_sql을 사용하여 데이터 수정
        # 시간 형식이 HH:MM인 경우 HH:MM:SS로 변환
        if original_time and len(original_time.split(':')) == 2:
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

# --- 초기 설정 및 세션 스테이트 초기화 ---
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now().date()
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now().time()
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_item' not in st.session_state:
    st.session_state.edit_item = None

# --- 사이드바 헤더 및 수정 모드 데이터 로드 ---
if st.session_state.edit_mode:
    st.sidebar.header("✏️ 지출 내역 수정")
    item = st.session_state.edit_item
    
    # 수정 버튼을 눌렀을 때 최초 1회만 위젯 값을 수정 데이터로 동기화
    if st.session_state.get('needs_sync', False):
        try:
            st.session_state.input_date = datetime.strptime(item['original_date'], '%Y-%m-%d').date()
            time_parts = item['original_time'].split(':')
            st.session_state.input_time = datetime.now().replace(
                hour=int(time_parts[0]), 
                minute=int(time_parts[1]) if len(time_parts) > 1 else 0
            ).time()
        except:
            pass
        st.session_state.needs_sync = False # 동기화 완료 후 플래그 해제
else:
    st.sidebar.header("📝 지출 내역 입력")

# --- 1. 날짜/시간 입력 ---
# value 대신 key를 사용하면 사용자가 입력을 바꿀 때마다 세션 스테이트에 자동 저장됩니다.
date = st.sidebar.date_input("날짜", key="current_date")
time = st.sidebar.time_input("시간", key="current_time")

# --- 2. 대분류 선택 ---
category_options = list(CATEGORY_STRUCTURE.keys())
curr_cat_idx = 0
if st.session_state.edit_mode and st.session_state.edit_item:
    orig_cat = st.session_state.edit_item.get('category')
    if orig_cat in category_options:
        curr_cat_idx = category_options.index(orig_cat)

category = st.sidebar.selectbox(
    "카테고리 (대분류)", 
    options=category_options,
    index=curr_cat_idx
)

# --- 3. 중분류 선택 ---
reason_options = CATEGORY_STRUCTURE.get(category, [])
curr_reason_idx = 0
if st.session_state.edit_mode and st.session_state.edit_item:
    orig_reason = st.session_state.edit_item.get('reason')
    if orig_reason in reason_options:
        curr_reason_idx = reason_options.index(orig_reason)

reason = st.sidebar.selectbox("사유 (중분류)", options=reason_options, index=curr_reason_idx)

# --- 4. 금액 및 메모 ---
# 금액과 메모는 위젯 재실행 시 초기화되는 문제를 방지하기 위해 
# 수정 모드일 때만 value를 명시적으로 할당합니다.
if st.session_state.edit_mode:
    cost = st.sidebar.number_input("금액 (원)", min_value=0, step=1000, value=int(st.session_state.edit_item.get('cost', 0)))
    memo = st.sidebar.text_input("메모", value=st.session_state.edit_item.get('memo', ''), max_chars=50)
else:
    cost = st.sidebar.number_input("금액 (원)", min_value=0, step=1000)
    memo = st.sidebar.text_input("메모", placeholder="상세 내용을 입력하세요", max_chars=50)

# --- 5. 저장/수정/취소 버튼 ---
col_save, col_cancel = st.sidebar.columns(2)

with col_save:
    if st.session_state.edit_mode:
        if st.button("💾 수정 저장", use_container_width=True):
            # update_expense 함수 호출 시 모든 인자를 정확히 전달
            if update_expense(
                date.strftime("%Y-%m-%d"),
                time.strftime("%H:%M:%S"),
                category,
                reason,
                int(cost),
                memo,
                st.session_state.edit_item['original_date'],
                st.session_state.edit_item['original_time'],
                st.session_state.edit_item['category'],
                st.session_state.edit_item['reason']
            ):
                st.sidebar.success("✅ 수정 완료!")
                st.session_state.edit_mode = False
                st.session_state.edit_item = None
                
                # 위젯 에러 방지를 위해 del 사용
                if 'current_date' in st.session_state:
                    del st.session_state.current_date
                if 'current_time' in st.session_state:
                    del st.session_state.current_time
                st.rerun()
    else:
        # 입력 모드 저장 버튼
        if st.button("💾 저장", use_container_width=True):
            # add_expense 함수 호출 시 정의된 6개 인자 모두 전달
            if add_expense(
                date.strftime("%Y-%m-%d"),
                time.strftime("%H:%M:%S"),
                category,
                reason,
                int(cost),
                memo
            ):
                st.sidebar.success("✅ 저장 완료!")
                
                # 위젯 에러 방지를 위해 del 사용
                if 'current_date' in st.session_state:
                    del st.session_state.current_date
                if 'current_time' in st.session_state:
                    del st.session_state.current_time
                st.rerun()

with col_cancel:
    if st.session_state.edit_mode:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_item = None
            
            # 취소 시에도 초기화하고 싶다면 del
            if 'current_date' in st.session_state:
                del st.session_state.current_date
            if 'current_time' in st.session_state:
                del st.session_state.current_time
            st.rerun()

# 메인 화면 - 데이터 조회
st.header("📊 지출 내역 조회")

# 월 이동 버튼
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    if st.button("◀ 전월", use_container_width=True):
        current = st.session_state.current_date
        if current.month == 1:
            st.session_state.current_date = current.replace(year=current.year - 1, month=12)
        else:
            st.session_state.current_date = current.replace(month=current.month - 1)
        st.rerun()

with col2:
    st.markdown(
        f"<h3 style='text-align: center;'>{st.session_state.current_date.year}년 {st.session_state.current_date.month}월</h3>", 
        unsafe_allow_html=True
    )

with col3:
    if st.button("다음월 ▶", use_container_width=True):
        current = st.session_state.current_date
        if current.month == 12:
            st.session_state.current_date = current.replace(year=current.year + 1, month=1)
        else:
            st.session_state.current_date = current.replace(month=current.month + 1)
        st.rerun()

# 현재 선택된 월의 시작일과 종료일 계산
current_year = st.session_state.current_date.year
current_month = st.session_state.current_date.month

start_date = f"{current_year}-{current_month:02d}-01"
if current_month == 12:
    end_date = f"{current_year + 1}-01-01"
else:
    end_date = f"{current_year}-{current_month + 1:02d}-01"

# 데이터 처리용 변수 초기화
calendar_events = []
monthly_total = 0
daily_stats = {}

# DB 연결 및 데이터 가져오기
try:
    # 해당 월의 모든 지출 내역 가져오기 쿼리
    query = f"""
    SELECT 
        date,
        time,
        category,
        reason,
        cost,
        memo
    FROM card
    WHERE date >= '{start_date}' 
        AND date < '{end_date}'
    ORDER BY date, time
    """
    
    # handle_sql을 통해 DataFrame으로 가져옴
    df = handle_sql.get_data(query)
    
    # 데이터가 있을 경우에만 처리
    if not df.empty:
        # DataFrame을 Dict List로 변환
        results = df.to_dict('records')
        
        # 일별 지출 집계
        for row in results:
            date_val = row['date']
            if isinstance(date_val, (datetime, pd.Timestamp)):
                event_date = date_val.strftime('%Y-%m-%d')
            else:
                event_date = str(date_val)

            cost = row.get('cost', 0) or 0
            
            if event_date not in daily_stats:
                daily_stats[event_date] = {
                    'total': 0,
                    'items': []
                }
            
            daily_stats[event_date]['total'] += cost
            
            # time 처리 (Pandas timedelta 혹은 문자열)
            time_value = row.get('time', '')
            time_str = ''
            original_time_db = ''  # 데이터베이스 원본 시간 값 (UPDATE용)
            
            if time_value is not None:
                # Pandas Timedelta 혹은 datetime.timedelta 인 경우
                if hasattr(time_value, 'total_seconds'):
                    total_seconds = int(time_value.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                    original_time_db = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    time_str = str(time_value)
                    # 문자열인 경우 형식 정규화 (HH:MM 또는 HH:MM:SS)
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
                'cost': cost,
                'time': time_str,
                'memo': row.get('memo', ''),
                'original_date': event_date,
                'original_time': original_time_db  # 데이터베이스 형식으로 저장
            })
            
            monthly_total += cost
    
    # 캘린더 이벤트 생성 (일별 합계)
    for date, stats in daily_stats.items():
        event = {
            "title": f"{stats['total']:,}원",
            "start": date,
            "allDay": True,
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "textColor": "#dc3545",
            "extendedProps": {
                "daily_total": stats['total'],
                "items": stats['items']
            }
        }
        calendar_events.append(event)
    
except Exception as e:
    st.error(f"❌ 데이터 조회 오류: {e}")

# CSS 스타일
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
    }
    .fc-event-title {
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# 월별 통계 표시
st.markdown("---")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("💰 월 총 지출", f"{monthly_total:,}원")
with col_b:
    st.metric("📅 지출 일수", f"{len(daily_stats)}일")
with col_c:
    avg_daily = monthly_total / len(daily_stats) if len(daily_stats) > 0 else 0
    st.metric("📊 일평균 지출", f"{avg_daily:,.0f}원")

st.markdown("---")

# 캘린더 옵션 설정
calendar_options = {
    "editable": False,
    "selectable": True,
    "headerToolbar": {
        "left": "",
        "center": "",
        "right": "",
    },
    "initialView": "dayGridMonth",
    "initialDate": f"{current_year}-{current_month:02d}-01",
    "locale": "ko",
    "height": 600,
}

# 캘린더 렌더링
state = calendar(
    events=calendar_events, 
    options=calendar_options, 
    key=f"calendar_{current_year}_{current_month}"
)

# 날짜 클릭 시 선택된 날짜 업데이트
if state and state.get('dateClick'):
    # state['dateClick']['date']는 "2024-05-17T00:00:00.000Z" 형태일 수 있음
    clicked_raw = state['dateClick']['date']
    
    try:
        # T를 기준으로 잘라서 날짜만 가져오거나, 9시간을 더해줍니다.
        if 'T' in clicked_raw:
            # ISO 형식일 경우 파싱 후 9시간 더하기
            dt_obj = datetime.fromisoformat(clicked_raw.replace('Z', '+00:00'))
            kst_date = (dt_obj + timedelta(hours=9)).date()
            st.session_state.selected_date = kst_date
        else:
            # 단순 문자열일 경우
            st.session_state.selected_date = datetime.strptime(clicked_raw[:10], '%Y-%m-%d').date()
    except Exception as e:
        st.error(f"날짜 선택 오류: {e}")

# --- 캘린더 이벤트 클릭 시 선택된 날짜 업데이트 (시차 보정) ---
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

# 선택된 날짜의 지출 내역 표시 (디폴트: 오늘 날짜)
selected_date_str = st.session_state.selected_date.strftime('%Y-%m-%d')

if selected_date_str in daily_stats:
    st.markdown("---")
    st.subheader(f"📅 {selected_date_str} 지출 내역")
    
    stats = daily_stats[selected_date_str]
    st.write(f"**일 총 지출: {stats['total']:,}원**")
    
    # 각 항목을 카드 형태로 표시하고 수정 버튼 추가
    for idx, item in enumerate(stats['items']):
        with st.container():
            col_info, col_btn = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"""
                <div style="
                    padding: 10px;
                    margin: 5px 0;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                ">
                    <strong>{item['time'] or '-'}</strong> | 
                    <strong>{item['category'] or '-'}</strong> - {item['reason'] or '-'} | 
                    <strong style="color: #dc3545;">{item['cost']:,}원</strong>
                    {f'<br><small style="color: #666;">메모: {item["memo"] or "-"}</small>' if item.get('memo') else ''}
                </div>
                """, unsafe_allow_html=True)
            
            with col_btn:
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                if st.button("✏️ 수정", key=f"edit_{selected_date_str}_{idx}", use_container_width=True):
                    st.session_state.edit_mode = True
                    st.session_state.edit_item = item
                    st.rerun()
            
            st.markdown("---")
    
    # 테이블 형태로도 표시 (참고용)
    detail_data = []
    for item in stats['items']:
        detail_data.append({
            '시간': item['time'] or '-',
            '카테고리': item['category'] or '-',
            '내용': item['reason'] or '-',
            '금액': f"{item['cost']:,}원",
            '메모': item['memo'] or '-'
        })
    
    with st.expander("📋 테이블 보기"):
        df_detail = pd.DataFrame(detail_data)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)
        
elif selected_date_str:
    st.markdown("---")
    st.info(f"📆 {selected_date_str}에는 지출 내역이 없습니다.")