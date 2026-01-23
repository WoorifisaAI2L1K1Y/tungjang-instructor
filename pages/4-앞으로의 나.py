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

st.set_page_config(
    page_title="앞으로의 나",
    page_icon="🪖",
    layout="wide"
)

# utils 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, "..")
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("utils/handle_sql.py 파일을 찾을 수 없습니다.")

st.title("🪖 미래 소비 훈련소")
st.caption("지금의 선택이 미래를 만든다. 숫자는 거짓말을 하지 않는다.")

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
    st.warning("소비 데이터가 없어 훈련이 불가하다.")
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
    st.subheader("🪖 교관의 최종 평가")

    instructor_img_path = "./images/5-교관의_한마디.png"

    st.markdown("""
    <style>
    .speech-bubble {
        background: #FFF3CD;
        border-radius: 12px;
        padding: 16px;
        font-weight: 600;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.15);
    }
    </style>
    """, unsafe_allow_html=True)

    if "coach_feedback" not in st.session_state:
        st.session_state.coach_feedback = "훈련병, 버튼을 눌러 평가를 받아라."

    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(instructor_img_path, use_container_width=True)
    with col2:
        st.markdown(
            f"<div class='speech-bubble'>{st.session_state.coach_feedback}</div>",
            unsafe_allow_html=True
        )

    # 낭비(충동+게으름) 계산
    month_df = df_reinterpreted[df_reinterpreted["month"] == current_month]
    waste_amount = month_df[month_df["재해석"].isin(["충동", "게으름"])]["cost"].sum()

    if st.button("🧠 미래 평가 받기"):
        with st.spinner("교관이 판단 중이다..."):
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
    st.subheader("📆 일일 생존비")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("나의 월 예산", f"{monthly_budget:,.0f}원")

    with col2:
        st.metric("현재까지 사용한 금액", f"{used_this_month:,.0f}원")

    if remaining_budget < 0:
        st.error(f"예산 초과: {remaining_budget:,.0f}원")
    else:
        st.success(f"사용 가능한 남은 금액: {remaining_budget:,.0f}원")

    st.markdown("---")

    c1, c2 = st.columns(2)
    c1.metric("📅 남은 일수", f"{remaining_days}일")
    c2.metric("📌 하루 사용 가능 금액", f"{daily_available:,.0f}원")

# =========================
# TAB 3: 희망회로
# =========================
with tab3:
    st.subheader("🔮 희망회로")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("나의 월 예산", f"{monthly_budget:,.0f}원")
    with col2:
        st.metric("예상 월 지출", f"{avg_monthly:,.0f}원")

    months = st.slider("몇 개월간 버틸 것인가?", 1, 12, 6)
    savings = (monthly_budget - avg_monthly) * months

    st.metric("예상 모은 금액", f"{savings:,.0f}원")

    destination = ""
    center_lat, center_lon, zoom = 37.5, 127, 3

    if savings < 0:
        destination = "논산 훈련소"
        center_lat, center_lon, zoom = 36.187, 127.098, 11
    elif savings < 500_000:
        destination = "국내 여행"
        center_lat, center_lon, zoom = 36.5, 127.8, 6
    elif savings < 1_000_000:
        destination = "일본"
        center_lat, center_lon, zoom = 35.6762, 139.6503, 5
    elif savings < 2_000_000:
        destination = "두바이"
        center_lat, center_lon, zoom = 25.2048, 55.2708, 5
    elif savings < 3_000_000:
        destination = "파리"
        center_lat, center_lon, zoom = 48.8566, 2.3522, 5
    else:
        destination = "아이슬란드"
        center_lat, center_lon, zoom = 64.9631, -19.0208, 4

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

    if destination == "논산 훈련소":
        mark(36.187, 127.098, "논산 훈련소", "Nonsan Training Center")
    elif destination == "국내 여행":
        mark(37.5665, 126.9780, "국내 여행", "Domestic Trip")
    elif destination == "일본":
        mark(35.6762, 139.6503, "일본 여행", "Japan")
    elif destination == "두바이":
        mark(25.2048, 55.2708, "두바이", "Dubai")
    elif destination == "파리":
        mark(48.8566, 2.3522, "파리", "Paris")
    else:
        mark(64.9631, -19.0208, "아이슬란드", "Iceland")

    st.success(f"🧭 이번 희망회로 결과: **{destination} 가능**")
    st_folium(fmap, height=450, width=800)
