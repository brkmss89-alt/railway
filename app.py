
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# analysis_result.csv를 app_05.py와 같은 폴더에 두세요.
# 실행: streamlit run app_05.py
# .py 파일에 직접 붙여 넣는 경우 첫 줄의 %%writefile 명령은 제외하세요.

# ==================================================
# 1. 페이지 설정
# ==================================================
st.set_page_config(
    page_title="철도 데이터 분석 대시보드",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 표에서는 읽기 쉬운 이름으로 표시합니다.
# 다운로드하는 CSV의 원래 열 이름은 유지합니다.
COLUMN_CONFIG = {
    "측정시각": st.column_config.DatetimeColumn(
        "측정 시각",
        format="YYYY-MM-DD HH:mm",
    ),
    "목표시각": st.column_config.DatetimeColumn(
        "예측 대상 시각",
        format="YYYY-MM-DD HH:mm",
    ),
    "설비ID": "설비",
    "온도_C": st.column_config.NumberColumn(
        "현재 온도 (℃)", format="%.2f"
    ),
    "진동_mm_s": st.column_config.NumberColumn(
        "진동 (mm/s)", format="%.3f"
    ),
    "전류_A": st.column_config.NumberColumn(
        "전류 (A)", format="%.2f"
    ),
    "다음온도_C": st.column_config.NumberColumn(
        "실제 다음 온도 (℃)", format="%.2f"
    ),
    "AI예측온도_C": st.column_config.NumberColumn(
        "AI 예측 온도 (℃)", format="%.2f"
    ),
    "절대오차_C": st.column_config.NumberColumn(
        "절대오차 (℃)", format="%.2f"
    ),
    "AI결과": "AI 판정",
}


def show_table(data):
    """표의 날짜, 숫자, 표시 이름을 통일합니다."""
    st.dataframe(
        data,
        hide_index=True,
        width="stretch",
        column_config={
            col: config
            for col, config in COLUMN_CONFIG.items()
            if col in data.columns
        },
    )


def show_chart(fig, key):
    """그래프의 글씨, 범례, 크기를 통일합니다."""
    fig.update_layout(
        height=440,
        font=dict(size=15),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=30),
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    fig.update_xaxes(
        tickformat="%m/%d<br>%H:%M",
        title_standoff=15,
    )
    fig.update_yaxes(title_standoff=15)

    st.plotly_chart(
        fig,
        width="stretch",
        key=key,
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )


# ==================================================
# 2. 제목과 데이터 읽기
# ==================================================
st.title("🚆 철도 데이터 분석 대시보드")

st.caption(
    "설비와 기간 선택 → AI 점검후보 확인 → "
    "온도 예측 비교 → 보고서 저장"
)

st.info(
    "교육용 가상 자료입니다. AI 확인후보는 고장 확정이 아닙니다."
)

data_path = Path(__file__).resolve().parent / "analysis_result.csv"

try:
    df = pd.read_csv(data_path, encoding="utf-8-sig")
except (
    OSError,
    UnicodeError,
    pd.errors.ParserError,
    pd.errors.EmptyDataError,
) as exc:
    st.error(f"analysis_result.csv를 읽을 수 없습니다: {exc}")
    st.info("분석 결과 CSV를 app_05.py와 같은 폴더에 넣어주세요.")
    st.stop()

required_columns = [
    "측정시각",
    "설비ID",
    "온도_C",
    "AI결과",
    "목표시각",
    "다음온도_C",
    "AI예측온도_C",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error("필요한 열이 없습니다: " + ", ".join(missing_columns))
    st.info(
        "원본 센서 CSV가 아니라 AI 분석 결과가 포함된 "
        "analysis_result.csv가 필요합니다."
    )
    st.stop()

df["측정시각"] = pd.to_datetime(df["측정시각"], errors="coerce")
df["목표시각"] = pd.to_datetime(df["목표시각"], errors="coerce")

df["설비ID"] = (
    df["설비ID"].astype("string").str.strip().replace("", pd.NA)
)
df["AI결과"] = (
    df["AI결과"].astype("string").str.strip().replace("", pd.NA)
)

# 숫자로 읽을 수 없는 값은 채우지 않고 결측값으로 처리합니다.
invalid_numbers = 0

for col in [
    "온도_C", "다음온도_C", "AI예측온도_C",
    "진동_mm_s", "전류_A",
]:
    if col in df.columns:
        original = df[col]
        converted = pd.to_numeric(original, errors="coerce")
        converted = converted.replace(
            [float("inf"), float("-inf")],
            float("nan"),
        )
        invalid_numbers += int(
            (original.notna() & converted.isna()).sum()
        )
        df[col] = converted

invalid_rows = df["측정시각"].isna() | df["설비ID"].isna()
excluded_rows = int(invalid_rows.sum())

df = (
    df.loc[~invalid_rows]
    .sort_values(["설비ID", "측정시각"])
    .copy()
)

if df.empty:
    st.warning("조회할 수 있는 설비와 측정시각이 없습니다.")
    st.stop()

if excluded_rows:
    st.warning(
        f"설비 또는 측정시각을 확인할 수 없는 "
        f"{excluded_rows:,}행은 제외했습니다."
    )

if invalid_numbers:
    st.warning(
        f"유효한 숫자로 읽을 수 없는 값 "
        f"{invalid_numbers:,}개를 결측값으로 처리했습니다."
    )


# ==================================================
# 3. 사이드바: 설비와 조회 기간 선택
# ==================================================
with st.sidebar:
    st.header("⚙️ 조회 조건")
    st.caption("선택한 조건은 모든 탭에 동일하게 적용됩니다.")

    equipment = st.selectbox(
        "설비 선택",
        sorted(df["설비ID"].unique()),
    )

    equipment_view = df.loc[
        df["설비ID"] == equipment
    ].copy()

    min_date = equipment_view["측정시각"].min().date()
    max_date = equipment_view["측정시각"].max().date()

    st.subheader("📅 조회 기간")

    start = st.date_input(
        "시작일",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
        key=f"start_{equipment}_{min_date}_{max_date}",
    )

    end = st.date_input(
        "종료일",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key=f"end_{equipment}_{min_date}_{max_date}",
    )

    if start is None or end is None:
        st.warning("시작일과 종료일을 모두 선택하세요.")
        st.stop()

    if start > end:
        st.error("시작일은 종료일보다 늦을 수 없습니다.")
        st.stop()

    st.divider()

    st.caption(
        f"자료 기간: {min_date:%Y-%m-%d} ~ {max_date:%Y-%m-%d}"
    )
    st.caption(
        "시작일과 종료일을 모두 포함하며, "
        "측정시각을 기준으로 조회합니다."
    )


# ==================================================
# 4. 공통 데이터와 지표 계산
# ==================================================
view = equipment_view.loc[
    (equipment_view["측정시각"].dt.date >= start)
    & (equipment_view["측정시각"].dt.date <= end)
].copy()

if view.empty:
    st.warning("조회 결과가 없습니다. 날짜를 다시 선택하세요.")
    st.stop()

candidates = view.loc[
    view["AI결과"].eq("확인후보").fillna(False)
].copy()

# 기존 코드와 동일하게 실제값과 예측값이 모두 있는 행을 비교합니다.
pred = view.dropna(
    subset=["다음온도_C", "AI예측온도_C"]
).copy()

pred["절대오차_C"] = (
    pred["다음온도_C"] - pred["AI예측온도_C"]
).abs()

mae = pred["절대오차_C"].mean()
max_error = pred["절대오차_C"].max()
max_temperature = view["온도_C"].max()

mae_text = (
    f"{mae:.2f} ℃" if pd.notna(mae) else "자료 없음"
)
max_error_text = (
    f"{max_error:.2f} ℃" if pd.notna(max_error) else "자료 없음"
)
max_temperature_text = (
    f"{max_temperature:.2f} ℃"
    if pd.notna(max_temperature)
    else "자료 없음"
)


# ==================================================
# 5. 상단 요약: 핵심 숫자를 먼저 확인
# ==================================================
st.subheader(f"{equipment} · 조회 요약")
st.caption(
    f"측정시각 기준 {start:%Y-%m-%d} ~ {end:%Y-%m-%d}"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "조회 기록",
    f"{len(view):,}건",
    border=True,
)

col2.metric(
    "AI 확인후보",
    f"{len(candidates):,}건",
    border=True,
    help=(
        "추가 확인 대상으로 표시된 기록 수입니다. "
        "실제 고장 횟수가 아닙니다."
    ),
)

col3.metric(
    "조회 기간 최고 온도",
    max_temperature_text,
    border=True,
)

col4.metric(
    "평균 예측 오차 · MAE",
    mae_text,
    border=True,
    help=(
        "실제 온도와 AI 예측 온도가 평균적으로 "
        "얼마나 차이 났는지 나타냅니다."
    ),
)

st.caption(
    f"예측 오차는 실제값과 예측값이 모두 있는 "
    f"{len(pred):,}건으로 계산했습니다."
)


# ==================================================
# 6. 탭 만들기
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "🔍 AI 점검후보",
    "🌡️ 다음 1시간 온도 예측",
    "📝 업무검토 및 저장",
])


