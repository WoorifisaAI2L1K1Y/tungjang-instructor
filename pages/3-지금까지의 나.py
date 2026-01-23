import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import sys

# --------------------------------------------------------------------------------
# 1. 초기 설정 및 모듈 경로 설정
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="📚교관의 분석📚",
    page_icon="💰",
    layout="wide"
)

# utils 폴더의 모듈을 불러오기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("utils/handle_sql.py 파일을 찾을 수 없습니다.")


# --------------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 (handle_sql 사용)
# --------------------------------------------------------------------------------
def load_and_process_data():
    try:
        # SQL 쿼리 작성
        query = """
            SELECT date, time, category, reason, cost, memo
            FROM card
            ORDER BY date DESC, time DESC
        """
        
        # [변경됨] handle_sql을 통해 DataFrame으로 직접 가져옴
        df = handle_sql.get_data(query)
        
        # 데이터가 없는 경우 빈 DataFrame 반환
        if df.empty:
            return pd.DataFrame()

        # 영문 컬럼명 -> 한글 컬럼명 변경
        # handle_sql 결과의 컬럼 순서: date, time, category, reason, cost, memo
        df.columns = ['날짜', '시간', '대분류', '소분류', '비용', '비고']

        # --- 이하 데이터 정제 로직은 기존과 동일 ---
        
        # 날짜 처리
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        df = df.dropna(subset=['날짜'])
        
        # 비용 처리
        df['비용'] = pd.to_numeric(df['비용'], errors='coerce')
        df = df.dropna(subset=['비용'])

        # 파생 변수 생성
        df['month'] = df['날짜'].dt.strftime('%Y-%m')
        
        day_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
        df['weekday_name'] = df['날짜'].dt.weekday.map(day_map)
        
        # 시간 처리 (Pandas Timedelta 또는 문자열 대응)
        if pd.api.types.is_timedelta64_dtype(df['시간']):
             df['hour'] = df['시간'].dt.components['hours']
        else:
            # 문자열이나 기타 타입일 경우 처리
            temp_time = pd.to_datetime(df['시간'].astype(str), format='%H:%M:%S', errors='coerce')
            df['hour'] = temp_time.dt.hour.fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"❌ 데이터 로드 및 처리 중 오류 발생: {e}")
        return pd.DataFrame()

# --------------------------------------------------------------------------------
# 3. 비즈니스 로직 함수 (재해석 & 포맷팅) - 기존 유지
# --------------------------------------------------------------------------------
def apply_reinterpretation(df):
    """(대분류, 소분류) 조합으로 소비 성격을 재해석"""
    df = df.copy()
    mapping_rules = {
        ("식비", "배달/야식"): "게으름",
        ("식비", "카페/간식"): "충동",
        ("식비", "술/유흥"): "충동",
        ("주거/통신", "월세/관리비"): "호흡",
        ("주거/통신", "공과금"): "호흡",
        ("주거/통신", "통신비"): "호흡",
        ("주거/통신", "구독/OTT"): "호흡",
        ("생활/쇼핑", "패션/미용"): "충동",
        ("생활/쇼핑", "가전/가구"): "충동",
        ("생활/쇼핑", "반려동물"): "호흡",
        ("교통/차량", "대중교통"): "호흡",
        ("교통/차량", "자차/주유"): "호흡",
        ("교통/차량", "택시/호출"): "게으름",
        ("건강/운동", "운동/헬스"): "성장",
        ("교육/계발", "도서/문구"): "성장",
        ("교육/계발", "강의/수강"): "성장",
        ("관계", "데이트/모임"): "충동",
        ("문화/취미", "영화/공연"): "충동",
        ("문화/취미", "여행"): "충동",
        ("금융", "보험/세금"): "호흡",
        ("금융", "저축/투자"): "성장"
    }
    
    def get_category(row):
        return mapping_rules.get((row['대분류'], row['소분류']), "중립")

    df['재해석'] = df.apply(get_category, axis=1)
    return df

def format_currency(value):
    return f"₩{int(value):,}"

