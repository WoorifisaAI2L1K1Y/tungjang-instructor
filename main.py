import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import json

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

# --- [예산 저장 및 로드 함수] ---
BUDGET_FILE = 'data/budget_settings.json'

if not os.path.exists('data'):
    os.makedirs('data')

def load_budget():
    if os.path.exists(BUDGET_FILE):
        with open(BUDGET_FILE, 'r') as f:
            try:
                data = json.load(f)
                return data.get('budget', 0)
            except:
                return 0
    return 0

def save_budget():
    new_value = st.session_state['budget_input']
    with open(BUDGET_FILE, 'w') as f:
        json.dump({'budget': new_value}, f)

def main():
    # --- [사이드바] 예산 입력 ---
    with st.sidebar:
        st.header("💰 예산 설정")
        saved_budget = load_budget()
        monthly_budget = st.number_input(
            "이번 달 목표 예산 (원)",
            min_value=0, 
            value=saved_budget, 
            step=10000,
            help="예산 관리를 위해 목표 금액을 입력하세요.",
            key='budget_input',
            on_change=save_budget
        )

    # --- [2. 로고 영역] ---
    logo_l, logo_m, logo_r = st.columns([2, 2, 2])
    with logo_m:
        try:
            st.image('./images/logo.png', use_container_width=True)
        except:
            st.markdown("<h3 style='text-align: center;'>💸 텅장 훈련소 💸</h3>", unsafe_allow_html=True)
    
    st.markdown("---")

    # --- [3. 데이터 분석 로직] ---
    df_negative = handle_sql.get_data(SQL="""
                                            SELECT reason, SUM(cost) AS total_cost
                                            FROM card
                                            WHERE date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
                                            AND reason IN (
                                                '배달/야식', '카페/간식', '술/유흥', '패션/미용', 
                                                '가전/가구', '택시/호출', '데이트/모임', '영화/공연', '여행'
                                            )
                                            GROUP BY reason
                                     """)
    
    df_all = handle_sql.get_data(SQL="""
                                            SELECT reason, SUM(cost) AS total_cost
                                            FROM card
                                            WHERE date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
                                            GROUP BY reason
                                     """)

    negative_sum = 0
    total_sum = 0
    
    try:
        if not df_negative.empty:
            negative_sum = df_negative['total_cost'].sum()
            
        if not df_all.empty:
            total_sum = df_all['total_cost'].sum()

    except (IndexError, KeyError, Exception) as e:
        st.error(f"데이터 처리 오류: {e}")
        return

    # 기본 낭비율 계산
    negative_percent = (negative_sum / total_sum) * 100 if total_sum > 0 else 0

    # --- [4. 조건별 상태 설정] ---
    
    # [조건 A] 예산 미입력 (Default 0)
    if monthly_budget == 0:
        img_path = './images/0-궁금.png'
        bg_color = "#E3F2FD" # 하늘색
        status_text = "훈련생! 이번 달 예산을 설정하지 않았군.<br>좌측 사이드바에 예산을 입력하게!"

    # [조건 A'] 예산이 너무 적을 때 (0 ~ 10,000원 미만)
    elif 0 < monthly_budget < 10000:
        img_path = './images/6-어이없음.png'
        bg_color = "#FFE0B2"
        status_text = f"자네 지금 장난하나? {monthly_budget}원으론 <br>돈까스도 못 사 먹네.<br><b>최소 10,000원 이상</b>으로 현실적인 예산을 설정하게!"

    # [조건 B] 예산이 정상적으로 설정되었을 때 (10,000원 이상) -> 예산 소진율 기준 평가
    else:
        budget_usage_rate = (total_sum / monthly_budget) * 100
        
        if budget_usage_rate <= 30:
            img_path, bg_color = './images/1-온화.png', "#D4EDDA"
            status_text = f"예산의 {budget_usage_rate:.1f}%만 사용했군.<br>아주 훌륭해! 이 페이스를 유지하게. 😊"
        elif budget_usage_rate <= 60:
            img_path, bg_color = './images/2-걱정.png', "#FFF3CD"
            status_text = f"벌써 예산의 {budget_usage_rate:.1f}% 을 썼네.<br>지출 속도를 조금 늦추는 게 좋겠어. 😟"
        elif budget_usage_rate <= 90:
            img_path, bg_color = './images/3-짜증.png', "#F8D7DA"
            status_text = f"비상! 예산이 거의 바닥났어({budget_usage_rate:.1f}%)!<br>이제부터는 숨만 쉬고 살게! 😠"
        else:
            img_path, bg_color = './images/4-화남.png', "#F8D7DA"
            status_text = f"곧 예산 초과다!!<br>훈련생, 자네는 계획이란 게 없나?! 😡"

    # --- [5. 메인 레이아웃 구성] ---
    
    # 박스 스타일 함수
    def info_box(label, value, color="black", bg_color="white", height="auto"):
        return f"""
        <div style="
            background-color: {bg_color}; 
            padding: 10px; 
            border-radius: 8px; 
            text-align: center; 
            box-shadow: 0px 1px 2px rgba(0,0,0,0.1);
            border: 1px solid #eee;
            margin-bottom: 8px;
            height: {height};
            display: flex;
            flex-direction: column;
            justify-content: center;
            "> 
            <p style="font-size: 12px; color: #888; margin: 0;">{label}</p>
            <p style="font-size: 16px; font-weight: bold; color: {color}; margin: 2px 0 0 0;">{value}</p>
        </div>
        """

    # --- [Top Section] 교관(좌) + 기본 정보(우, 세로 스택) ---
    top_left, top_right = st.columns([3, 1])

    # [좌측] 교관 이미지 + 말풍선
    with top_left:
        st.markdown("#### 📢 교관의 한마디")
        sub_img, sub_bubble = st.columns([1.8, 2.5])
        
        with sub_img:
            try:
                st.image(img_path, use_container_width=True)
            except:
                st.write("😐")
        
        with sub_bubble:
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

    # [우측] 기본 정보 3개 (세로 스택 - 항상 표시)
    with top_right:
        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True) # 높이 맞춤용
        st.markdown(info_box("이번 달 전체 소비", f"{total_sum:,.0f}원"), unsafe_allow_html=True)
        st.markdown(info_box("이번 달 낭비 소비", f"{negative_sum:,.0f}원", "#dc3545"), unsafe_allow_html=True)
        st.markdown(info_box("훈련생의 낭비율", f"{negative_percent:.1f}%", "#dc3545"), unsafe_allow_html=True)

    # --- [Bottom Section] 예산 상세 정보 (1행 3열) ---
    # 예산이 정상적으로 설정되었을 때만 표시
    if monthly_budget >= 10000:
        st.markdown("<br>", unsafe_allow_html=True) # 간격 추가
        st.markdown("##### 📊 예산 상세 분석")
        
        budget_usage_rate = (total_sum / monthly_budget) * 100
        waste_budget_rate = (negative_sum / monthly_budget) * 100
        remaining_budget = monthly_budget - total_sum
        
        # 3개의 컬럼으로 분할
        b_col1, b_col2, b_col3 = st.columns(3)
        
        with b_col1:
            usage_color = "#dc3545" if budget_usage_rate > 100 else "#007bff"
            st.markdown(info_box("예산 소진율", f"{budget_usage_rate:.1f}%", color=usage_color, bg_color="#f8f9fa"), unsafe_allow_html=True)
            
        with b_col2:
            st.markdown(info_box("예산 잠식률 (낭비/예산)", f"{waste_budget_rate:.1f}%", color="#dc3545", bg_color="#f8f9fa"), unsafe_allow_html=True)
            
        with b_col3:
            remain_color = "black" if remaining_budget >= 0 else "#dc3545"
            st.markdown(info_box("남은 예산 (잔액)", f"{remaining_budget:,.0f}원", color=remain_color, bg_color="#f8f9fa"), unsafe_allow_html=True)

if __name__ == "__main__":
    main()