# ==================================================
# 탭 1. AI 점검후보
# ==================================================
with tab1:
    st.subheader("어떤 시점을 확인해야 할까요?")

    if not candidates.empty:
        st.warning(
            f"선택한 기간에 AI 확인후보가 "
            f"{len(candidates):,}건 있습니다. "
            "해당 시각의 센서 상태와 운전 조건을 함께 확인하세요."
        )
    else:
        st.info(
            "선택한 기간에 확인후보로 표시된 기록이 없습니다. "
            "AI 결과가 없는 기록도 있을 수 있으며, "
            "정상 확정을 의미하지 않습니다."
        )

    st.markdown("#### 온도 변화와 확인후보")

    if view["온도_C"].notna().any():
        fig = px.line(
            view,
            x="측정시각",
            y="온도_C",
            markers=len(view) <= 48,
            labels={
                "측정시각": "측정 시각",
                "온도_C": "온도 (℃)",
            },
        )

        fig.update_traces(
            name="측정 온도",
            showlegend=True,
            line=dict(color="#2563EB", width=2.5),
            connectgaps=False,
            hovertemplate=(
                "%{x|%Y-%m-%d %H:%M}<br>"
                "%{y:.2f} ℃<extra>측정 온도</extra>"
            ),
        )

        visible_candidates = candidates.dropna(
            subset=["온도_C"]
        )

        if not visible_candidates.empty:
            fig.add_scatter(
                x=visible_candidates["측정시각"],
                y=visible_candidates["온도_C"],
                mode="markers",
                name="AI 확인후보",
                marker=dict(
                    color="#C2410C",
                    size=12,
                    symbol="diamond",
                ),
                hovertemplate=(
                    "%{x|%Y-%m-%d %H:%M}<br>"
                    "%{y:.2f} ℃<extra>AI 확인후보</extra>"
                ),
            )

        show_chart(fig, "anomaly_chart")

        st.caption(
            "선은 측정 온도, 마름모는 AI 확인후보입니다. "
            "그래프에 마우스를 올리면 시각과 온도를 확인할 수 있습니다."
        )

        missing_candidate_temperature = (
            len(candidates) - len(visible_candidates)
        )

        if missing_candidate_temperature:
            st.caption(
                f"온도가 없는 후보 "
                f"{missing_candidate_temperature:,}건은 "
                "그래프에 표시하지 않고 아래 목록에만 포함했습니다."
            )

    else:
        st.info(
            "온도값이 없어 그래프를 표시할 수 없습니다. "
            "후보 목록은 확인할 수 있습니다."
        )

    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### 확인후보 상세 목록")

        if candidates.empty:
            st.write("표시할 확인후보가 없습니다.")
        else:
            candidate_columns = [
                col
                for col in [
                    "측정시각", "온도_C",
                    "진동_mm_s", "전류_A", "AI결과",
                ]
                if col in candidates.columns
            ]
            show_table(candidates[candidate_columns])

    with right:
        st.markdown("#### AI 판정별 기록 수")

        result_counts = (
            view["AI결과"]
            .fillna("결과 없음")
            .value_counts()
            .rename_axis("AI 판정")
            .reset_index(name="건수")
        )

        show_table(result_counts)

        st.caption(
            "모델미탐지는 정상 보증이 아니며, "
            "결과 없음은 판정값이 없는 기록입니다."
        )


