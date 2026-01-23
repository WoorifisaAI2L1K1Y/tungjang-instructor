import streamlit as st
import pandas as pd
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

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

# utils 폴더 경로 설정
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
# 데이터 로드
# =========================
@st.cache_data(ttl=600)
def load_expense_data():
    try:
        query = """
        SELECT date, time, category, reason, cost
        FROM card
        """
        df = handle_sql.get_data(query)

        if df.empty:
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"])
        df["cost"] = pd.to_numeric(df["cost"], errors="coerce").fillna(0)
        df["month"] = df["date"].dt.to_period("M").astype(str)
        df["weekday"] = df["date"].dt.day_name()

        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()


df = load_expense_data()

if df.empty:
    st.warning("소비 데이터가 없어 훈련이 불가하다.")
    st.stop()

# =========================
# 공통 계산
# =========================
monthly = df.groupby("month")["cost"].sum().reset_index()
recent_3 = monthly.tail(3)

if len(recent_3) > 0:
    avg_monthly = recent_3["cost"].mean()
    last_month = recent_3.iloc[-1]["cost"]
    trend = last_month - avg_monthly
else:
    avg_monthly = last_month = trend = 0

category_ratio = (
    df.groupby("category")["cost"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(
    ["🔮 미래 시나리오", "📉 위험 예측", "🪖 교관의 평가"]
)

# =========================
# TAB 1: 미래 시나리오
# =========================
with tab1:
    st.subheader("🔮 미래 소비 시나리오 선택")

    col1, col2 = st.columns([1, 2])

    with col1:
        future_months = st.slider(
            "몇 개월 뒤를 볼 것인가?",
            min_value=1,
            max_value=12,
            value=6
        )

        scenario = st.radio(
            "소비 시나리오",
            ["😐 유지", "😇 절약 (-20%)", "😈 폭증 (+15%)"]
        )

    multiplier = {
        "😐 유지": 1.0,
        "😇 절약 (-20%)": 0.8,
        "😈 폭증 (+15%)": 1.15
    }[scenario]

    predicted_monthly = avg_monthly * multiplier
    predicted_total = predicted_monthly * future_months

    with col2:
        st.metric("예상 월 지출", f"{predicted_monthly:,.0f}원")
        st.metric(
            f"{future_months}개월 총 지출",
            f"{predicted_total:,.0f}원"
        )

    # 누적 지출 시각화
    sim_df = pd.DataFrame({
        "month": range(1, future_months + 1),
        "누적 지출": [predicted_monthly * i for i in range(1, future_months + 1)]
    })

    st.line_chart(sim_df.set_index("month"))

# =========================
# TAB 2: 위험 예측
# =========================
with tab2:
    st.subheader("📉 미래 위험 예측")

    danger_line = avg_monthly * 1.1

    if predicted_monthly > danger_line:
        st.error("🚨 위험 상태: 현재 패턴은 통제 불능이다.")
        level = "HIGH RISK"
    elif predicted_monthly > avg_monthly:
        st.warning("⚠️ 주의 상태: 소비가 증가 추세다.")
        level = "WARNING"
    else:
        st.success("✅ 안정 상태: 통제 가능한 소비다.")
        level = "STABLE"

    st.metric("위험 등급", level)

    # 카테고리 비중 시각화
    st.subheader("💸 지출 상위 카테고리")
    st.bar_chart(category_ratio)

# =========================
# GPT 프롬프트
# =========================
def generate_prompt(avg_monthly, future_months, predicted_total, category_ratio, scenario):
    top_categories = "\n".join(
        [f"- {cat}: {cost:,.0f}원" for cat, cost in category_ratio.items()]
    )

    return f"""
너는 소비 훈련소 교관이다.
모호한 표현은 절대 사용하지 마라.

[시나리오]
{scenario}

[객관적 수치]
- 평균 월 지출: {avg_monthly:,.0f}원
- {future_months}개월 예상 총 지출: {predicted_total:,.0f}원
- 지출 상위 카테고리:
{top_categories}

아래 형식으로만 답해라.

[판단]

[미래 경고]

[즉시 명령]

모든 문장은 단정적으로 작성하라.
"""

# =========================
# TAB 3: 교관의 평가
# =========================
with tab3:
    st.subheader("🪖 교관의 최종 평가")

    instructor_img_path = r"./images/5-교관의_한마디.png"

    # 말풍선 CSS (다른 파일에서 사용한 스타일 차용)
    st.markdown(
    """
    <style>
    .speech-bubble {
        position: relative;
        background: #FFF3CD; /* 노란 말풍선 */
        border-radius: 12px;
        padding: 16px;
        color: #333;
        box-shadow: 1px 1px 4px rgba(0,0,0,0.15);
        margin-left: 8px;
        min-height: 100px;
        display: flex;
        align-items: center;
        font-size: 16px;
        line-height: 1.6;
        font-weight: 600;
    }
    .speech-bubble:after {
        content: '';
        position: absolute;
        left: 0;
        top: 40px;
        width: 0;
        height: 0;
        border: 12px solid transparent;
        border-right-color: #FFF3CD; /* 꼬리도 같은 노랑 */
        border-left: 0;
        margin-top: -12px;
        margin-left: -12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


    # 상태 저장 (버튼 전/후 말풍선 유지용)
    if "coach_feedback" not in st.session_state:
        st.session_state.coach_feedback = "훈련병, 아직 판단할 정보가 부족하다.<br>아래 버튼을 눌러 미래를 확인해라."

    # 레이아웃: 이미지 | 말풍선
    col_img, col_bubble = st.columns([1.2, 3.8])

    with col_img:
        st.image(instructor_img_path, use_container_width=True)

    with col_bubble:
        st.markdown(
            f"""
            <div class="speech-bubble">
            {st.session_state.coach_feedback}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 버튼
    if st.button("🧠 미래 평가 받기"):
        with st.spinner("교관이 판단 중이다..."):
            try:
                prompt = generate_prompt(
                    avg_monthly,
                    future_months,
                    predicted_total,
                    category_ratio,
                    scenario
                )

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "너는 소비 훈련소 교관이다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6
                )

                # 응답을 세션에 저장 → 말풍선 내용 교체
                st.session_state.coach_feedback = response.choices[0].message.content.replace(
                    "\n", "<br>"
                )

                st.rerun()

            except Exception as e:
                st.error(f"AI 호출 중 오류 발생: {e}")
    st.warning("말뿐인 다짐은 의미 없다. 숫자로 증명해라.")
