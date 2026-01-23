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

# 세션 스테이트에 현재 날짜 저장
if 'current_date' not in st.session_state:
    st.session_state.current_date = datetime.now()

# 월 이동 버튼을 캘린더 위에 배치
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
    st.markdown(f"<h3 style='text-align: center;'>{st.session_state.current_date.year}년 {st.session_state.current_date.month}월</h3>", unsafe_allow_html=True)

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

# DB 연결 및 데이터 가져오기 (handle_sql 사용)
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
    FROM sample
    WHERE date >= '{start_date}' 
        AND date < '{end_date}'
    ORDER BY date, time
    """
    
    # [변경됨] handle_sql을 통해 DataFrame으로 가져옴
    df = handle_sql.get_data(query)
    
    # 데이터가 있을 경우에만 처리
    if not df.empty:
        # 기존 로직 재사용을 위해 DataFrame을 Dict List로 변환
        # orient='records'는 [{'col1': val1, ...}, ...] 형태를 만듦
        results = df.to_dict('records')
        
        # 일별 지출 집계
        for row in results:
            # Pandas Timestamp 객체일 수 있으므로 strftime 사용
            # 혹은 문자열일 경우 그대로 사용
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
            
            if time_value is not None:
                # Pandas Timedelta 혹은 datetime.timedelta 인 경우
                if hasattr(time_value, 'total_seconds'):
                    total_seconds = int(time_value.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    time_str = f"{hours:02d}:{minutes:02d}"
                else:
                    time_str = str(time_value)

            daily_stats[event_date]['items'].append({
                'category': row.get('category', ''),
                'reason': row.get('reason', ''),
                'cost': cost,
                'time': time_str,
                'memo': row.get('memo', '')
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

# --- 이하 UI 코드는 기존과 동일 ---

# 월별 통계 표시
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

# 날짜 클릭 시 상세 내역 표시
if state and state.get('dateClick'):
    clicked_date = state['dateClick']['date'][:10]
    
    if clicked_date in daily_stats:
        st.markdown("---")
        st.subheader(f"📅 {clicked_date} 지출 내역")
        
        stats = daily_stats[clicked_date]
        st.write(f"**일 총 지출: {stats['total']:,}원**")
        
        detail_data = []
        for item in stats['items']:
            detail_data.append({
                '시간': item['time'] or '-',
                '카테고리': item['category'] or '-',
                '내용': item['reason'] or '-',
                '금액': f"{item['cost']:,}원",
                '메모': item['memo'] or '-'
            })
        
        df_detail = pd.DataFrame(detail_data)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)
    else:
        st.info(f"📆 {clicked_date}에는 지출 내역이 없습니다.")

# 이벤트 클릭 시 상세 내역 표시
elif state and state.get('eventClick'):
    event_data = state['eventClick']['event']
    clicked_date = event_data.get('start', '')[:10]
    
    if clicked_date in daily_stats:
        st.markdown("---")
        st.subheader(f"📅 {clicked_date} 지출 내역")
        
        stats = daily_stats[clicked_date]
        st.write(f"**일 총 지출: {stats['total']:,}원**")
        
        detail_data = []
        for item in stats['items']:
            detail_data.append({
                '시간': item['time'] or '-',
                '카테고리': item['category'] or '-',
                '내용': item['reason'] or '-',
                '금액': f"{item['cost']:,}원",
                '메모': item['memo'] or '-'
            })
        
        df_detail = pd.DataFrame(detail_data)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)