# --------------------------------------------------------------------------------
# 4. 메인 화면 구성 - 기존 유지
# --------------------------------------------------------------------------------
def main():
    st.title("💰 AI 가계부: 소비 재해석 & 패턴 분석")

    # 사이드바: 데이터 새로고침 버튼
    with st.sidebar:
        st.header("데이터 관리")
        if st.button("🔄 최신 데이터 불러오기"):
            st.rerun()

    # 1. 데이터 로드 (수정된 함수 호출)
    raw_df = load_and_process_data()

    if raw_df.empty:
        st.warning("데이터가 없거나 DB 연결에 실패했습니다.")
        return

    # 2. 재해석 적용
    df = apply_reinterpretation(raw_df)

    # 3. 탭 구성
    tab1, tab2 = st.tabs(["📊 월별 리포트 (재해석)", "🔥 소비 패턴 분석"])

    # --- TAB 1: 월별 리포트 ---
    with tab1:
        st.subheader("📅 월별 소비 성격 분석")
        
        # 월 선택 필터
        all_months = sorted(df['month'].unique(), reverse=True)
        # 데이터가 있을 때만 selectbox 표시
        if len(all_months) > 0:
            selected_month = st.selectbox("분석할 월을 선택하세요", all_months)
            
            month_df = df[df['month'] == selected_month].copy()
            
            # 통계 집계
            total_cost = month_df["비용"].sum()
            cost_by_type = month_df.groupby("재해석")["비용"].sum()
            
            impulse = cost_by_type.get("충동", 0)
            lazy = cost_by_type.get("게으름", 0)
            breath = cost_by_type.get("호흡", 0)
            growth = cost_by_type.get("성장", 0)
            waste = impulse + lazy

            # KPI Metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("총 지출", format_currency(total_cost))
            col2.metric("낭비 (충동+게으름)", format_currency(waste), delta="줄여야 할 돈", delta_color="inverse")
            col3.metric("호흡 (고정비)", format_currency(breath))
            col4.metric("성장 (투자)", format_currency(growth))

            # 차트 및 데이터 테이블
            c_chart, c_table = st.columns([1, 1.5])
            
            with c_chart:
                # 파이 차트 색상 지정
                colors = {"충동":"#FF6B6B", "게으름":"#FFA07A", "호흡":"#4D96FF", "성장":"#6BCB77", "중립":"#E0E0E0"}
                fig = px.pie(
                    names=cost_by_type.index, 
                    values=cost_by_type.values,
                    title=f"{selected_month} 소비 비중",
                    hole=0.4,
                    color=cost_by_type.index,
                    color_discrete_map=colors
                )
                st.plotly_chart(fig, use_container_width=True)

            with c_table:
                st.markdown(f"**📝 {selected_month} 상세 내역**")
                display_cols = ["날짜", "대분류", "소분류", "비용", "재해석", "비고"]
                st.dataframe(
                    month_df[display_cols].sort_values("날짜", ascending=False), 
                    use_container_width=True,
                    height=400
                )
        else:
            st.info("데이터가 충분하지 않습니다.")

    # --- TAB 2: 패턴 분석 ---
    with tab2:
        st.subheader("🔍 소비 행동 패턴 분석")
        
        col_left, col_right = st.columns(2)

        # [좌측] 상관관계 분석
        with col_left:
            st.markdown("#### 📉 낭비 지출이 총지출에 미치는 영향")
            # 월별 데이터 집계
            monthly_agg = df.groupby("month").apply(
                lambda x: pd.Series({
                    "total": x["비용"].sum(),
                    "waste": x[x["재해석"].isin(["충동", "게으름"])]["비용"].sum()
                })
            ).reset_index()

            if len(monthly_agg) > 1:
                fig_scatter = px.scatter(
                    monthly_agg, x="waste", y="total", text="month",
                    labels={"waste": "낭비성 지출 (충동+게으름)", "total": "총 지출"},
                    title="월별 낭비 지출 vs 총 지출 상관관계"
                )
                # 추세선 추가
                z = np.polyfit(monthly_agg["waste"], monthly_agg["total"], 1)
                p = np.poly1d(z)
                x_range = np.linspace(monthly_agg["waste"].min(), monthly_agg["waste"].max(), 100)
                fig_scatter.add_trace(go.Scatter(x=x_range, y=p(x_range), mode='lines', name='추세선', line=dict(dash='dot', color='red')))
                
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("데이터가 2개월 이상 쌓여야 추세 분석이 가능합니다.")

        # [우측] 히트맵 분석
        with col_right:
            st.markdown("#### 🔥 언제 돈을 많이 쓸까?")
            target_type = st.radio("분석할 유형 선택", ["충동", "게으름", "호흡", "성장", "전체"], horizontal=True)
            
            # 필터링
            target_df = df if target_type == "전체" else df[df["재해석"] == target_type]

            if not target_df.empty:
                # 요일/시간별 집계
                heatmap_data = target_df.groupby(["weekday_name", "hour"])["비용"].sum().reset_index()
                
                # 피벗 테이블 (행: 요일, 열: 시간)
                week_order = ["월", "화", "수", "목", "금", "토", "일"]
                # 관측되지 않은 요일이나 시간대도 0으로 채우기 위해 로직 보완
                pivot_table = heatmap_data.pivot_table(
                    index="weekday_name", columns="hour", values="비용", fill_value=0
                ).reindex(week_order)

                # 히트맵 시각화
                fig_heatmap = px.imshow(
                    pivot_table,
                    labels=dict(x="시간(시)", y="요일", color="지출액"),
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    aspect="auto",
                    color_continuous_scale="Reds"
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Top 3 지출 항목
                st.markdown(f"**🏆 [{target_type}] 지출 금액 Top 3**")
                top3 = target_df.nlargest(3, "비용")[["날짜", "대분류", "소분류", "비용", "비고"]]
                top3["비용"] = top3["비용"].apply(format_currency)
                st.table(top3)
            else:
                st.warning(f"선택하신 '{target_type}' 유형의 지출 내역이 없습니다.")

if __name__ == "__main__":
    main()