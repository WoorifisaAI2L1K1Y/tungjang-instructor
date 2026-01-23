# pages/4_앞으로의_나.py
import streamlit as st
import pandas as pd
import datetime
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------------------------------------------------
# 1. 초기 설정 및 모듈 경로 설정
# --------------------------------------------------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(
    page_title="앞으로의 나",
    page_icon="🪖",
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

st.title("🪖 앞으로의 나 – 미래 소비 훈련 시뮬레이션")


# --------------------------------------------------------------------------------
# 2. 데이터 로드 (handle_sql 사용)
# --------------------------------------------------------------------------------
@st.cache_data(ttl=600)  # 캐시 유효 시간 추가 (옵션)
def load_expense_data():
    try:
        # DB 연결 정보는 handle_sql 내부에서 처리
        query = """
        SELECT date, time, category, reason, cost
        FROM card
        """
        
        # [변경됨] handle_sql을 통해 DataFrame으로 가져옴
        df = handle_sql.get_data(query)

        if df.empty:
            return pd.DataFrame()

        # 데이터 전처리
        df["date"] = pd.to_datetime(df["date"])
        # cost 컬럼 숫자형 변환 (안전장치)
        df["cost"] = pd.to_numeric(df["cost"], errors='coerce').fillna(0)
        
        # 파생 변수 생성
        df["month"] = df["date"].dt.to_period("M").astype(str)
        df["weekday"] = df["date"].dt.day_name()

        return df

    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()


df = load_expense_data()

if df.empty:
    st.warning("소비 데이터가 없습니다. 훈련 불가.")
    st.stop()

# =========================
# 미래 소비 예측용 요약
# =========================
st.subheader("📈 현재 소비 추세 요약")

monthly = (
    df.groupby("month")["cost"]
    .sum()
    .reset_index()
)

recent_3 = monthly.tail(3)

# 데이터가 충분하지 않을 경우 처리
if len(recent_3) > 0:
    avg_monthly = recent_3["cost"].mean()
    last_month = recent_3.iloc[-1]["cost"]
    trend = last_month - avg_monthly
else:
    avg_monthly = 0
    last_month = 0
    trend = 0

category_ratio = (
    df.groupby("category")["cost"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
)

col1, col2 = st.columns(2)

with col1:
    st.metric("최근 3개월 평균 지출", f"{avg_monthly:,.0f}원")
    st.metric(
        "최근 월 지출",
        f"{last_month:,.0f}원",
        delta=f"{trend:,.0f}원",
        delta_color="inverse" # 지출이 늘면 빨간색(부정적)으로 표시
    )

with col2:
    st.write("### 💣 주요 지출 카테고리 TOP 5")
    st.dataframe(category_ratio, use_container_width=True)

# =========================
# 미래 시뮬레이션
# =========================
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
# GPT 프롬프트 생성
# =========================
def generate_prompt(df, avg_monthly, future_months, predicted_total, category_ratio):
    # category_ratio는 Series 형태이므로 items() 사용
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
# GPT 호출
# =========================
if st.button("🪖 미래 소비 평가 받기"):
    with st.spinner("교관이 평가 중이다..."):
        prompt = generate_prompt(
            df,
            avg_monthly,
            future_months,
            predicted_total,
            category_ratio
        )

        try:
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
            st.subheader("🗣️ 교관의 평가")
            st.markdown(feedback)
            
        except Exception as e:
            st.error(f"AI 호출 중 오류가 발생했습니다: {e}")

# =========================
# 추가: 수동 시뮬레이터
# =========================
st.divider()
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