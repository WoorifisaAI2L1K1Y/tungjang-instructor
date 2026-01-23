import streamlit as st
import pandas as pd
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
import folium
from streamlit_folium import st_folium
from datetime import datetime

# =========================
# 기본 설정
# =========================
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="텅장 훈련소", page_icon="💸🪖", layout="wide")

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
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
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

# utils 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, "..")
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("utils/handle_sql.py 파일을 찾을 수 없습니다.")

# 헤더 영역
st.markdown("""
<div style="text-align: center; padding: 20px 0; margin-bottom: 30px;">
    <h1 style="color: #1f1f1f; font-size: 36px; font-weight: 700; margin: 0;">
        🪖 미래 소비 훈련소
    </h1>
    <p style="color: #666; font-size: 16px; margin-top: 10px;">
        지금의 선택이 미래를 만든다. 숫자는 거짓말을 하지 않는다.
    </p>
</div>
""", unsafe_allow_html=True)

# =========================
# 예산 로드
# =========================
BUDGET_FILE = "data/budget_settings.json"
DEFAULT_BUDGET = 1_000_000

def load_budget():
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, "r") as f:
                data = json.load(f)
                return data.get("budget", DEFAULT_BUDGET)
        except:
            return DEFAULT_BUDGET
    return DEFAULT_BUDGET

monthly_budget = load_budget()

# =========================
# 데이터 로드
# =========================
@st.cache_data(ttl=600)
def load_expense_data():
    query = """
    SELECT date, time, category, reason, cost
    FROM card
    """
    df = handle_sql.get_data(query)
    df["date"] = pd.to_datetime(df["date"])
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df

df = load_expense_data()
if df.empty:
    st.warning("⚠️ 소비 데이터가 없어 훈련이 불가합니다.")
    st.stop()

# =========================
# 공통 계산
# =========================
monthly = df.groupby("month")["cost"].sum().reset_index()
recent_3 = monthly.tail(3)
avg_monthly = recent_3["cost"].mean()