# ==================================================
# 탭 2. 다음 1시간 온도 예측
# ==================================================
with tab2:
    st.subheader("AI 예측은 실제 온도와 얼마나 달랐을까요?")

    st.caption(
        "CSV에 저장된 실제 다음 온도와 AI 예측을 비교합니다. "
        "새로 미래를 예측하는 화면은 아닙니다."
    )

    if pred.empty:
        st.info(
            "선택한 기간에는 실제 온도와 AI 예측 온도를 "
            "함께 비교할 자료가 없습니다."
        )

    else:
        st.info(
            f"{len(pred):,}건을 비교한 결과, "
            f"평균 절대오차는 {mae:.2f} ℃, "
            f"가장 큰 절대오차는 {max_error:.2f} ℃입니다."
        )

        st.caption(
            "평균 오차가 작더라도 특정 시점의 오차는 클 수 있으므로 "
            "아래 상세 기록도 확인하세요."
        )

        plot_pred = (
            pred.dropna(subset=["목표시각"])
            .sort_values("목표시각")
        )

        if plot_pred.empty:
            st.warning(
                "예측 대상 시각이 없어 그래프를 표시할 수 없습니다. "
                "오차 계산과 표는 확인할 수 있습니다."
            )

        else:
            graph_data = plot_pred.rename(
                columns={
                    "다음온도_C": "실제 온도",
                    "AI예측온도_C": "AI 예측 온도",
                }
            )

            fig2 = px.line(
                graph_data,
                x="목표시각",
                y=["실제 온도", "AI 예측 온도"],
                markers=len(graph_data) <= 48,
                color_discrete_map={
                    "실제 온도": "#2563EB",
                    "AI 예측 온도": "#C2410C",
                },
                labels={
                    "목표시각": "예측 대상 시각",
                    "value": "온도 (℃)",
                    "variable": "구분",
                },
            )

            # 색뿐 아니라 선 모양으로도 실제값과 예측값을 구분합니다.
            for trace in fig2.data:
                trace.update(
                    line=dict(
                        width=2.5,
                        dash=(
                            "dash"
                            if trace.name == "AI 예측 온도"
                            else "solid"
                        ),
                    ),
                    hovertemplate=(
                        "%{x|%Y-%m-%d %H:%M}<br>"
                        "%{y:.2f} ℃"
                        "<extra>%{fullData.name}</extra>"
                    ),
                )

            show_chart(fig2, "prediction_chart")

            st.caption(
                "실선은 실제 온도, 점선은 AI 예측입니다. "
                "두 선의 간격이 넓을수록 예측 오차가 큽니다."
            )

        if len(plot_pred) < len(pred):
            st.caption(
                f"예측 대상 시각이 없는 "
                f"{len(pred) - len(plot_pred):,}건은 "
                "오차 계산에는 포함하고 그래프에서는 제외했습니다."
            )

        st.caption(
            "조회 조건은 측정시각 기준이고, "
            "이 그래프는 목표시각 기준입니다. "
            "다음 시간의 예측 대상 시각은 "
            "조회 종료일 다음 날에 걸칠 수 있습니다."
        )

        st.markdown("#### 오차가 큰 기록부터 확인하기 · 상위 5건")

        prediction_columns = [
            "목표시각",
            "다음온도_C",
            "AI예측온도_C",
            "절대오차_C",
        ]

        show_table(
            pred.nlargest(5, "절대오차_C")[prediction_columns]
        )

        with st.expander("전체 예측 비교 결과 보기"):
            show_table(
                pred.sort_values("목표시각")[prediction_columns]
            )


