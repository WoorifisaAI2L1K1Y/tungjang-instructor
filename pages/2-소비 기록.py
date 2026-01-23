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

# 세션 스테이트 초기화
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

# 선택된 날짜 초기화 (디폴트: 오늘)
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.now().date()

# 수정 모드 및 수정할 항목 정보
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_item' not in st.session_state:
    st.session_state.edit_item = None

# 사이드바 헤더 (수정 모드에 따라 변경)
if st.session_state.edit_mode:
    st.sidebar.header("✏️ 지출 내역 수정")
else:
    st.sidebar.header("📝 지출 내역 입력")

# 수정 모드인 경우 원본 데이터 표시
if st.session_state.edit_mode and st.session_state.edit_item:
    st.sidebar.info(f"**수정 중:** {st.session_state.edit_item.get('category', '')} - {st.session_state.edit_item.get('reason', '')}")

# 1. 날짜/시간 입력 (수정 모드일 때는 원본 값 사용, 아니면 현재 날짜/시간)
if st.session_state.edit_mode and st.session_state.edit_item:
    # 수정 모드: 원본 데이터의 날짜/시간 사용
    original_date_str = st.session_state.edit_item.get('original_date', '')
    original_time_str = st.session_state.edit_item.get('original_time', '')
    
    try:
        if original_date_str:
            edit_date = datetime.strptime(original_date_str, '%Y-%m-%d').date()
        else:
            edit_date = datetime.now().date()
    except:
        edit_date = datetime.now().date()
    
    try:
        if original_time_str:
            time_parts = original_time_str.split(':')
            edit_time = datetime.now().replace(hour=int(time_parts[0]), minute=int(time_parts[1]) if len(time_parts) > 1 else 0, second=0).time()
        else:
            edit_time = datetime.now().time()
    except:
        edit_time = datetime.now().time()
    
    date = st.sidebar.date_input("날짜", value=edit_date)
    time = st.sidebar.time_input("시간", value=edit_time)
else:
    # 입력 모드: 현재 날짜/시간을 디폴트로 사용
    date = st.sidebar.date_input("날짜", value=datetime.now().date())
    time = st.sidebar.time_input("시간", value=datetime.now().time())

# 2. 대분류 선택
if st.session_state.edit_mode and st.session_state.edit_item:
    # 수정 모드: 원본 카테고리 사용
    original_category = st.session_state.edit_item.get('category', list(CATEGORY_STRUCTURE.keys())[0])
    category = st.sidebar.selectbox(
        "카테고리 (대분류)", 
        options=list(CATEGORY_STRUCTURE.keys()),
        index=list(CATEGORY_STRUCTURE.keys()).index(original_category) if original_category in CATEGORY_STRUCTURE else 0
    )
else:
    category = st.sidebar.selectbox(
        "카테고리 (대분류)", 
        options=list(CATEGORY_STRUCTURE.keys())
    )

# 3. 중분류 선택 (선택된 대분류에 맞춰 목록 갱신)
reason_options = CATEGORY_STRUCTURE.get(category, [])
if st.session_state.edit_mode and st.session_state.edit_item:
    # 수정 모드: 원본 사유 사용
    original_reason = st.session_state.edit_item.get('reason', reason_options[0] if reason_options else '')
    if original_reason in reason_options:
        reason = st.sidebar.selectbox(
            "사유 (중분류)",
            options=reason_options,
            index=reason_options.index(original_reason)
        )
    else:
        reason = st.sidebar.selectbox(
            "사유 (중분류)",
            options=reason_options
        )
else:
    reason = st.sidebar.selectbox(
        "사유 (중분류)",
        options=reason_options
    )

# 4. 금액 및 메모
if st.session_state.edit_mode and st.session_state.edit_item:
    # 수정 모드: 원본 값 사용
    original_cost = st.session_state.edit_item.get('cost', 0)
    original_memo = st.session_state.edit_item.get('memo', '')
    cost = st.sidebar.number_input("금액 (원)", min_value=0, step=1000, value=int(original_cost))
    memo = st.sidebar.text_input("메모", value=original_memo, max_chars=50)
else:
    cost = st.sidebar.number_input("금액 (원)", min_value=0, step=1000)
    memo = st.sidebar.text_input("메모", placeholder="상세 내용을 입력하세요", max_chars=50)

# 5. 저장/수정 버튼
col_save, col_cancel = st.sidebar.columns(2)

with col_save:
    if st.session_state.edit_mode:
        if st.button("💾 수정 저장", use_container_width=True):
            if st.session_state.edit_item:
                original_date = st.session_state.edit_item.get('original_date', '')
                original_time = st.session_state.edit_item.get('original_time', '')
                original_category = st.session_state.edit_item.get('category', '')
                original_reason = st.session_state.edit_item.get('reason', '')
                
                if update_expense(
                    date.strftime("%Y-%m-%d"),
                    time.strftime("%H:%M:%S"),
                    category,
                    reason,
                    int(cost),
                    memo,
                    original_date,
                    original_time,
                    original_category,
                    original_reason
                ):
                    st.sidebar.success("✅ 수정 완료!")
                    st.session_state.edit_mode = False
                    st.session_state.edit_item = None
                    st.rerun()
    else:
        if st.button("💾 저장", use_container_width=True):
            if add_expense(
                date.strftime("%Y-%m-%d"),
                time.strftime("%H:%M:%S"),
                category,
                reason,
                int(cost),
                memo
            ):
                st.sidebar.success("✅ 저장 완료!")
                st.rerun()

with col_cancel:
    if st.session_state.edit_mode:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.edit_mode = False
            st.session_state.edit_item = None
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
    clicked_date_str = state['dateClick']['date'][:10]
    try:
        clicked_date = datetime.strptime(clicked_date_str, '%Y-%m-%d').date()
        st.session_state.selected_date = clicked_date
    except:
        pass

# 이벤트 클릭 시 선택된 날짜 업데이트
elif state and state.get('eventClick'):
    event_data = state['eventClick']['event']
    clicked_date_str = event_data.get('start', '')[:10]
    try:
        clicked_date = datetime.strptime(clicked_date_str, '%Y-%m-%d').date()
        st.session_state.selected_date = clicked_date
    except:
        pass

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