category_ratio = (
    df.groupby("category")["cost"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)

current_month = datetime.now().strftime("%Y-%m")
used_this_month = df[df["month"] == current_month]["cost"].sum()

# =========================
# 공통 계산(남은 일수 / 하루 사용 가능 금액)
# =========================
today = datetime.now()
days_in_month = pd.Period(today.strftime("%Y-%m")).days_in_month
remaining_days = days_in_month - today.day
remaining_budget = monthly_budget - used_this_month
daily_available = remaining_budget / remaining_days if remaining_days > 0 else 0

# =========================
# 재해석 매핑 (TAB1에서 낭비 계산용)
# =========================
def apply_reinterpretation(df):
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
    
    df = df.copy()
    df['sub_category'] = df['reason']  # reason을 소분류로 사용
    def get_category(row):
        return mapping_rules.get((row['category'], row['sub_category']), "중립")
    df['재해석'] = df.apply(get_category, axis=1)
    return df

df_reinterpreted = apply_reinterpretation(df)

# =========================
# 프롬프트 생성
# =========================
def generate_final_prompt(
    budget,
    used_amount,
    remaining_days,
    daily_limit,
    waste_amount
):
    return f"""
너는 소비 훈련소 교관이다. 이 훈련의 최종 결론을 내야 한다.
아래 사용자 지출 정보를 보고 최종 교관의 한마디를 출력해라.
현재 남은 일수 대비 하루에 사용할 수 있는 금액을 포함하고, 
낭비 비용에 따라 사용자가 어떻게 해야하는지 한 문장으로 분석해라.

사용자는 월 예산: {budget:,.0f}원
현재까지 사용한 금액: {used_amount:,.0f}원
남은 일 수: {remaining_days}일
남은 일 동안 쓸 수 있는 금액: {daily_limit:,.0f}원
낭비(충동+게으름)비용: {waste_amount:,.0f}원

출력은 반드시 교관 말투인 명령어로 해야하며, 군대에서 처럼 다,나,까 말투로 출력해라.
개조식이 아닌 자연스러운 말투로 5문장 이내로 출력해라.
"""

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(
    ["🪖 교관의 평가", "📆 일일 생존비", "🔮 희망회로"]
)

# =========================
# TAB 1: 교관의 평가
# =========================
with tab1:
    st.markdown('<div class="section-header">🪖 교관의 최종 평가</div>', unsafe_allow_html=True)

    instructor_img_path = "./images/5-교관의_한마디.png"
    bg_color = "#FFF3CD"  # 말풍선 배경색

    if "coach_feedback" not in st.session_state:
        st.session_state.coach_feedback = "훈련병, 버튼을 눌러 평가를 받아라."

    # 메인 페이지와 동일한 레이아웃: 이미지와 말풍선 나란히
    sub_img, sub_bubble = st.columns([1.8, 2.5])
    
    with sub_img:
        try:
            st.image(instructor_img_path, use_container_width=True)
        except:
            st.write("🪖")
    
    with sub_bubble:
        bubble_style = f"""
        <style>
        .speech-bubble {{
            position: relative;
            background: {bg_color};
            border-radius: 12px;
            padding: 18px 22px;
            color: #333;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.15);
            margin-left: 10px;
            display: flex;
            align-items: center;
            min-height: 90px;
            border: 2px solid rgba(0,0,0,0.08);
        }}
        .speech-bubble:after {{
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            width: 0;
            height: 0;
            border: 14px solid transparent;
            border-right-color: {bg_color};
            border-left: 0;
            margin-top: -14px;
            margin-left: -14px;
        }}
        .bubble-text {{
            font-size: 15px;
            font-weight: 600;
            line-height: 1.6;
            margin: 0;
            font-family: 'Malgun Gothic', sans-serif;
        }}
        </style>
        """
        st.markdown(bubble_style, unsafe_allow_html=True)
        st.markdown(
            f'<div class="speech-bubble"><p class="bubble-text">{st.session_state.coach_feedback}</p></div>',
            unsafe_allow_html=True
        )

    # 낭비(충동+게으름) 계산
    month_df = df_reinterpreted[df_reinterpreted["month"] == current_month]
    waste_amount = month_df[month_df["재해석"].isin(["충동", "게으름"])]["cost"].sum()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧠 미래 평가 받기", use_container_width=True):
        with st.spinner("교관이 판단 중입니다..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 소비 훈련소 교관이다."},
                    {"role": "user", "content": generate_final_prompt(
                        monthly_budget,
                        used_this_month,
                        remaining_days,
                        daily_available,
                        waste_amount
                    )}
                ],
                temperature=0.4
            )
            st.session_state.coach_feedback = response.choices[0].message.content.replace("\n", "<br>")
            st.rerun()

# =========================
# TAB 2: 일일 생존비
# =========================
with tab2:
    st.markdown('<div class="section-header">📆 일일 생존비</div>', unsafe_allow_html=True)

    # 메트릭 카드 함수
    def create_metric_card(title, value, value_color="#1f1f1f", bg_color="white"):
        return f"""
        <div class="metric-card" style="background-color: {bg_color};">
            <div>
                <div style="font-size: 13px; color: #666; margin-bottom: 8px; font-weight: 500;">
                    {title}
                </div>
                <div style="font-size: 28px; font-weight: 700; color: {value_color};">
                    {value}
                </div>
            </div>
        </div>
        """

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(create_metric_card("나의 월 예산", f"{monthly_budget:,.0f}원"), unsafe_allow_html=True)

    with col2:
        st.markdown(create_metric_card("현재까지 사용한 금액", f"{used_this_month:,.0f}원"), unsafe_allow_html=True)

    if remaining_budget < 0:
        st.error(f"⚠️ 예산 초과: {remaining_budget:,.0f}원")
    else:
        st.success(f"✅ 사용 가능한 남은 금액: {remaining_budget:,.0f}원")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.markdown(create_metric_card("📅 남은 일수", f"{remaining_days}일", "#1f1f1f", "#f8f9fa"), unsafe_allow_html=True)
    c2.markdown(create_metric_card("📌 하루 사용 가능 금액", f"{daily_available:,.0f}원", "#1f1f1f", "#f8f9fa"), unsafe_allow_html=True)

