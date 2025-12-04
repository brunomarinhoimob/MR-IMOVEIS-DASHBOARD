import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date
from app_dashboard import carregar_dados_planilha


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def mes_ano_ptbr_para_date(texto: str):
    """Converte 'novembro 2025' -> date(2025, 11, 1)."""
    if not isinstance(texto, str):
        return pd.NaT
    t = texto.strip().lower()
    partes = t.split()
    if len(partes) != 2:
        return pd.NaT
    mes_nome, ano_str = partes
    mapa = {
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }
    mes = mapa.get(mes_nome)
    if not mes:
        return pd.NaT
    try:
        return date(int(ano_str), mes, 1)
    except Exception:
        return pd.NaT


def conta_analises_base(s: pd.Series) -> int:
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(s: pd.Series) -> int:
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(s: pd.Series) -> int:
    return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame, status_venda=None) -> pd.DataFrame:
    """
    Retorna, no máximo, 1 venda por cliente (último status no tempo).
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA", "VENDA INFORMADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df2 = df_scope[s.isin([x.upper() for x in status_venda])].copy()
    if df2.empty:
        return df2

    if "NOME_CLIENTE_BASE" not in df2.columns:
        df2["NOME_CLIENTE_BASE"] = (
            df2.get("CLIENTE", "")
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    if "CPF_CLIENTE_BASE" not in df2.columns:
        df2["CPF_CLIENTE_BASE"] = ""

    df2["CHAVE_CLIENTE"] = (
        df2["NOME_CLIENTE_BASE"].astype(str).str.upper().str.strip()
        + " | "
        + df2["CPF_CLIENTE_BASE"].astype(str).str.strip()
    )

    if "DIA" in df2.columns:
        df2 = df2.sort_values("DIA")

    return df2.groupby("CHAVE_CLIENTE").tail(1).copy()


def format_currency(v) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# ---------------------------------------------------------
# CONFIG DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil do Corretor",
    page_icon="🧑‍💼",
    layout="wide",
)

st.title("🧑‍💼 Funil Individual do Corretor")
st.caption(
    "Análises, aprovações, vendas, meta e acompanhamento por período + DATA BASE."
)


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df = carregar_dados_planilha()
if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# DATA BASE
if "DATA BASE" in df.columns:
    df["DATA_BASE"] = df["DATA BASE"].astype(str).apply(mes_ano_ptbr_para_date)
    df["DATA_BASE_LABEL"] = df["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    df["DATA_BASE"] = df["DIA"]
    df["DATA_BASE_LABEL"] = df["DIA"].dt.strftime("%m/%Y")

# Lista corretores
corretores = sorted(df["CORRETOR"].dropna().astype(str).unique())

st.sidebar.title("Filtros do corretor")
corretor_sel = st.sidebar.selectbox("Selecione o corretor", corretores)

df_cor = df[df["CORRETOR"] == corretor_sel].copy()
if df_cor.empty:
    st.warning("Nenhum dado para esse corretor.")
    st.stop()

# ---------------------------------------------------------
# SELECTOR DATA BASE
# ---------------------------------------------------------
bases_validas = (
    df_cor[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna(subset=["DATA_BASE"])
    .drop_duplicates()
    .sort_values("DATA_BASE")
)

opcoes_bases = bases_validas["DATA_BASE_LABEL"].tolist()
if not opcoes_bases:
    st.warning("Corretor sem DATA BASE definida na planilha.")
    st.stop()

default_bases = opcoes_bases[-2:] if len(opcoes_bases) >= 2 else opcoes_bases

bases_selecionadas = st.sidebar.multiselect(
    "DATA BASE do corretor (mês comercial)",
    options=opcoes_bases,
    default=default_bases,
)

if not bases_selecionadas:
    bases_selecionadas = opcoes_bases

df_periodo = df_cor[df_cor["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()
if df_periodo.empty:
    st.warning("Nenhum registro do corretor nas DATA BASE selecionadas.")
    st.stop()

# Tipo de venda
radio_venda = st.sidebar.radio(
    "Tipo de venda",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA"),
)
if radio_venda == "Só VENDA GERADA":
    status_venda_considerado = ["VENDA GERADA"]
    desc_venda = "apenas VENDA GERADA"
else:
    status_venda_considerado = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_venda = "VENDA GERADA + VENDA INFORMADA"


# ---------------------------------------------------------
# INTERVALO REAL PELOS DIAS DA PLANILHA
# ---------------------------------------------------------
dias_validos = df_periodo["DIA"].dropna()
if not dias_validos.empty:
    data_ini_mov = dias_validos.min().date()
    data_fim_mov = dias_validos.max().date()
else:
    hoje = date.today()
    data_ini_mov = hoje
    data_fim_mov = hoje

if len(bases_selecionadas) == 1:
    base_txt = bases_selecionadas[0]
else:
    base_txt = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"Corretor: **{corretor_sel}** • DATA BASE: **{base_txt}** • "
    f"Dias: **{data_ini_mov.strftime('%d/%m/%Y')}** → **{data_fim_mov.strftime('%d/%m/%Y')}** • "
    f"Vendas consideradas: **{desc_venda}**."
)


# ---------------------------------------------------------
# KPIs DO CORRETOR
# ---------------------------------------------------------
st.markdown("## 📌 Funil do período (corretor)")

status_col = df_periodo["STATUS_BASE"].fillna("").astype(str).str.upper()

analises_em = conta_analises_base(status_col)
reanalises = conta_reanalises(status_col)
aprovacoes = conta_aprovacoes(status_col)

# 🔧 AQUI ESTAVA O ERRO: status_vendas → status_venda
df_vendas = obter_vendas_unicas(
    df_periodo, status_venda=status_venda_considerado
)
vendas = len(df_vendas)
vgv = df_vendas["VGV"].sum() if not df_vendas.empty else 0.0

c1, c2, c3 = st.columns(3)
c1.metric("Análises (EM)", analises_em)
c2.metric("Aprovações", aprovacoes)
c3.metric("Vendas (únicas)", vendas)

c4, c5 = st.columns(2)
c4.metric("Reanálises", reanalises)
c5.metric("VGV total", format_currency(vgv))

st.markdown("---")


# ---------------------------------------------------------
# PLANEJAMENTO (META)
# ---------------------------------------------------------
st.markdown("## 🎯 Planejamento baseado no funil do corretor")

if vendas > 0:
    analises_por_venda = analises_em / vendas if analises_em > 0 else 0.0
    aprovacoes_por_venda = aprovacoes / vendas if aprovacoes > 0 else 0.0

    meta_vendas = st.number_input(
        "Meta de vendas do corretor para o próximo período",
        min_value=0,
        step=1,
        value=vendas,
    )

    if meta_vendas > 0:
        analises_necessarias = int(np.ceil(analises_por_venda * meta_vendas))
        aprovacoes_necessarias = int(np.ceil(aprovacoes_por_venda * meta_vendas))

        m1, m2, m3 = st.columns(3)
        m1.metric("Meta de vendas", meta_vendas)
        m2.metric("Análises necessárias (aprox.)", analises_necessarias)
        m3.metric("Aprovações necessárias (aprox.)", aprovacoes_necessarias)

        st.caption(
            "Cálculos baseados no funil REAL do corretor no período filtrado pela DATA BASE."
        )

        # ---------------------------------------------------------
        # GRÁFICO META x REAL
        # ---------------------------------------------------------
        st.markdown("### 📊 Acompanhamento da meta – corretor")

        indicador = st.selectbox(
            "Indicador para comparar com a meta",
            ["Análises", "Aprovações", "Vendas"],
        )

        periodo_acomp = st.date_input(
            "Período do acompanhamento",
            value=(data_ini_mov, data_fim_mov),
        )
        if isinstance(periodo_acomp, tuple) and len(periodo_acomp) == 2:
            data_ini_sel, data_fim_sel = periodo_acomp
        else:
            data_ini_sel, data_fim_sel = data_ini_mov, data_fim_mov

        if data_ini_sel > data_fim_sel:
            st.error("A data inicial não pode ser maior que a data final.")
        else:
            dr = pd.date_range(start=data_ini_sel, end=data_fim_sel, freq="D")
            dias_meta = [d.date() for d in dr]

            if not dias_meta:
                st.info("Período sem dias válidos para montar o gráfico.")
            else:
                df_periodo["DIA_DATA"] = df_periodo["DIA"].dt.date
                df_range = df_periodo[
                    (df_periodo["DIA_DATA"] >= data_ini_sel)
                    & (df_periodo["DIA_DATA"] <= data_fim_sel)
                ].copy()

                if indicador == "Análises":
                    df_temp = df_range[
                        df_range["STATUS_BASE"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        == "EM ANÁLISE"
                    ].copy()
                    total_meta = analises_necessarias
                elif indicador == "Aprovações":
                    df_temp = df_range[
                        df_range["STATUS_BASE"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        == "APROVADO"
                    ].copy()
                    total_meta = aprovacoes_necessarias
                else:
                    df_temp = obter_vendas_unicas(
                        df_range, status_venda=status_venda_considerado
                    ).copy()
                    total_meta = meta_vendas

                if df_temp.empty or total_meta == 0:
                    st.info(
                        "Não há dados suficientes nesse intervalo ou a meta está zerada "
                        "para o indicador escolhido."
                    )
                else:
                    df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
                    cont_por_dia = (
                        df_temp.groupby("DIA_DATA")
                        .size()
                        .reindex(dias_meta, fill_value=0)
                    )

                    df_line = pd.DataFrame(
                        {"DIA": pd.to_datetime(dias_meta), "Real": cont_por_dia.values}
                    )
                    df_line["Real"] = df_line["Real"].cumsum()

                    # Real para no último dia com movimento
                    ultimo_mov = df_temp["DIA_DATA"].max()
                    if pd.notnull(ultimo_mov):
                        mask_future = df_line["DIA"].dt.date > ultimo_mov
                        df_line.loc[mask_future, "Real"] = np.nan

                    # Meta linear
                    df_line["Meta"] = np.linspace(0, total_meta, len(df_line))

                    df_plot = df_line.melt(
                        "DIA", var_name="Série", value_name="Valor"
                    )

                    chart = (
                        alt.Chart(df_plot)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("DIA:T", title="Dia"),
                            y=alt.Y("Valor:Q", title="Quantidade acumulada"),
                            color=alt.Color("Série:N", title=""),
                        )
                        .properties(height=350)
                    )

                    st.altair_chart(chart, use_container_width=True)
                    st.caption(
                        "Linha **Real** = indicador acumulado do corretor dentro do período escolhido, "
                        "parando no último dia com movimentação. "
                        "Linha **Meta** = ritmo necessário, do início ao fim do intervalo, "
                        "para bater a meta calculada."
                    )
else:
    st.info(
        "Esse corretor ainda não possui vendas no período selecionado, "
        "então não é possível projetar metas com base no funil."
    )