# ==================================================
# 탭 3. 업무검토 및 저장
# ==================================================
with tab3:
    st.subheader("확인한 내용을 정리하고 저장하세요.")

    memo_column, report_column = st.columns([1, 1.3])

    with memo_column:
        st.markdown("#### 업무 검토 메모")

        with st.form("review_form"):
            note = st.text_area(
                "확인할 사항 및 조치 제안",
                value=(
                    "센서 상태와 운전 조건을 확인한 후 "
                    "담당자 검토가 필요합니다."
                ),
                height=200,
                key=f"note_{equipment}_{start}_{end}",
            )

            st.form_submit_button(
                "메모를 보고서에 반영",
                type="primary",
            )

        st.caption(
            "메모를 수정한 뒤 위 버튼을 누르면 보고서에 반영됩니다."
        )

    report = f"""철도 데이터 분석 보고서
================================

[분석 대상]
설비: {equipment}
조회 기간: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}
조회 기준: 측정시각, 시작일·종료일 포함

[조회 요약]
조회 기록: {len(view):,}건
AI 확인후보: {len(candidates):,}건
조회 기간 최고 온도: {max_temperature_text}

[다음 1시간 온도 예측 비교]
비교 자료: {len(pred):,}건
평균 절대오차(MAE): {mae_text}
최대 절대오차: {max_error_text}
예측 대상 시각은 조회 종료일 다음 날에 걸칠 수 있습니다.

[업무 검토 메모]
{note}

[유의사항]
교육용 가상 자료입니다.
AI 확인후보는 실제 고장 확정이 아닙니다.
모델미탐지도 정상 확정을 의미하지 않습니다.
예측 비교는 CSV에 저장된 실제값과 예측값을 사용합니다.
"""

    with report_column:
        st.markdown("#### 보고서 미리보기")

        with st.container(border=True):
            st.text(report)

    st.divider()
    st.markdown("#### 현재 조회 결과 내려받기")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label="📥 조회 결과 CSV",
            data=view.to_csv(index=False).encode("utf-8-sig"),
            file_name="dashboard_result.csv",
            mime="text/csv",
            width="stretch",
        )

    with col2:
        st.download_button(
            label="📥 점검 후보 CSV",
            data=candidates.to_csv(index=False).encode("utf-8-sig"),
            file_name="inspection_candidates.csv",
            mime="text/csv",
            width="stretch",
        )

    with col3:
        st.download_button(
            label="📥 보고서 TXT",
            data=report.encode("utf-8-sig"),
            file_name="dashboard_report.txt",
            mime="text/plain",
            width="stretch",
        )

    st.caption(
        "파일에는 현재 선택한 설비와 기간의 조회 결과만 포함됩니다."
    )


# ==================================================
# 7. 전체 조회 데이터: 필요할 때 펼쳐서 확인
# ==================================================
st.divider()

with st.expander(f"전체 조회 데이터 보기 · {len(view):,}건"):
    show_table(view)
