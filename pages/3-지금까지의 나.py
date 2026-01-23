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

st.set_page_config(page_title="텅장 훈련소", page_icon="💸🪖", layout="wide")

# 페이지 전체 배경색 설정 (메인 페이지와 일관성 유지)
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

# utils 폴더의 모듈을 불러오기 위한 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
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
# 4. 메인 화면 구성
# --------------------------------------------------------------------------------
def main():
    # 헤더 영역
    st.markdown("""
    <div style="text-align: center; padding: 20px 0; margin-bottom: 30px;">
        <h1 style="color: #1f1f1f; font-size: 36px; font-weight: 700; margin: 0;">
            💰 지금까지의 나
        </h1>
        <p style="color: #666; font-size: 16px; margin-top: 10px;">
            소비 재해석 및 패턴 분석 리포트
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ 데이터 관리")
        if st.button("🔄 데이터 강제 동기화", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        st.markdown("""
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 8px; font-size: 13px; color: #666;">
            <strong>💡 팁</strong><br>
            데이터가 업데이트되지 않으면<br>
            동기화 버튼을 눌러주세요.
        </div>
        """, unsafe_allow_html=True)

    # 1. 데이터 로드
    raw_df = load_and_process_data()

    if raw_df.empty:
        st.warning("⚠️ 데이터가 없거나 DB 연결에 실패했습니다. utils/handle_sql 설정을 확인해주세요.")
        return

    # 2. 재해석 적용
    df = apply_reinterpretation(raw_df)

    # 3. 탭 구성
    tab1, tab2 = st.tabs(["📊 월별 리포트", "🔥 소비 패턴 분석"]) 

    # --- TAB 1: 월별 리포트 ---
    with tab1:
        st.markdown('<div class="section-header">📅 월별 소비 성격 분석</div>', unsafe_allow_html=True)
        
        # 월 선택
        all_months = sorted(df['month'].unique(), reverse=True)
        col_select, col_info = st.columns([2, 3])
        with col_select:
            selected_month = st.selectbox(
                "📆 분석할 월을 선택하세요", 
                all_months,
                help="분석하고 싶은 월을 선택하면 해당 월의 상세 리포트를 확인할 수 있습니다."
            )
        
        # [중요] 선택된 월 데이터만 필터링
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

        # KPI Metrics - 카드 스타일로 개선
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        
        def create_metric_card(title, value, badge_text="", badge_color="#888", value_color="#1f1f1f"):
            # 배지가 없는 경우 빈 공간 추가하여 높이 통일
            badge_html = f'<div style="margin-top: 8px;"><span style="background-color: {badge_color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">{badge_text}</span></div>' if badge_text else '<div style="margin-top: 8px; height: 24px;"></div>'
            return f"""
            <div class="metric-card" style="height: 160px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="font-size: 13px; color: #666; margin-bottom: 8px; font-weight: 500;">
                        {title}
                    </div>
                    <div style="font-size: 28px; font-weight: 700; color: {value_color}; margin-bottom: 8px;">
                        {value}
                    </div>
                </div>
                {badge_html}
            </div>
            """
        
        with col1:
            st.markdown(create_metric_card(
                "총 소비",
                format_currency(total_cost),
                value_color="#1f1f1f"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(create_metric_card(
                "낭비 (충동+게으름)",
                format_currency(waste),
                f"줄여야 할 돈 ({waste_pct:.1f}%)",
                "#dc3545"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(create_metric_card(
                "호흡 (고정비)",
                format_currency(breath),
                f"{breath_pct:.1f}%",
                "#4D96FF"
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown(create_metric_card(
                "성장 (투자)",
                format_currency(growth),
                f"{growth_pct:.1f}%",
                "#6BCB77"
            ), unsafe_allow_html=True)

        # 차트 영역
        st.markdown("<br>", unsafe_allow_html=True)
        col_pie, col_def_table = st.columns([1.2, 1])
        
        # [좌측] 소비 성격 비중 (파이차트)
        with col_pie:
            st.markdown(f"### 🎨 {selected_month} 소비 성격 비중")
            
            colors = {"충동":"#FF6B6B", "게으름":"#FFA07A", "호흡":"#4D96FF", "성장":"#6BCB77", "중립":"#E0E0E0"}
            
            if not cost_by_type.empty:
                fig_pie = px.pie(
                    names=cost_by_type.index, 
                    values=cost_by_type.values,
                    hole=0.5,
                    color=cost_by_type.index,
                    color_discrete_map=colors
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>금액: %{value:,.0f}원<br>비율: %{percent}<extra></extra>'
                )
                fig_pie.update_layout(
                    height=450, 
                    margin=dict(t=20, b=20, l=20, r=20),
                    font=dict(size=14),
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("📊 데이터가 없습니다.")

        # [우측] 소비 유형 정의 표
        with col_def_table:
            st.markdown("### 📋 소비 유형 정의")
            st.markdown("##### 교관이 정한 기준이니 숙지하도록!")
            
            # 개선된 테이블 스타일
            st.markdown("""
            <div style="background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                        <th style="padding: 10px; text-align: left; font-weight: 600;">유형</th>
                        <th style="padding: 10px; text-align: left; font-weight: 600;">정의</th>
                        <th style="padding: 10px; text-align: center; font-weight: 600;">판정</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 10px; font-weight: 600; color: #FF6B6B;">게으름</td>
                        <td style="padding: 10px;">편리함에 굴복한 비용</td>
                        <td style="padding: 10px; text-align: center;"><span style="color: #dc3545; font-weight: 600;">🔴 낭비</span></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 10px; font-weight: 600; color: #FFA07A;">충동</td>
                        <td style="padding: 10px;">계획 없는 감정 소비</td>
                        <td style="padding: 10px; text-align: center;"><span style="color: #dc3545; font-weight: 600;">🔴 낭비</span></td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e9ecef;">
                        <td style="padding: 10px; font-weight: 600; color: #4D96FF;">호흡</td>
                        <td style="padding: 10px;">생활 유지 필수 비용</td>
                        <td style="padding: 10px; text-align: center;"><span style="color: #0066cc; font-weight: 600;">🔵 필수</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: 600; color: #6BCB77;">성장</td>
                        <td style="padding: 10px;">미래를 위한 투자</td>
                        <td style="padding: 10px; text-align: center;"><span style="color: #28a745; font-weight: 600;">🟢 투자</span></td>
                    </tr>
                </tbody>
            </table>
            </div>
            """, unsafe_allow_html=True)

        # 하단 영역: 상세 내역 & Top 5 차트
        st.markdown("<br>", unsafe_allow_html=True)
        col_list, col_bar = st.columns([2.2, 1])

        # [좌측 하단] 상세 내역 테이블
        with col_list:
            st.markdown(f"### 📝 {selected_month} 상세 내역")
            display_cols = ["날짜", "대분류", "소분류", "비용", "재해석", "비고"]
            
            # 데이터프레임 스타일링
            display_df = month_df[display_cols].sort_values("날짜", ascending=False).copy()
            display_df['날짜'] = display_df['날짜'].dt.strftime('%Y-%m-%d')
            display_df['비용'] = display_df['비용'].apply(lambda x: f"₩{int(x):,}")
            
            # 재해석에 따른 색상 적용
            def color_reinterpretation(val):
                colors_map = {
                    '게으름': '#FFA07A',
                    '충동': '#FF6B6B',
                    '호흡': '#4D96FF',
                    '성장': '#6BCB77',
                    '중립': '#E0E0E0'
                }
                color = colors_map.get(val, '#E0E0E0')
                return f'background-color: {color}; color: white; font-weight: 600;'
            
            styled_df = display_df.style.applymap(
                color_reinterpretation, 
                subset=['재해석']
            )
            
            st.dataframe(
                styled_df,
                use_container_width=True, 
                height=450,
                hide_index=True
            )

        # [우측 하단] 소비 상위 Top 5 (바차트)
        with col_bar:
            st.markdown(f"### 💸 {selected_month} 소비 상위 Top 5")
            
            if not month_df.empty:
                category_ratio = (
                    month_df.groupby("대분류")["비용"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                )
                
                fig_bar = px.bar(
                    x=category_ratio.values, 
                    y=category_ratio.index,
                    orientation='h',
                    text=[f"₩{int(x):,}" for x in category_ratio.values],
                    labels={'x': '비용', 'y': '카테고리'},
                    color=category_ratio.values,
                    color_continuous_scale='Blues'
                )
                
                fig_bar.update_layout(
                    height=450, 
                    margin=dict(t=20, b=20, l=10, r=10),
                    xaxis_tickformat=',',
                    showlegend=False,
                    yaxis={'categoryorder':'total ascending'}
                )
                fig_bar.update_traces(
                    textposition='outside',
                    textfont=dict(size=11, color='#333')
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("📊 데이터가 없습니다.")

    # --- TAB 2: 패턴 분석 ---
    with tab2:
        st.markdown('<div class="section-header">🔍 소비 행동 패턴 분석</div>', unsafe_allow_html=True)
        
        col_upper_left, col_upper_right = st.columns(2)

        # 1. 상단 좌측: 텍스트 및 상태 말풍선
        with col_upper_left:
            st.markdown("""
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 20px;">
                <h4 style="color: #856404; margin: 0 0 10px 0;">⚠️ 낭비는 게으름과 충동 구매의 결과</h4>
                <p style="color: #856404; margin: 0; font-size: 14px;">아래는 낭비가 총 소비에 미치는 영향 분석입니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 상관계수 계산
            monthly_agg = df.groupby("month").apply(
                lambda x: pd.Series({
                    "total": x["비용"].sum(),
                    "waste": x[x["재해석"].isin(["충동", "게으름"])]["비용"].sum() 
                })
            ).reset_index()

            corr_value = 0 
            if len(monthly_agg) > 1:
                corr_value = monthly_agg['waste'].corr(monthly_agg['total'])

            # 이미지 경로 및 상태 텍스트 설정
            script_dir = os.path.dirname(os.path.abspath(__file__)) 
            root_dir = os.path.dirname(script_dir)                  
            img_dir = os.path.join(root_dir, 'images')              

            val_html = f"<span style='color: #d63384; font-size: 1.2em; font-weight: 700;'>{corr_value:.2f}</span>"
            
            # 기본값
            img_path = os.path.join(img_dir, '0-궁금.png')
            bg_color = "#f8f9fa"
            status_text = "데이터가 부족합니다."

            if len(monthly_agg) > 1:
                if corr_value >= 0.7:
                    img_path = os.path.join(img_dir, '4-화남.png')
                    bg_color = "#ffeaea" 
                    status_text = f"낭비가 총 소비를 <span style='color: #e03131; font-weight: 700;'>직접적으로 폭발시키는</span> 상관계수가 {val_html}입니다!<br>정신 차리세요! 당장 충동을 억제하세요! 😡"
                elif corr_value >= 0.3:
                    img_path = os.path.join(img_dir, '3-짜증.png')
                    bg_color = "#fff3cd"
                    status_text = f"낭비가 늘면 소비도 <span style='color: #e8590c; font-weight: 700;'>따라서 증가하는</span> 상관계수가 {val_html}입니다!<br>경고합니다! 낭비가 심각합니다. 정신 차리세요! 😠"
                elif corr_value > -0.3:
                    img_path = os.path.join(img_dir, '1-온화.png')
                    bg_color = "#d4edda"
                    status_text = f"낭비와 소비가 <span style='color: #2b8a3e; font-weight: 700;'>서로 영향이 없는</span> 상관계수가 {val_html}입니다.<br>보고! 특이사항 없음. 생명 유지비(고정비)를 점검하세요. 🤔"
                else:
                    img_path = os.path.join(img_dir, '2-걱정.png')
                    bg_color = "#e2e3e5"
                    status_text = f"낭비를 줄였는데 소비가 늘어나는 <span style='color: #5f3dc4; font-weight: 700;'>역방향</span> 상관계수가 {val_html} 감지!<br>비상! 기현상입니다. 정밀 분석이 필요합니다! 😨"

            # 말풍선 렌더링
            c_img, c_bubble = st.columns([1, 2.5])
            with c_img:
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.write("🪖")
            
            with c_bubble:
                bubble_style = f"""
                <style>
                .speech-bubble {{
                    position: relative; background: {bg_color}; border-radius: 12px; padding: 18px 22px;
                    color: #333; box-shadow: 2px 2px 8px rgba(0,0,0,0.15); margin-left: 10px;
                    display: flex; align-items: center; min-height: 90px; border: 2px solid rgba(0,0,0,0.08);
                }}
                .speech-bubble:after {{
                    content: ''; position: absolute; left: 0; top: 50%; width: 0; height: 0;
                    border: 14px solid transparent; border-right-color: {bg_color}; border-left: 0;
                    margin-top: -14px; margin-left: -14px;
                }}
                .bubble-text {{ font-size: 15px; font-weight: 600; line-height: 1.6; margin: 0; font-family: 'Malgun Gothic', sans-serif; }}
                </style>
                """
                st.markdown(bubble_style, unsafe_allow_html=True)
                st.markdown(f'<div class="speech-bubble"><p class="bubble-text">{status_text}</p></div>', unsafe_allow_html=True)

        # 2. 상단 우측: 가이드 말풍선
        with col_upper_right:
            st.markdown("""
            <div style="background-color: #e7f5ff; padding: 15px; border-radius: 8px; border-left: 4px solid #1c7ed6; margin-bottom: 20px;">
                <h4 style="color: #0b7285; margin: 0 0 10px 0;">🔥 언제 소비가 가장 많은지 확인하세요</h4>
                <p style="color: #0b7285; margin: 0; font-size: 14px;">히트맵으로 시간대별 소비 패턴을 분석합니다.</p>
            </div>
            """, unsafe_allow_html=True)
            
            img_path_guide = os.path.join(img_dir, '5-교관의_한마디.png')
            bubble_bg_color = "#e7f5ff"
            guide_text = "💡 <span style='color: #0b7285; font-weight: 700;'>히트맵 판별법</span>: 가로축은 <span style='color: #1c7ed6; font-weight: 600;'>시간</span>, 세로축은 <span style='color: #1c7ed6; font-weight: 600;'>요일</span>입니다.<br>색이 <span style='color: #e03131; font-weight: 700;'>붉을수록</span> 해당 시간대에 소비가 극심합니다!"

            c_bubble_r, c_img_r = st.columns([2.5, 1])
            
            with c_bubble_r:
                guide_style = f"""
                <style>
                .guide-bubble {{
                    position: relative; background: {bubble_bg_color}; border-radius: 12px; padding: 18px 22px;
                    color: #333; box-shadow: 2px 2px 8px rgba(0,0,0,0.15); margin-right: 10px;
                    display: flex; align-items: center; min-height: 90px; border: 2px solid rgba(0,0,0,0.08);
                }}
                .guide-bubble:after {{
                    content: ''; position: absolute; right: 0; top: 50%; width: 0; height: 0;
                    border: 14px solid transparent; border-left-color: {bubble_bg_color}; border-right: 0;
                    margin-top: -14px; margin-right: -14px;
                }}
                .guide-text {{ font-size: 15px; font-weight: 600; line-height: 1.6; margin: 0; font-family: 'Malgun Gothic', sans-serif; }}
                </style>
                """
                st.markdown(guide_style, unsafe_allow_html=True)
                st.markdown(f'<div class="guide-bubble"><p class="guide-text">{guide_text}</p></div>', unsafe_allow_html=True)

            with c_img_r:
                if os.path.exists(img_path_guide):
                    st.image(img_path_guide, use_container_width=True)
                else:
                    st.write("🪖")

        # 하단: 차트 영역
        st.markdown("<br>", unsafe_allow_html=True)
        col_chart_left, col_chart_right = st.columns(2)

        # 하단 좌측: 산점도
        with col_chart_left:
            st.markdown("### 📉 낭비 vs 총 소비 상관관계 분석도")
            
            if len(monthly_agg) > 1:
                fig_scatter = px.scatter(
                    monthly_agg, 
                    x="waste", 
                    y="total", 
                    text="month",
                    labels={"waste": "낭비 (충동+게으름)", "total": "총 소비"},
                    size=[10]*len(monthly_agg),
                    color="total",
                    color_continuous_scale="Reds"
                )
                try:
                    z = np.polyfit(monthly_agg["waste"], monthly_agg["total"], 1)
                    p = np.poly1d(z)
                    x_range = np.linspace(monthly_agg["waste"].min(), monthly_agg["waste"].max(), 100)
                    fig_scatter.add_trace(go.Scatter(
                        x=x_range, 
                        y=p(x_range), 
                        mode='lines', 
                        name='추세선', 
                        line=dict(dash='dot', color='red', width=2)
                    ))
                except Exception:
                    pass
                
                fig_scatter.update_layout(
                    margin=dict(t=20, l=10, r=10, b=10),
                    height=450,
                    xaxis_tickformat=',',
                    yaxis_tickformat=',',
                    showlegend=True
                )
                fig_scatter.update_traces(textposition="top center", textfont_size=10)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("🪖 훈련 데이터 부족! 최소 2개월 이상의 기록이 필요합니다.")

        # 하단 우측: 히트맵
        with col_chart_right:
            filter_options = ["충동", "게으름", "호흡", "성장"]
            selected_types = st.multiselect(
                "📌 분석할 유형을 선택하세요 (복수 선택 가능)", 
                options=filter_options, 
                default=filter_options,
                help="분석하고 싶은 소비 유형을 선택하세요"
            )

            title_text = f"선택된 유형({', '.join(selected_types)})의 전체 소비 히트맵" if selected_types else "유형을 선택하세요"
            st.markdown(f"### 🌡️ {title_text}")

            if selected_types:
                target_df = df[df["재해석"].isin(selected_types)]
            else:
                target_df = pd.DataFrame()
                st.warning("⚠️ 분석할 유형을 하나 이상 선택해주세요.")

            if not target_df.empty:
                heatmap_data = target_df.groupby(["weekday_name", "hour"])["비용"].sum().reset_index()
                
                week_order = ["월", "화", "수", "목", "금", "토", "일"]
                pivot_table = heatmap_data.pivot_table(
                    index="weekday_name", columns="hour", values="비용", fill_value=0
                ).reindex(week_order)

                fig_heatmap = px.imshow(
                    pivot_table,
                    labels=dict(x="시간(시)", y="요일", color="소비액"),
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    aspect="auto",
                    color_continuous_scale="Reds",
                    text_auto=True
                )
                fig_heatmap.update_xaxes(range=[-0.5, 23.5], tickmode='linear', dtick=2)
                
                fig_heatmap.update_layout(
                    margin=dict(t=20, l=10, r=10, b=10),
                    height=450
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)
                
                # Top 3 표시 개선
                st.markdown("#### 🏆 선택 항목 합산 소비 Top 3")
                top3 = target_df.nlargest(3, "비용")[["날짜", "대분류", "소분류", "비용", "비고"]].copy()
                top3['날짜'] = top3['날짜'].dt.strftime('%Y-%m-%d')
                top3["비용"] = top3["비용"].apply(format_currency)
                top3 = top3.reset_index(drop=True)
                top3.index = top3.index + 1
                
                # 스타일링된 테이블
                st.dataframe(
                    top3,
                    use_container_width=True,
                    hide_index=False,
                    height=150
                )
            
            elif selected_types:
                st.warning("⚠️ 선택한 유형에 해당하는 소비 내역이 없습니다.")

if __name__ == "__main__":
    main()
