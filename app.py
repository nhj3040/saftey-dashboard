import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 페이지 기본 설정
st.set_page_config(page_title="안전동행자금 수주 현황 대시보드", layout="wide")

st.title("🛡️ 안전동행자금 수주 현황 대시보드")

# 2. 열 이름 유연한 자동 검색 함수
def find_col(df, keywords):
    for c in df.columns:
        clean_c = str(c).replace(' ', '').replace('_', '').replace('\x0d', '').lower()
        if any(kw in clean_c for kw in keywords):
            return c
    return None

# 3. 대표 기종명 파싱 함수 (지정 항목 외 모두 '기타' 처리)
def extract_rep_model(model_str):
    if pd.isna(model_str):
        return "기타"

    m_str = str(model_str).strip()
    m_upper = m_str.upper()

    if any(m_kw in m_upper for m_kw in ['M1', 'M2', 'M3', 'M4']):
        return 'M series'

    if 'VESTA-1100' in m_upper or 'VESTA 1100' in m_upper:
        return 'VESTA-1100'
    elif 'VESTA-1300' in m_upper or 'VESTA 1300' in m_upper:
        return 'VESTA-1300'
    elif 'VESTA' in m_upper:
        return 'VESTA series'

    if 'SIRIUS-UL+' in m_upper or 'SIRIUS UL+' in m_upper or 'SIRIUS-UL' in m_upper:
        return 'SIRIUS-UL+'
    elif 'SIRIUS' in m_upper:
        return 'SIRIUS series'

    if 'HI-TECH 230' in m_upper or 'HITECH 230' in m_upper:
        return 'Hi-TECH 230'
    elif 'HI-TECH 200' in m_upper or 'HITECH 200' in m_upper:
        return 'Hi-TECH 200'
    elif 'HI-TECH' in m_upper or 'HITECH' in m_upper:
        return 'Hi-TECH series'

    if 'D2-5AX' in m_upper:
        return 'D2-5AX'

    return '기타'

