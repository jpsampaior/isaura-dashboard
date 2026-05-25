"""
BI — Gestão de Incidentes (ITIL)
Atividade Prática conforme AtivPratica - Bi de Incidentes.pdf

ETL → Tabela Fato (1 linha/incidente) + D_Calendario → Dashboard com 4 filtros, 4 KPIs e 4 gráficos.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

PRIORITY_ORDER = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]

from etl_core import run_etl as _run_etl_core


@st.cache_data
def run_etl() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Retorna tabela fato, dimensão calendário e metadados do ETL."""
    fato, d_cal_base, meta = _run_etl_core()
    d_cal = d_cal_base.copy()
    d_cal["ano"] = d_cal["data"].dt.year
    d_cal["mes"] = d_cal["data"].dt.month
    d_cal["mes_nome"] = d_cal["data"].dt.strftime("%b/%Y")
    d_cal["trimestre"] = d_cal["data"].dt.to_period("Q").astype(str)
    meta["estrategia_resolucao"] = (
        "Chamados Resolved/Closed sem resolved_at foram preenchidos com closed_at "
        "(todos os casos possuíam closed_at)."
    )
    return fato, d_cal, meta


def filter_fato(fato: pd.DataFrame, d_cal: pd.DataFrame) -> pd.DataFrame:
    df = fato.copy()

    min_d = d_cal["data"].min().date()
    max_d = d_cal["data"].max().date()
    periodo = st.sidebar.date_input(
        "Período (D_Calendario)",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )
    if isinstance(periodo, tuple) and len(periodo) == 2:
        ini, fim = periodo
        df = df[
            (df["data_abertura"] >= pd.Timestamp(ini))
            & (df["data_abertura"] <= pd.Timestamp(fim) + pd.Timedelta(days=1))
        ]

    prioridades = st.sidebar.multiselect(
        "Prioridade",
        PRIORITY_ORDER,
        default=[],
    )
    if prioridades:
        df = df[df["priority"].isin(prioridades)]

    equipes = sorted(df["assignment_group"].dropna().unique())
    equipes_sel = st.sidebar.multiselect("Equipe responsável", equipes, default=[])
    if equipes_sel:
        df = df[df["assignment_group"].isin(equipes_sel)]

    status_opts = sorted(fato["incident_state"].dropna().unique())
    status_sel = st.sidebar.multiselect("Status do chamado", status_opts, default=[])
    if status_sel:
        df = df[df["incident_state"].isin(status_sel)]

    return df


# --- KPIs (seção 4B) --------------------------------------------------------

def show_kpis(df: pd.DataFrame) -> None:
    volume = df["number"].nunique()
    mttr = df["mttr_horas"].mean()
    sla_pct = df["made_sla"].mean() * 100 if df["made_sla"].notna().any() else 0
    criticos = (df["priority"] == "1 - Critical").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volume total de chamados", f"{volume:,}")
    c2.metric(
        "MTTR (tempo médio de atendimento)",
        f"{mttr:.1f} h" if pd.notna(mttr) else "—",
        help="Média de (resolved_at − opened_at) em horas.",
    )
    c3.metric("Taxa de conformidade SLA", f"{sla_pct:.1f}%")
    c4.metric("Chamados críticos", f"{criticos:,}")


# --- Gráficos (seção 4C) ----------------------------------------------------

