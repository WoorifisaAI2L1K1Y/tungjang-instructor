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
    st.error("handle_sql.py 파일을 찾을 수 없습니다.")

# --- [1. 기본 설정 및 배경색 지정] ---
st.set_page_config(page_title="텅장 훈련소", layout="centered")

# 페이지 전체 배경색 설정
page_bg_color = "#fcfcfb"
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {page_bg_color};
    }}
    </style>
    """, unsafe_allow_html=True)

def main():
    # --- [2. 로고 영역 (작게 유지)] ---
    logo_l, logo_m, logo_r = st.columns([2, 2, 2])
    with logo_m:
        try:
            st.image('./images/logo.png', use_container_width=True)
        except:
            st.markdown("<h3 style='text-align: center;'>💸 텅장 훈련소 💸</h3>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- [3. 데이터 분석 로직] ---
    df_negative = handle_sql.get_data(SQL = """SELECT reason, SUM(cost) AS total_cost
            FROM sample
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            AND reason IN (
                '배달/야식', '카페/간식', '술/유흥', '패션/미용', 
                '가전/가구', '택시/호출', '데이트/모임', '영화/공연', '여행'
            )
            GROUP BY reason
            WITH ROLLUP""")
    
    df_all = handle_sql.get_data(SQL="""SELECT reason, SUM(cost) AS total_cost
            FROM sample
            WHERE date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
            GROUP BY reason
            WITH ROLLUP""")

    # 기본값 초기화
    negative_sum = 0
    total_sum = 0
    category_msg = "기타"

    try:
        if not df_negative.empty:
            negative_sum = df_negative.iloc[-1]['total_cost']
            df_sorted = df_negative.iloc[:-1].sort_values(by='total_cost', ascending=False)
            top_categories = df_sorted['reason'].head(2).tolist()
            
            if len(top_categories) >= 2:
                category_msg = f"<b>{top_categories[0]}</b>, <b>{top_categories[1]}</b>"
            elif len(top_categories) == 1:
                category_msg = f"<b>{top_categories[0]}</b>"

        if not df_all.empty:
            total_sum = df_all.iloc[-1]['total_cost']

    except (IndexError, KeyError, Exception) as e:
        st.error(f"데이터 처리 오류: {e}")
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

    # --- [5. 메인 레이아웃 구성] ---
    
    # 5-1. Info Box 함수 정의 (margin-bottom 추가하여 세로 간격 확보)
    def info_box(label, value, color="black"):
        return f"""
        <div style="
            background-color: white; 
            padding: 8px; 
            border-radius: 8px; 
            text-align: center; 
            box-shadow: 0px 1px 2px rgba(0,0,0,0.1);
            border: 1px solid #eee;
            margin-bottom: 8px;"> 
            <p style="font-size: 11px; color: #888; margin: 0;">{label}</p>
            <p style="font-size: 15px; font-weight: bold; color: {color}; margin: 2px 0 0 0;">{value}</p>
        </div>
        """

    # 5-2. 화면 분할 (좌측: 교관 / 우측: 정보박스)
    # 비율을 [3, 1] 정도로 주어 교관 말풍선 영역을 넓게 확보
    main_col_left, main_col_right = st.columns([3, 1])

    # === [좌측 컬럼: 교관 이미지 + 말풍선] ===
    with main_col_left:
        st.markdown("#### 📢 교관의 한마디")
        
        # 내부 분할 (이미지 : 말풍선)
        sub_img, sub_bubble = st.columns([1.8, 2.5])
        
        with sub_img:
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.write("😐")
        
        with sub_bubble:
            # 말풍선 CSS
            bubble_style = f"""
            <style>
            .speech-bubble {{
                position: relative;
                background: {bg_color};
                border-radius: 12px;
                padding: 15px;
                color: #333;
                box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
                margin-left: 5px;
                display: flex;
                align-items: center;
                min-height: 80px;
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
            </style>
            """
            st.markdown(bubble_style, unsafe_allow_html=True)
            st.markdown(f'<div class="speech-bubble"><b>{status_text}</b></div>', unsafe_allow_html=True)

    # === [우측 컬럼: 정보 박스 세로 스택] ===
    with main_col_right:
        # 타이틀 높이 맞추기 위한 공백 (선택사항)
        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
        
        # 박스 3개를 세로로 나열 (별도 컬럼 없이 순서대로 출력)
        st.markdown(info_box("지난 한 달간 전체 지출", f"{total_sum:,.0f}원"), unsafe_allow_html=True)
        st.markdown(info_box("지난 한 달간 낭비 지출", f"{negative_sum:,.0f}원", "#dc3545"), unsafe_allow_html=True)
        st.markdown(info_box("훈련생의 낭비율", f"{negative_percent:.1f}%", "#dc3545"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()