# =========================
# TAB 3: 희망회로
# =========================
with tab3:
    st.markdown('<div class="section-header">🔮 희망회로</div>', unsafe_allow_html=True)

    # 메트릭 카드 함수
    def create_metric_card(title, value, value_color="#1f1f1f", bg_color="white"):
        return f"""
        <div class="metric-card" style="background-color: {bg_color};">
            <div>
                <div style="font-size: 13px; color: #666; margin-bottom: 8px; font-weight: 500;">
                    {title}
                </div>
                <div style="font-size: 28px; font-weight: 700; color: {value_color};">
                    {value}
                </div>
            </div>
        </div>
        """

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(create_metric_card("나의 월 예산", f"{monthly_budget:,.0f}원"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("예상 월 지출", f"{avg_monthly:,.0f}원"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    months = st.slider("몇 개월간 버틸 것인가?", 1, 12, 6, help="저축 기간을 선택하세요")
    savings = (monthly_budget - avg_monthly) * months

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(create_metric_card("예상 모은 금액", f"{savings:,.0f}원", "#1f1f1f", "#f8f9fa"), unsafe_allow_html=True)

    destination = ""
    center_lat, center_lon, zoom = 37.5, 127, 3

    # 1. 저축액에 따른 목적지 및 지도 중심 좌표 설정
    if savings < 0:
        destination = "논산 훈련소"
        # 육군훈련소 (연무대)
        center_lat, center_lon, zoom = 36.1223, 127.1139, 13
        
    elif savings < 500_000:
        destination = "부산"
        # 부산 시청 및 중심가
        center_lat, center_lon, zoom = 35.1796, 129.0756, 11
        
    elif savings < 1_000_000:
        destination = "일본"
        # 도쿄 (일본의 대표 도시)
        center_lat, center_lon, zoom = 35.6895, 139.6917, 10
        
    elif savings < 2_000_000:
        destination = "싱가포르"
        # 싱가포르 (도시 국가)
        center_lat, center_lon, zoom = 1.3521, 103.8198, 11
        
    elif savings < 3_000_000:
        destination = "호주"
        # 시드니 (호주의 대표 랜드마크)
        center_lat, center_lon, zoom = -33.8688, 151.2093, 11
        
    else:
        destination = "뉴욕"
        # 뉴욕 맨해튼
        center_lat, center_lon, zoom = 40.7128, -74.0060, 11

    # 2. 지도 생성
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="CartoDB positron"
    )

    def mark(lat, lon, ko, en):
        folium.Marker(
            [lat, lon],
            tooltip=f"{ko} / {en}",
            popup=f"<b>{ko}</b><br>{en}",
            icon=folium.Icon(icon="plane", prefix="fa", color="blue")
        ).add_to(fmap)

    # 3. 목적지에 맞는 마커 표시 (상단 좌표와 일치시킴)
    if destination == "논산 훈련소":
        mark(36.1223, 127.1139, "논산 훈련소", "Nonsan Training Center")
    elif destination == "부산":
        mark(35.1796, 129.0756, "부산 여행", "Busan")
    elif destination == "일본":
        mark(35.6895, 139.6917, "일본 여행", "Japan (Tokyo)")
    elif destination == "싱가포르":
        mark(1.3521, 103.8198, "싱가포르 여행", "Singapore")
    elif destination == "호주":
        mark(-33.8688, 151.2093, "호주 여행", "Australia (Sydney)")
    else:
        mark(40.7128, -74.0060, "뉴욕 여행", "New York")

    st.markdown("<br>", unsafe_allow_html=True)
    st.success(f"🧭 이번 희망회로 결과: **{destination} 가능**")
    st_folium(fmap, height=450, width=800)