def chart_evolucao_aberturas(df: pd.DataFrame) -> None:
    serie = (
        df.dropna(subset=["opened_at"])
        .assign(mes=lambda x: x["opened_at"].dt.to_period("M").astype(str))
        .groupby("mes", as_index=False)
        .agg(aberturas=("number", "nunique"))
        .sort_values("mes")
    )
    fig = px.area(
        serie,
        x="mes",
        y="aberturas",
        title="Gráfico 1 — Evolução temporal de aberturas",
        labels={"mes": "Mês", "aberturas": "Chamados abertos"},
        markers=True,
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_top_sintomas(df: pd.DataFrame) -> None:
    top = (
        df["u_symptom"]
        .dropna()
        .value_counts()
        .head(10)
        .reset_index()
    )
    top.columns = ["Sintoma", "Volume"]
    fig = px.bar(
        top,
        x="Volume",
        y="Sintoma",
        orientation="h",
        title="Gráfico 2 — Top 10 sintomas mais recorrentes",
        labels={"Volume": "Chamados", "Sintoma": ""},
    )
    fig.update_layout(
        yaxis=dict(categoryorder="total ascending"),
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_prioridade(df: pd.DataFrame) -> None:
    dist = df["priority"].value_counts().reindex(PRIORITY_ORDER, fill_value=0)
    dist = dist.reset_index()
    dist.columns = ["Prioridade", "Quantidade"]
    fig = px.pie(
        dist,
        names="Prioridade",
        values="Quantidade",
        hole=0.45,
        title="Gráfico 3 — Distribuição por faixa de prioridade",
        color="Prioridade",
        color_discrete_map={
            "1 - Critical": "#c0392b",
            "2 - High": "#e67e22",
            "3 - Moderate": "#3498db",
            "4 - Low": "#95a5a6",
        },
    )
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)


def chart_equipe_desempenho(df: pd.DataFrame) -> None:
    equipe = (
        df.dropna(subset=["assignment_group"])
        .groupby("assignment_group", as_index=False)
        .agg(
            volume=("number", "count"),
            mttr_horas=("mttr_horas", "mean"),
        )
        .sort_values("volume", ascending=False)
        .head(15)
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=equipe["assignment_group"],
            y=equipe["volume"],
            name="Volume resolvido",
            marker_color="#2c3e50",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=equipe["assignment_group"],
            y=equipe["mttr_horas"],
            name="MTTR (h)",
            mode="lines+markers",
            line=dict(color="#e74c3c", width=2),
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title="Gráfico 4 — Carga de trabalho e MTTR por equipe",
        xaxis_title="Equipe",
        margin=dict(l=20, r=20, t=50, b=80),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(title_text="Volume", secondary_y=False)
    fig.update_yaxes(title_text="MTTR (horas)", secondary_y=True)
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


def prepare_table_view(df: pd.DataFrame) -> pd.DataFrame:
    """Formata a tabela fato filtrada para exibição."""
    view = df.copy()
    if "opened_at" in view.columns:
        view = view.sort_values("opened_at", ascending=False, na_position="last")
    for col in ["opened_at", "resolved_at", "closed_at"]:
        if col in view.columns:
            view[col] = view[col].dt.strftime("%d/%m/%Y %H:%M")
    if "data_abertura" in view.columns:
        view["data_abertura"] = view["data_abertura"].dt.strftime("%d/%m/%Y")
    if "mttr_horas" in view.columns:
        view["mttr_horas"] = view["mttr_horas"].round(2)
    return view


def show_data_table(df: pd.DataFrame) -> None:
    st.subheader("Dados após limpeza (ETL)")
    st.caption(
        f"{len(df):,} chamados exibidos · mesmos filtros do painel · "
        "1 linha por incidente (estado final)"
    )
    st.dataframe(
        prepare_table_view(df),
        use_container_width=True,
        height=420,
        hide_index=True,
    )


# --- App --------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="BI — Gestão de Incidentes",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; }
        h1 { font-weight: 600; letter-spacing: -0.02em; }
        [data-testid="stMetricValue"] { font-size: 1.6rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("BI — Gestão de Incidentes (ITIL)")
    st.caption(
        "Painel estratégico para diretoria de TI · "
        "Base: incident_event_log.csv · Tabela fato (estado final por chamado)"
    )

    fato, d_cal, meta = run_etl()

    with st.expander("ETL aplicado (relatório de engenharia)"):
        st.markdown(
            f"""
            | Etapa | Ação |
            |-------|------|
            | Tratamento de `?` | Substituído por nulo em `resolved_at`, `assignment_group`, `u_symptom` |
            | Inconsistência de resolução | {meta['estrategia_resolucao']} |
            | Registros corrigidos | **{meta['preenchidos_closed_at']:,}** chamados |
            | Deduplicação | 1 linha por `number` com maior `sys_mod_count` |
            | D_Calendario | {len(d_cal):,} dias ({d_cal['data'].min().date()} a {d_cal['data'].max().date()}) |
            | Log bruto → Fato | {meta['linhas_log']:,} linhas → **{meta['chamados_unicos']:,}** chamados |
            """
        )

    st.sidebar.header("Filtros principais")
    df = filter_fato(fato, d_cal)

    if df.empty:
        st.warning("Nenhum chamado corresponde aos filtros selecionados.")
        return

    st.subheader("KPIs")
    show_kpis(df)
    st.divider()
    st.subheader("Análises estratégicas")

    r1c1, r1c2 = st.columns(2)
    with r1c1:
        chart_evolucao_aberturas(df)
    with r1c2:
        chart_prioridade(df)

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        chart_top_sintomas(df)
    with r2c2:
        chart_equipe_desempenho(df)

    st.divider()
    show_data_table(df)


if __name__ == "__main__":
    main()
