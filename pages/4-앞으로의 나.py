# pages/4_앞으로의_나.py
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
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)

try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("utils/handle_sql.py 파일을 찾을 수 없습니다.")

st.title("🪖 앞으로의 나 – 미래 소비 훈련 시뮬레이션")

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
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 현재 소비 요약", "🔮 미래 소비 시뮬레이션", "🪖 교관의 평가", "🎯 소비 통제 시뮬레이터"]
)

# =========================
# TAB 1: 현재 소비 요약
# =========================
with tab1:
    st.subheader("📈 현재 소비 추세 요약")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("최근 3개월 평균 지출", f"{avg_monthly:,.0f}원")
        st.metric(
            "최근 월 지출",
            f"{last_month:,.0f}원",
            delta=f"{trend:,.0f}원",
            delta_color="inverse"
        )

    with col2:
        st.markdown("**지출 상위 카테고리 TOP 5**")
        st.dataframe(
            category_ratio.reset_index().rename(
                columns={"category": "카테고리", "cost": "지출액"}
            ),
            use_container_width=True
        )

# =========================
# TAB 2: 미래 소비 시뮬레이션
# =========================
with tab2:
    st.subheader("🔮 이대로 가면 벌어질 일")

    future_months = st.slider(
        "몇 개월 뒤를 상상해볼까?",
        min_value=1,
        max_value=12,
        value=3
    )

    predicted_total = avg_monthly * future_months

    st.info(
        f"지금 소비 습관이 유지되면 **{future_months}개월 후 총 지출은 약 "
        f"{predicted_total:,.0f}원** 입니다."
    )

# =========================
# GPT 프롬프트
# =========================
def generate_prompt(avg_monthly, future_months, predicted_total, category_ratio):
    top_categories = "\n".join(
        [f"- {cat}: {cost:,.0f}원" for cat, cost in category_ratio.items()]
    )

    return f"""
너는 소비 훈련소 교관이다.
모호한 표현은 절대 사용하지 마라.

[객관적 수치]
- 최근 3개월 평균 월 지출: {avg_monthly:,.0f}원
- {future_months}개월 유지 시 예상 총 지출: {predicted_total:,.0f}원
- 지출 상위 카테고리:
{top_categories}

아래 형식으로만 답해라.

[판단]
현재 소비는 평균 월 {avg_monthly:,.0f}원을 사용하며, 상위 카테고리에 지출이 집중되어 있다.

[미래 경고]
이 패턴이 {future_months}개월 지속되면 총 {predicted_total:,.0f}원을 사용하게 되며,
현재 수입이 변하지 않을 경우 {future_months}개월 이내 재정 압박이 발생한다.

[즉시 명령]
1. 다음 달부터 가장 큰 지출 카테고리 비용을 최소 20% 감축하라.
2. 월 총 지출을 {avg_monthly * 0.8:,.0f}원 이하로 제한하라.
3. 불필요한 소비 항목은 7일간 기록 후 즉시 차단하라.

모든 문장은 단정적으로 작성하라.
"""

# =========================
# TAB 3: 교관의 평가
# =========================
with tab3:
    st.subheader("🪖 교관의 평가")

    if st.button("미래 소비 평가 받기"):
        with st.spinner("교관이 평가 중이다..."):
            try:
                prompt = generate_prompt(
                    avg_monthly,
                    future_months,
                    predicted_total,
                    category_ratio
                )

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "너는 소비 훈련소 교관이다."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )

                feedback = response.choices[0].message.content
                st.divider()
                st.markdown(feedback)

            except Exception as e:
                st.error(f"AI 호출 중 오류가 발생했습니다: {e}")

# =========================
# TAB 4: 소비 통제 시뮬레이터
# =========================
with tab4:
    st.subheader("🎯 소비 통제 시뮬레이터")

    cut_ratio = st.slider(
        "월 소비를 몇 % 줄일 수 있겠나?",
        min_value=0,
        max_value=50,
        value=10
    )

    reduced_monthly = avg_monthly * (1 - cut_ratio / 100)
    saved = (avg_monthly - reduced_monthly) * future_months

    st.success(
        f"{cut_ratio}% 통제 성공 시\n\n"
        f"- 월 지출: {reduced_monthly:,.0f}원\n"
        f"- {future_months}개월 절약 금액: {saved:,.0f}원"
    )

    st.warning("말뿐인 다짐은 의미 없다. 숫자로 증명해라.")
