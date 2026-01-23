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
    # 로컬 테스트 등을 위해 파일이 없을 경우를 대비한 더미 처리 (실제 환경에선 무시됨)
    pass


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
        
        # handle_sql을 통해 DataFrame으로 직접 가져옴
        if 'utils.handle_sql' in sys.modules:
            df = handle_sql.get_data(query)
        else:
            # handle_sql이 없는 경우(테스트용) 빈 데이터프레임
            return pd.DataFrame()
        
        # 데이터가 없는 경우 빈 DataFrame 반환
        if df.empty:
            return pd.DataFrame()

        # 영문 컬럼명 -> 한글 컬럼명 변경
        df.columns = ['날짜', '시간', '대분류', '소분류', '비용', '비고']

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
        
        # 시간 처리
        if pd.api.types.is_timedelta64_dtype(df['시간']):
             df['hour'] = df['시간'].dt.components['hours']
        else:
            temp_time = pd.to_datetime(df['시간'].astype(str), format='%H:%M:%S', errors='coerce')
            df['hour'] = temp_time.dt.hour.fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"❌ 데이터 로드 및 처리 중 오류 발생: {e}")
        return pd.DataFrame()

# --------------------------------------------------------------------------------
# 3. 비즈니스 로직 함수 (재해석 & 포맷팅)
# --------------------------------------------------------------------------------
def apply_reinterpretation(df):
    """(대분류, 소분류) 조합으로 지출 성격을 재해석"""
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
# 4. 메인 화면 구성
# --------------------------------------------------------------------------------
def main():
    st.title("💰지출 재해석 및 패턴 분석을 실시하겠다.") 

    with st.sidebar:
        st.header("데이터 관리")
        if st.button("🔄 데이터 강제 동기화"):
            st.cache_data.clear() # 혹시 모를 캐시 삭제
            st.rerun()

    # 1. 데이터 로드 (페이지 열릴 때마다 무조건 실행됨)
    raw_df = load_and_process_data()

    if raw_df.empty:
        st.warning("데이터가 없거나 DB 연결에 실패했다. utils/handle_sql 설정을 확인해보아라.")
        return

    # 2. 재해석 적용
    df = apply_reinterpretation(raw_df)

    # 3. 탭 구성
    tab1, tab2 = st.tabs(["📊 월별 리포트 (재해석)", "🔥 지출 패턴 분석"]) # [수정] 용어 통일

    # --- TAB 1: 월별 리포트 ---
    with tab1:
        st.subheader("📅 월별 지출 성격 분석이다.") # [수정] 용어 통일
        
        all_months = sorted(df['month'].unique(), reverse=True)
        selected_month = st.selectbox("분석할 월을 선택하라.", all_months)
        
        month_df = df[df['month'] == selected_month].copy()
        
        # 통계 집계
        total_cost = month_df["비용"].sum()
        cost_by_type = month_df.groupby("재해석")["비용"].sum()
        
        impulse = cost_by_type.get("충동", 0)
        lazy = cost_by_type.get("게으름", 0)
        breath = cost_by_type.get("호흡", 0)
        growth = cost_by_type.get("성장", 0)
        waste = impulse + lazy

        # 비중(%) 계산
        if total_cost > 0:
            waste_pct = (waste / total_cost) * 100
            breath_pct = (breath / total_cost) * 100
            growth_pct = (growth / total_cost) * 100
        else:
            waste_pct = breath_pct = growth_pct = 0

        # KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        common_style = """
        <div style="display: flex; flex-direction: column;">
            <span style="font-size: 14px; color: #555; margin-bottom: 5px;">{}</span>
            <span style="font-size: 32px; font-weight: bold; line-height: 1.2;">{}</span>
            <div style="margin-top: 5px;">{}</div>
        </div>
        """
        
        with col1:
            st.markdown(common_style.format(
                "총 지출",
                format_currency(total_cost),
                "<span style='color: transparent; font-size: 14px;'>-</span>"
            ), unsafe_allow_html=True)
        
        with col2:
            waste_badge = f"""
            <span style="background-color: #ffeaea; color: #df4759; padding: 4px 8px; border-radius: 4px; font-size: 14px; font-weight: 500;">
                줄여야 할 돈 ({waste_pct:.1f}%)
            </span>
            """
            st.markdown(common_style.format(
                "낭비 (충동+게으름)",
                format_currency(waste),
                waste_badge
            ), unsafe_allow_html=True)
        
        with col3:
            breath_text = f"""
            <span style="color: #888; font-size: 14px;">
                {breath_pct:.1f}%
            </span>
            """
            st.markdown(common_style.format(
                "호흡 (고정비)",
                format_currency(breath),
                breath_text
            ), unsafe_allow_html=True)
        
        with col4:
            growth_text = f"""
            <span style="color: #888; font-size: 14px;">
                {growth_pct:.1f}%
            </span>
            """
            st.markdown(common_style.format(
                "성장 (투자)",
                format_currency(growth),
                growth_text
            ), unsafe_allow_html=True)

        # 차트 및 데이터 테이블
        c_chart, c_table = st.columns([1, 1.5])
        
        with c_chart:
            colors = {"충동":"#FF6B6B", "게으름":"#FFA07A", "호흡":"#4D96FF", "성장":"#6BCB77", "중립":"#E0E0E0"}
            if not cost_by_type.empty:
                fig = px.pie(
                    names=cost_by_type.index, 
                    values=cost_by_type.values,
                    title=f"{selected_month} 지출 비중", # [수정] 용어 통일
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
                height=400,
                hide_index=True
            )

    # --- TAB 2: 패턴 분석 ---
    with tab2:
        st.subheader("🔍 지출 행동 패턴 분석이다!") # [수정] 용어 통일
        
        col_left, col_right = st.columns(2)

# [좌측] 상관관계 분석
        with col_left:
            st.markdown("##### 📉 너의 낭비가 총 지출에 미치는 영향을 보여주겠다.")
            
            # 1. 데이터 집계
            monthly_agg = df.groupby("month").apply(
                lambda x: pd.Series({
                    "total": x["비용"].sum(),
                    "waste": x[x["재해석"].isin(["충동", "나태"])]["비용"].sum()
                })
            ).reset_index()

            if len(monthly_agg) > 1:
                # 2. 상관계수 계산
                corr_value = monthly_agg['waste'].corr(monthly_agg['total'])
                
                # 3. 산점도 시각화
                fig_scatter = px.scatter(
                    monthly_agg, x="waste", y="total", text="month",
                    labels={"waste": "낭비 (충동+나태)", "total": "총 지출"},
                    title="낭비 vs 총 지출 상관관계"
                )
                try:
                    z = np.polyfit(monthly_agg["waste"], monthly_agg["total"], 1)
                    p = np.poly1d(z)
                    x_range = np.linspace(monthly_agg["waste"].min(), monthly_agg["waste"].max(), 100)
                    fig_scatter.add_trace(go.Scatter(x=x_range, y=p(x_range), mode='lines', name='추세선', line=dict(dash='dot', color='red')))
                except Exception:
                    pass
                
                st.plotly_chart(fig_scatter, use_container_width=True)
                
                # ----------------------------------------------------------------
                # [수정] 교관의 정밀 타격 (한마디) 섹션
                # ----------------------------------------------------------------
                st.markdown("---")
                st.markdown("#### 📢 교관이 정밀 타격을 실시하겠다.")

                # 경로 설정 (pages 폴더 밖으로 나가서 images 폴더 찾기)
                script_dir = os.path.dirname(os.path.abspath(__file__)) 
                root_dir = os.path.dirname(script_dir)                  
                img_dir = os.path.join(root_dir, 'images')              

                # 4. 상관계수에 따른 이미지 및 멘트 선정
                # [수정] Bold 제거, 색상만 적용
                val_html = f"<span style='color: #d63384; font-size: 1.1em;'>{corr_value:.2f}</span>"

                if corr_value >= 0.7:
                    img_path = os.path.join(img_dir, '4-화남.png')
                    bg_color = "#ffeaea" 
                    # 강조: 빨간색 (#e03131)
                    status_text = f"낭비가 총 지출을 <span style='color: #e03131;'>직접적으로 폭발시키는</span> 상관계수 {val_html}이다!<br>정신이 있는 건가?! 당장 충동을 억제하고 실시! 😡"
                elif corr_value >= 0.3:
                    img_path = os.path.join(img_dir, '3-짜증.png')
                    bg_color = "#fff3cd"
                    # 강조: 주황색 (#e8590c)
                    status_text = f"낭비가 늘면 지출도 <span style='color: #e8590c;'>따라서 증가하는</span> 상관계수 {val_html}다!<br>경고한다! 전력 누수가 심각하다. 정신 차려라! 😠"
                elif corr_value > -0.3:
                    img_path = os.path.join(img_dir, '1-온화.png')
                    bg_color = "#d4edda"
                    # 강조: 초록색 (#2b8a3e)
                    status_text = f"낭비와 지출이 <span style='color: #2b8a3e;'>서로 영향이 없는</span> 상관계수 {val_html}.<br>보고! 특이사항 없음. 생명 유지비(고정비)를 점검하라. 🤔"
                else:
                    img_path = os.path.join(img_dir, '2-걱정.png')
                    bg_color = "#e2e3e5"
                    # 강조: 보라색 (#5f3dc4)
                    status_text = f"낭비를 줄였는데 지출이 늘어나는 <span style='color: #5f3dc4;'>역방향</span> 상관계수 {val_html} 감지!<br>비상! 기현상이다. 정밀 타격이 필요하다! 😨"

                # 5. 레이아웃 구성
                col_img, col_bubble = st.columns([1, 2.5])

                # [좌측] 교관 이미지
                with col_img:
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.error(f"이미지 경로 확인 필요: {img_path}")
                        st.write("🪖") 

                # [우측] 말풍선 메시지
                with col_bubble:
                    bubble_style = f"""
                    <style>
                    .speech-bubble {{
                        position: relative;
                        background: {bg_color};
                        border-radius: 12px;
                        padding: 15px 20px;
                        color: #333;
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
                        margin-left: 10px;
                        display: flex;
                        align-items: center;
                        min-height: 80px;
                        border: 2px solid rgba(0,0,0,0.05);
                    }}
                    .speech-bubble:after {{
                        content: '';
                        position: absolute;
                        left: 0;
                        top: 50%;
                        width: 0;
                        height: 0;
                        border: 12px solid transparent;
                        border-right-color: {bg_color};
                        border-left: 0;
                        margin-top: -12px;
                        margin-left: -12px;
                    }}
                    .bubble-text {{
                        font-size: 16px;
                        font-weight: bold; /* 전체 텍스트 기본 굵기 */
                        line-height: 1.5;
                        margin: 0;
                        font-family: 'Malgun Gothic', sans-serif;
                    }}
                    </style>
                    """
                    st.markdown(bubble_style, unsafe_allow_html=True)
                    # HTML이 적용된 status_text를 출력
                    st.markdown(f'<div class="speech-bubble"><p class="bubble-text">{status_text}</p></div>', unsafe_allow_html=True)

            else:
                st.info("🪖 훈련 데이터 부족! 최소 2개월 이상의 작전 기록이 필요하다.")




        # [우측] 히트맵 분석 (다중 선택)
        with col_right:
            st.markdown("##### 🔥 언제 지출이 가장 많은지 보여주겠다.") # [수정] 문구 자연스럽게 변경
            
            filter_options = ["충동", "게으름", "호흡", "성장"]
            selected_types = st.multiselect(
                "분석할 유형 선택하라. (복수 선택도 가능하다.)", 
                options=filter_options, 
                default=filter_options
            )
            
            if selected_types:
                target_df = df[df["재해석"].isin(selected_types)]
            else:
                target_df = pd.DataFrame()
                st.warning("분석할 유형을 하나 이상 선택하여라.")

            if not target_df.empty:
                heatmap_data = target_df.groupby(["weekday_name", "hour"])["비용"].sum().reset_index()
                
                week_order = ["월", "화", "수", "목", "금", "토", "일"]
                pivot_table = heatmap_data.pivot_table(
                    index="weekday_name", columns="hour", values="비용", fill_value=0
                ).reindex(week_order)

                fig_heatmap = px.imshow(
                    pivot_table,
                    labels=dict(x="시간(시)", y="요일", color="지출액"),
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    aspect="auto",
                    color_continuous_scale="Reds",
                    title=f"선택된 유형({', '.join(selected_types)}) 합산 히트맵"
                )
                fig_heatmap.update_xaxes(range=[-0.5, 23.5], tickmode='linear', dtick=2)
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # [수정] 순위 Table (인덱스 1부터 시작)
                st.markdown(f"**🏆 선택 항목 합산 지출 Top 3**")
                
                top3 = target_df.nlargest(3, "비용")[["날짜", "대분류", "소분류", "비용", "비고"]]
                top3["비용"] = top3["비용"].apply(format_currency)
                
                # 인덱스 리셋 후 1부터 시작하도록 조정
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                
                st.table(top3)
            
            elif selected_types:
                st.warning(f"선택한 유형에 해당하는 지출 내역이 없다.")

if __name__ == "__main__":
    main()