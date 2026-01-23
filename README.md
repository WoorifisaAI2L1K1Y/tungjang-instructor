<div align="center">

<img src="./images/logo.png" width="200" alt="Tungjang Instructor Logo">

# 🪖 텅장 훈련소 (Tungjang Instructor)

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT_4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

<br>

> **"본인의 소비에 있어서는 한없이 관대한 우리들,**<br>
> **무엇이 낭비인지 모르고 빠져나가는 수많은 돈들..."**

<br>

### **"말뿐인 다짐은 의미 없다. 숫자로 증명해라."**
\- 텅장 훈련소 교관 -

<br>

**텅장 훈련소**는 당신의 텅텅 비어가는 통장을 막기 위해,<br>
**교관**의 엄격한 지휘 아래 소비 습관을 교정하고 훈련하는 **자산 관리 훈련 프로그램**입니다.

<br>

</div>

---

## 🎯 프로젝트 목적 (Mission)

자신의 소비 패턴을 객관적으로 직시하지 못하는 훈련병들을 위해 **'교관'**이 직접 나섰습니다.
단순히 가계부를 작성하는 것을 넘어, **소비의 성격을 재해석**하고 **미래를 시뮬레이션**하여 강인한 경제 습관을 기르는 것이 본 훈련소의 목표입니다.

---

## 📂 주요 훈련 과정 (Features)

### 1. 메인 훈련장 (Main Training Center)
훈련의 시작점입니다. 이번 달 목표 예산을 설정하고, 실시간으로 교관의 피드백을 받습니다.

* **💰 예산 설정**: 사이드바를 통해 월간 목표 예산을 설정합니다.
* **📢 교관의 감정 상태**: 예산 소진율에 따라 교관의 표정과 메시지가 실시간으로 변화합니다.

| 예산 소진율 | 상태 | 교관의 표정 | 교관의 한마디 |
| :---: | :---: | :---: | :--- |
| **미설정** | **궁금** | <img src="./images/0-궁금.png" width="80"> | "훈련생! 이번 달 예산을 설정하지 않았군.<br>좌측 사이드바에 입력하게!" |
| **0 ~ 30%** | **온화** | <img src="./images/1-온화.png" width="80"> | "예산의 30% 이하만 사용했군.<br>아주 훌륭해! 이 페이스를 유지하게. 😊" |
| **30 ~ 60%** | **걱정** | <img src="./images/2-걱정.png" width="80"> | "벌써 예산의 절반 이상을 썼다.<br>적당히 돈을 써야 된다! 😟" |
| **60 ~ 100%** | **짜증** | <img src="./images/3-짜증.png" width="80"> | "비상! 예산이 거의 바닥났다!<br>이제부터는 숨만 쉬고 살아라! 😠" |
| **100% 초과** | **화남** | <img src="./images/4-화남.png" width="80"> | "예산 초과다!!<br>훈련생, 자네는 계획이란 게 없나?! 😡" |

* **📊 전황 분석**: 전체 소비액, 낭비 소비액, 낭비율을 직관적으로 보여주는 상황판을 제공합니다.

<br>

### 2. 소비 기록 (Spending Record)
훈련의 기본은 철저한 기록입니다.

* **📝 작전 기록**: 날짜, 시간, 대분류/중분류(식비, 주거, 금융 등), 금액, 메모를 입력하여 DB에 즉시 보고합니다.
* **📅 월간 캘린더**: `Streamlit Calendar`를 활용해 날짜별 지출 전황을 한눈에 파악하고, 클릭 시 상세 내역을 브리핑합니다.

<br>

### 3. 지금까지의 나 (Past Analysis)
과거의 나약했던 소비 습관을 심층 분석하여 뜯어고칩니다.

* **🧠 소비 성격 재해석**: 단순 카테고리를 넘어, 소비의 본질을 4가지 유형으로 재정의합니다.
    * 🔴 **게으름**: 배달, 택시 등 편리함에 굴복한 비용
    * 🟠 **충동**: 카페, 쇼핑, 유흥 등 계획 없는 지출
    * 🔵 **호흡**: 월세, 공과금 등 생존을 위한 필수 비용
    * 🟢 **성장**: 도서, 운동, 투자 등 미래를 위한 탄약
* **📉 패턴 정밀 타격**: '낭비'와 '총 지출' 간의 상관계수를 분석하여 소비 폭주 원인을 찾아냅니다.
* **🔥 지출 히트맵**: 요일별/시간대별 지출이 집중되는 '취약 시간대'를 시각화합니다.

<br>

### 4. 앞으로의 나 (Future Prediction)
현재의 나태함이 미래에 어떤 재앙을 불러올지 시뮬레이션합니다.

* **🔮 미래 시나리오**: 유지(😐), 절약(😇 -20%), 폭증(😈 +15%) 시나리오에 따른 미래 자산 변화를 예측합니다.
* **🚨 위험 등급 산정**: 현재 패턴을 분석하여 `STABLE`, `WARNING`, `HIGH RISK` 등급을 매깁니다.
* **🤖 AI 교관의 최종 평가**: **OpenAI GPT-4o-mini**가 당신의 소비 데이터를 분석하여 뼈 때리는 조언과 즉시 실행 명령을 하달합니다.

---

## 🛠 기술 스택 (Tech Stack)

| 구분 | 기술 | 설명 |
| :--- | :--- | :--- |
| **Framework** | ![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) | 직관적인 웹 대시보드 및 인터랙티브 UI 구현 |
| **Language** | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | 핵심 로직 및 데이터 처리 |
| **Data Analysis** | ![Pandas](https://img.shields.io/badge/-Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/-NumPy-013243?style=flat-square&logo=numpy&logoColor=white) | 대용량 소비 데이터 전처리 및 통계 분석 |
| **Visualization** | ![Plotly](https://img.shields.io/badge/-Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white) ![Altair](https://img.shields.io/badge/-Altair-F2C811?style=flat-square&logo=vega&logoColor=black) | 동적 차트, 히트맵, 상관관계 산점도 시각화 |
| **Database** | ![MySQL](https://img.shields.io/badge/-MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white) | 지출 데이터의 안정적인 저장 및 관리 (`PyMySQL`) |
| **AI Intelligence** | ![OpenAI](https://img.shields.io/badge/-GPT_4o_mini-412991?style=flat-square&logo=openai&logoColor=white) | 개인화된 소비 피드백 및 코칭 메시지 생성 |

---

## 🚀 훈련소 입소 방법 (Getting Started)

훈련을 시작하려면 아래 절차를 따르십시오.

### 1. 환경 설정 (Prerequisites)
* Python 3.9 이상
* MySQL Database

### 2. 설치 (Installation)
```bash
# 레포지토리 클론
git clone [https://github.com/your-repo/tungjang-instructor.git](https://github.com/your-repo/tungjang-instructor.git)

# 디렉토리 이동
cd tungjang-instructor

# 필수 패키지 설치
pip install -r requirements.txt

# 실행 (local 시)
streamlit run main.py
```