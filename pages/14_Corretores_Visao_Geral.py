import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

# ------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Corretores – Visão Geral",
    page_icon="🧑‍💼",
    layout="wide",
)

# ------------------------------------------------------------
# LOGO
# ------------------------------------------------------------
try:
    st.image("logo_mr.png", width=140)
except:
    pass

st.title("🧑‍💼 Visão Geral dos Corretores – MR Imóveis")
st.caption("KPIs por corretor, vendas, eficiência e performance completa.")


# ------------------------------------------------------------
# CARREGAR PLANILHA GOOGLE SHEETS
# ------------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"


def limpar_data(s):
    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return dt.dt.date


@st.cache_data(ttl=60)
def carregar_base():
    df = pd.read_csv(CSV_URL)

    df.columns = [c.upper().strip() for c in df.columns]

    # DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_data(df["DATA"])
    else:
        df["DIA"] = limpar_data(df["DIA"]) if "DIA" in df.columns else pd.NaT

    # NOME CLIENTE
    possiveis_nomes = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = next((c for c in possiveis_nomes if c in df.columns), None)
    df["NOME_CLIENTE_BASE"] = df[col_nome].astype(str).str.upper().str.strip() if col_nome else "NÃO INFORMADO"

    # CPF
    possiveis_cpf = ["CPF", "CPF CLIENTE"]
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)
    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].astype(str).str.replace(r"\D", "", regex=True) if col_cpf else ""
    )

    # EQUIPE
    if "EQUIPE" in df.columns:
        df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper().str.strip()
    else:
        df["EQUIPE"] = "NÃO INFORMADO"

    # CORRETOR
    if "CORRETOR" in df.columns:
        df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    else:
        df["CORRETOR"] = "NÃO INFORMADO"

    # STATUS BASE
    df["STATUS_BASE"] = ""
    s = df["STATUS"].fillna("").astype(str).str.upper() if "STATUS" in df.columns else ""

    df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
    df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
    df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
    df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[s.str.contains("ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
    df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0

    return df


df = carregar_base()


# ------------------------------------------------------------
# LÓGICA GLOBAL – ÚLTIMO STATUS DO CLIENTE (OPÇÃO A)
# ------------------------------------------------------------

def aplicar_logica_status_final(df):
    """
    Mantém SOMENTE o último status do cliente.
    Se ele tiver VENDA GERADA → exclui VENDA INFORMADA anterior.
    """

    df2 = df.copy()

    df2["CHAVE"] = (
        df2["NOME_CLIENTE_BASE"].astype(str)
        + " | "
        + df2["CPF_CLIENTE_BASE"].astype(str)
    )

    df2 = df2.sort_values("DIA")
    df_final = df2.groupby("CHAVE").tail(1).copy()

    return df_final


# ------------------------------------------------------------
# SIDEBAR – FILTROS
# ------------------------------------------------------------
dias_validos = df["DIA"].dropna()

data_min = dias_validos.min()
data_max = dias_validos.max()

periodo = st.sidebar.date_input(
    "Período",
    value=(max(data_min, data_max - timedelta(days=30)), data_max),
    min_value=data_min,
    max_value=data_max,
)

data_ini, data_fim = periodo

equipes = ["Todas"] + sorted(df["EQUIPE"].unique())
corretores = ["Todos"] + sorted(df["CORRETOR"].unique())

equipe_sel = st.sidebar.selectbox("Equipe", equipes)
corretor_sel = st.sidebar.selectbox("Corretor", corretores)


# ------------------------------------------------------------
# FILTRAR BASE
# ------------------------------------------------------------
df_filtro = df[
    (df["DIA"] >= data_ini) &
    (df["DIA"] <= data_fim)
].copy()

if equipe_sel != "Todas":
    df_filtro = df_filtro[df_filtro["EQUIPE"] == equipe_sel]

if corretor_sel != "Todos":
    df_filtro = df_filtro[df_filtro["CORRETOR"] == corretor_sel]


# ------------------------------------------------------------
# APLICA A LÓGICA DO ÚLTIMO STATUS DO CLIENTE
# ------------------------------------------------------------
df_clean = aplicar_logica_status_final(df_filtro)


# ------------------------------------------------------------
# KPIs
# ------------------------------------------------------------
total_vendas = df_clean[df_clean["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
qtd_vendas = len(total_vendas)

vgv_total = total_vendas["VGV"].sum()
ticket_medio = vgv_total / qtd_vendas if qtd_vendas > 0 else 0

vendas_geradas = (df_clean["STATUS_BASE"] == "VENDA GERADA").sum()
vendas_informadas = (df_clean["STATUS_BASE"] == "VENDA INFORMADA").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendas Totais (líquidas)", qtd_vendas)
c2.metric("Vendas GERADAS", vendas_geradas)
c3.metric("Vendas INFORMADAS (reais)", vendas_informadas)
c4.metric("VGV Total", f"R$ {vgv_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

c5, c6 = st.columns(2)
c5.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
c6.metric("Corretores Ativos", df_clean["CORRETOR"].nunique())


# ------------------------------------------------------------
# RANKING DE CORRETORES
# ------------------------------------------------------------
st.subheader("🏅 Ranking de Corretores (Vendas Líquidas)")

df_rank = (
    total_vendas.groupby("CORRETOR")
    .agg(QTDE=("STATUS_BASE", "count"), VGV=("VGV", "sum"))
    .reset_index()
    .sort_values("VGV", ascending=False)
)

st.dataframe(df_rank, use_container_width=True)


# ------------------------------------------------------------
# TABELA DETALHADA
# ------------------------------------------------------------
st.subheader("📋 Base de Vendas (último status por cliente)")

df_show = df_clean[df_clean["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()

st.dataframe(
    df_show[[
        "DIA",
        "NOME_CLIENTE_BASE",
        "CPF_CLIENTE_BASE",
        "EQUIPE",
        "CORRETOR",
        "STATUS_BASE",
        "VGV"
    ]],
    use_container_width=True,
)
