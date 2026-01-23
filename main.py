import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..')
sys.path.append(parent_dir)
try:
    import utils.handle_sql as handle_sql
except ImportError:
    st.error("get_data.py 파일을 찾을 수 없습니다.")

# --- [1. 기본 설정 및 배경색 지정] ---
st.set_page_config(page_title="소비 습관 분석", layout="centered")

# 페이지 전체 배경색을 설정하는 CSS (원하는 색상 코드로 수정 가능)
page_bg_color = "#fcfcfb"  # 예: 아주 연한 회색/하늘색
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {page_bg_color};
    }}
    </style>
    """, unsafe_allow_html=True)



def main():
    # --- [2. 로고 영역] ---
    logo_l, logo_m, logo_r = st.columns([1, 2, 1])
    with logo_m:
        try:
            st.image('./images/logo.png', use_container_width=True)
        except:
            st.markdown("<h1 style='text-align: center;'>💸 텅장 훈련소 💸</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # --- [3. 데이터 분석 로직 (기존과 동일)] ---
    df_negative = handle_sql.get_data(SQL = """SELECT reason, SUM(cost) AS total_cost
            FROM sample
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            AND reason IN (
                '배달/야식', 
                '카페/간식', 
                '술/유흥', 
                '패션/미용', 
                '가전/가구', 
                '택시/호출', 
                '데이트/모임', 
                '영화/공연', 
                '여행'
            )
            GROUP BY reason""")
    df_all = handle_sql.get_data(SQL="""SELECT reason, SUM(cost) AS total_cost
            FROM sample
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            GROUP BY reason""")

    try:
        negative_sum = df_negative.iloc[-1]['total_cost']
        total_sum = df_all.iloc[-1]['total_cost']
        df_sorted = df_negative.iloc[:-1].sort_values(by='total_cost', ascending=False)
        top_categories = df_sorted['reason'].head(2).tolist()
        
        category_msg = ""
        if len(top_categories) >= 2:
            category_msg = f"<b>{top_categories[0]}</b>이랑 <b>{top_categories[1]}</b>"
        elif len(top_categories) == 1:
            category_msg = f"<b>{top_categories[0]}</b>"
            
    except (IndexError, KeyError):
        st.error("데이터 구조를 확인해주세요.")
        return

    negative_percent = (negative_sum / total_sum) * 100 if total_sum > 0 else 0


    # --- [4. 조건별 상태 설정] ---
    if negative_percent <= 20:
        img_path, bg_color = './images/1-온화.png', "#D4EDDA"
        status_text = "매우 건전한 소비 생활을 하고 계시네요! 😊"
    elif negative_percent <= 40:
        img_path, bg_color = './images/2-걱정.png', "#FFF3CD"
        status_text = "조금씩 불필요한 지출이 늘고 있어요.<br>주의하세요 😟"
    elif negative_percent <= 60:
        img_path, bg_color = './images/3-짜증.png', "#F8D7DA"
        status_text = f"아~ 슬슬 선을 넘는데요?<br>{category_msg} 좀 줄이세요! 😠"
    else:
        img_path, bg_color = './images/4-화남.png', "#F8D7DA"
        status_text = f"정신 차리세요!<br>지금 {category_msg}에 돈 쓸 때입니까? 😡"

    # --- [5. 교관의 한마디 섹션] ---
    st.markdown("#### 📢 교관의 한마디") # 캐릭터 위에 타이틀 추가

    col_img, col_bubble = st.columns([1, 2.5])

    with col_img:
        try:
            st.image(img_path, use_container_width=True)
        except:
            st.warning("이미지 로드 실패")

    with col_bubble:
        # 말풍선 스타일 (크기 및 폰트 축소 버전)
        bubble_style = f"""
        <style>
        .speech-bubble {{
            position: relative;
            background: {bg_color};
            border-radius: 12px;
            padding: 12px 18px;
            color: #333;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
            margin-left: 15px;
            display: flex;
            align-items: center;
            min-height: 60px; /* 높이 더 축소 */
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
            font-size: 16px; /* 글씨 크기 축소 */
            font-weight: bold;
            line-height: 1.3;
            margin: 0;
        }}
        </style>
        """
        st.markdown(bubble_style, unsafe_allow_html=True)
        st.markdown(f'<div class="speech-bubble"><p class="bubble-text">{status_text}</p></div>', unsafe_allow_html=True)

    # --- [6. 하단 지표] ---
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    col1.metric("전체 지출액", f"{total_sum:,.0f}원")
    col2.metric("부정적 소비", f"{negative_sum:,.0f}원", delta=f"{negative_percent:.1f}%", delta_color="inverse")

    st.markdown("---")
    st.subheader(f"현재 소비 상태: {negative_percent:.2f}%")

if __name__ == "__main__":
    main()