# 4. 파일 업로드 및 데이터 처리
uploaded_file = st.sidebar.file_uploader("영업 수주 엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name=0)
    df.columns = df.columns.astype(str).str.replace('\r', '').str.replace('\n', '').str.strip()

    df = df.dropna(subset=['기종명']).copy()

    delivery_col = find_col(df, ['변경납기', '납기일', '납기'])
    ship_col = find_col(df, ['출하계획', '출하일', '실출하', '출하'])

    df['대수'] = pd.to_numeric(df['대수'], errors='coerce').fillna(1)
    df['수주금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0)
    df['수주일_dt'] = pd.to_datetime(df['수주일'], errors='coerce')

    df = df[df['수주일_dt'].dt.year != 2025].copy()

    df['수주월'] = df['수주일_dt'].dt.strftime('%Y-%m')
    df['대표기종'] = df['기종명'].apply(extract_rep_model)

    if '사용자금' in df.columns:
        df['사용자금_clean'] = df['사용자금'].astype(str).str.replace(' ', '')
        df_safe_all = df[df['사용자금_clean'].str.contains('안전동행', na=False)].copy()
    else:
        df_safe_all = df.copy()

    if delivery_col:
        df_safe_all['납기일_dt'] = pd.to_datetime(df_safe_all[delivery_col], errors='coerce')
        df_safe_all = df_safe_all[df_safe_all['납기일_dt'].dt.year != 2025].copy()
        df_safe_all['납기월'] = df_safe_all['납기일_dt'].dt.strftime('%Y-%m')
    else:
        df_safe_all['납기월'] = '미정'

    if ship_col:
        df_safe_all['출하일_dt'] = pd.to_datetime(df_safe_all[ship_col], errors='coerce')
        df_safe_all['출하월'] = df_safe_all['출하일_dt'].dt.strftime('%Y-%m')
    else:
        df_safe_all['출하월'] = '미정'

    if delivery_col and ship_col:
        df_safe_all['지연일수'] = (df_safe_all['출하일_dt'] - df_safe_all['납기일_dt']).dt.days
        df_safe_all['납기연기여부'] = df_safe_all['지연일수'] > 0
    else:
        df_safe_all['지연일수'] = 0
        df_safe_all['납기연기여부'] = False

    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 조회 월 선택")
    available_months = ["전체 (All)"] + sorted(list(df_safe_all['수주월'].dropna().unique()))
    selected_month = st.sidebar.selectbox("조회할 수주월을 선택하세요:", available_months)

    if selected_month == "전체 (All)":
        df_safe = df_safe_all.copy()
        df_total_ref = df.copy()
    else:
        df_safe = df_safe_all[df_safe_all['수주월'] == selected_month].copy()
        df_total_ref = df[df['수주월'] == selected_month].copy()

    total_qty = df_total_ref['대수'].sum()
    total_amt = df_total_ref['수주금액'].sum()
    safe_qty = df_safe['대수'].sum()
    safe_amt = df_safe['수주금액'].sum()

    delayed_qty = df_safe[df_safe['납기연기여부']]['대수'].sum()
    delay_ratio = (delayed_qty / safe_qty * 100) if safe_qty > 0 else 0

    # 메인 UI 요약
    st.subheader("📌 안전동행 수주 요약")

    col_qty, col_amt = st.columns([2, 3])

    with col_qty:
        st.markdown("##### 📦 수주 대수 현황")
        q1, q2 = st.columns(2)
        q1.metric("전체 수주 대수", f"{int(total_qty):,} 대")
        q2.metric("안전동행 수주 대수", f"{int(safe_qty):,} 대")

    with col_amt:
        st.markdown("##### 💰 수주 금액 현황")
        a1, a2, a3 = st.columns(3)
        a1.metric("전체 수주 금액", f"{total_amt/1e8:,.2f} 억원")
        a2.metric("안전동행 수주 금액", f"{safe_amt/1e8:,.2f} 억원")
        a3.metric("안전동행 금액 비율", f"{(safe_amt/total_amt*100):.1f} %" if total_amt > 0 else "0.0 %")

    st.markdown("---")

    # 1️⃣ 월별 전체 수주 대수 vs 안전동행 수주 대수 비교 (위치 변경)
    st.subheader("1️⃣ 월별 전체 수주 대수 vs 안전동행 수주 대수 비교")
    tot_m = df.groupby('수주월')['대수'].sum().reset_index().rename(columns={'대수': '전체수주대수'})
    safe_m = df_safe_all.groupby('수주월')['대수'].sum().reset_index().rename(columns={'대수': '안전동행대수'})

    m_compare = pd.merge(tot_m, safe_m, on='수주월', how='outer').fillna(0).sort_values('수주월')
    m_compare['전체수주대수'] = m_compare['전체수주대수'].astype(int)
    m_compare['안전동행대수'] = m_compare['안전동행대수'].astype(int)
    m_compare['안전동행비중(%)'] = (m_compare['안전동행대수'] / m_compare['전체수주대수'] * 100).round(1)

    col_c1, col_c2 = st.columns([5, 5])

    with col_c1:
        st.markdown("**월별 수주 대수 비교**")
        disp_m_compare = m_compare.copy()
        disp_m_compare.columns = ['수주월', '전체 수주 대수', '안전동행 대수', '안전동행 비중 (%)']
        st.dataframe(disp_m_compare, use_container_width=True, hide_index=True)

    with col_c2:
        st.markdown("**월별 전체 수주 대비 안전동행**")
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(x=m_compare['수주월'], y=m_compare['전체수주대수'], name='전체 수주 대수', marker_color='#90a4ae'))
        fig_comp.add_trace(go.Bar(x=m_compare['수주월'], y=m_compare['안전동행대수'], name='안전동행 대수', marker_color='#1e88e5'))
        fig_comp.update_layout(barmode='group', height=300, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="수주월", yaxis_title="대수")
        st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")

    # 2️⃣ 대표 기종별 금액 및 대수 현황 (위치 변경)
    st.subheader("2️⃣ 대표 기종별 금액 및 대수 현황")

    model_summary = df_safe.groupby('대표기종').agg({'대수': 'sum', '수주금액': 'sum'}).reset_index().sort_values(by='대수', ascending=False)
    model_summary['금액_억원'] = (model_summary['수주금액'] / 1e8).round(2)

    col_m_tbl, col_m_fig = st.columns([4, 6])

    with col_m_tbl:
        st.markdown("**기종별 상세 집계표**")
        disp_model = model_summary[['대표기종', '대수', '금액_억원']].copy()
        disp_model['대수'] = disp_model['대수'].astype(int)
        disp_model.columns = ['대표 기종', '수주 대수(대)', '수주 금액(억원)']
        st.dataframe(disp_model, use_container_width=True, hide_index=True)

    with col_m_fig:
        st.markdown("**대표 기종별 금액(막대) & 대수(선) 복합 차트**")
        fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
        fig_combo.add_trace(
            go.Bar(
                x=model_summary['대표기종'],
                y=model_summary['금액_억원'],
                name="수주 금액(억원)",
                marker_color="#3366cc",
                text=model_summary['금액_억원'].apply(lambda x: f"{x:.1f}억"),
                textposition="auto"
            ),
            secondary_y=False
        )
        fig_combo.add_trace(
            go.Scatter(
                x=model_summary['대표기종'],
                y=model_summary['대수'],
                name="수주 대수(대)",
                mode="lines+markers+text",
                line=dict(color="#ff9900", width=3),
                marker=dict(size=8),
                text=model_summary['대수'].astype(int).astype(str) + "대",
                textposition="top center"
            ),
            secondary_y=True
        )
        fig_combo.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_combo.update_yaxes(title_text="수주 금액 (억원)", secondary_y=False)
        fig_combo.update_yaxes(title_text="수주 대수 (대)", secondary_y=True)
        st.plotly_chart(fig_combo, use_container_width=True)

    st.markdown("---")

    # 3️⃣ 납기 대비 출하 지연 분석
    st.subheader("3️⃣ 납기일 대비 출하 계획 지연(연기) 분석")
    st.caption(f"※ 매핑 컬럼: 납기일 (`{delivery_col}`) / 출하일 (`{ship_col}`)")

    # 지연 현황 상단 요약 카드
    col_del_kpi1, col_del_kpi2, col_del_kpi3 = st.columns(3)
    col_del_kpi1.metric("🛡️ 수주 대수", f"{int(safe_qty):,} 대")
    col_del_kpi2.metric("⚠️ 납기 대비 출하 연기 대수", f"{int(delayed_qty):,} 대")
    col_del_kpi3.metric("📊 납기 연기 비율", f"{delay_ratio:.1f} %")

    st.markdown(" ")

    # 금액 기준 집계로 변경
    delay_summary = df_safe.groupby('납기월').agg(
        납기예정대수=('대수', 'sum'),
        출하연기대수=('납기연기여부', lambda x: df_safe.loc[x.index[x], '대수'].sum()),
        납기예정금액=('수주금액', 'sum'),
        출하연기금액=('납기연기여부', lambda x: df_safe.loc[x.index[x], '수주금액'].sum())
    ).reset_index()

    delay_summary['납기 예정 금액(억원)'] = (delay_summary['납기예정금액'] / 1e8).round(2)
    delay_summary['출하 연기 금액(억원)'] = (delay_summary['출하연기금액'] / 1e8).round(2)

    col_d_tb, col_d_ch = st.columns([6, 4])

    with col_d_tb:
        st.markdown("**납기월별 출하 연기 집계표**")
        disp_delay = delay_summary[['납기월', '납기예정대수', '출하연기대수', '납기 예정 금액(억원)', '출하 연기 금액(억원)']].copy()
        disp_delay.columns = ['납기월', '납기 예정 대수', '출하 연기 대수', '납기 예정 금액(억원)', '출하 연기 금액(억원)']
        st.dataframe(disp_delay, use_container_width=True, hide_index=True)

    with col_d_ch:
        st.markdown("**납기월별 정상 출하 vs 연기 대수**")
        fig_delay = go.Figure()
        fig_delay.add_trace(go.Bar(
            x=delay_summary['납기월'], y=delay_summary['납기예정대수'] - delay_summary['출하연기대수'],
            name='정상/조기 출하', marker_color='#2ca02c'
        ))
        fig_delay.add_trace(go.Bar(
            x=delay_summary['납기월'], y=delay_summary['출하연기대수'],
            name='납기 연기 대수', marker_color='#d9534f'
        ))
        fig_delay.update_layout(barmode='stack', height=300, margin=dict(l=20, r=20, t=30, b=20), xaxis_title="납기월", yaxis_title="대수")
        st.plotly_chart(fig_delay, use_container_width=True)

else:
    st.info("👈 좌측 사이드바에서 엑셀 파일을 업로드해주세요.")
