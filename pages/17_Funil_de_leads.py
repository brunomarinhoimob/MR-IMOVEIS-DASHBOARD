import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Funil de Leads",
    layout="wide"
)

# =============================
# CONFIGURAÇÃO
# =============================
URL_PLANILHA = "COLE_AQUI_O_MESMO_LINK_CSV_QUE_JÁ_USA_NO DASHBOARD"

STATUS_ANALISE = "EM ANALISE"
STATUS_REANALISE = "REANALISE"
STATUS_APROVADO = ["APROVADO", "APROVADO BACEN"]
STATUS_VENDA_GERADA = "VENDA GERADA"
STATUS_VENDA_INFORMADA = "VENDA INFORMADA"
STATUS_DESISTIU = "DESISTIU"

# =============================
# CARREGAMENTO
# =============================
@st.cache_data(ttl=600)
def carregar_dados():
    df = pd.read_csv(URL_PLANILHA, dtype=str)

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df["DATA_BASE"] = df["DATA_BASE"].fillna("SEM DATA BASE")
    df["STATUS_BASE"] = df["STATUS_BASE"].str.upper().str.strip()
    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].str.upper().str.strip()
    df["ORIGEM"] = df["ORIGEM"].str.upper().str.strip()

    return df.dropna(subset=["CLIENTE", "DATA"])

df_raw = carregar_dados()

# =============================
# FILTROS
# =============================
st.title("🎯 Funil de Leads – Origem, Status e Conversão")

col1, col2, col3, col4 = st.columns(4)

with col1:
    data_ini, data_fim = st.date_input(
        "Período",
        value=(df_raw["DATA"].min().date(), df_raw["DATA"].max().date())
    )

with col2:
    data_base_sel = st.selectbox(
        "Data Base",
        ["TODAS"] + sorted(df_raw["DATA_BASE"].unique())
    )

with col3:
    equipe_sel = st.selectbox(
        "Equipe",
        ["TODAS"] + sorted(df_raw["EQUIPE"].unique())
    )

with col4:
    corretor_sel = st.selectbox(
        "Corretor",
        ["TODOS"] + sorted(df_raw["CORRETOR"].unique())
    )

origem_sel = st.selectbox(
    "Origem",
    ["TODAS"] + sorted(df_raw["ORIGEM"].unique())
)

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Apenas Vendas Geradas", "Vendas Geradas + Informadas"],
    horizontal=True
)

# =============================
# APLICA FILTROS
# =============================
df = df_raw[
    (df_raw["DATA"].dt.date >= data_ini) &
    (df_raw["DATA"].dt.date <= data_fim)
]

if data_base_sel != "TODAS":
    df = df[df["DATA_BASE"] == data_base_sel]

if equipe_sel != "TODAS":
    df = df[df["EQUIPE"] == equipe_sel]

if corretor_sel != "TODOS":
    df = df[df["CORRETOR"] == corretor_sel]

if origem_sel != "TODAS":
    df = df[df["ORIGEM"] == origem_sel]

# =============================
# HISTÓRICO POR LEAD
# =============================
df_hist = (
    df.sort_values("DATA")
      .groupby("CLIENTE", as_index=False)
      .agg({
          "STATUS_BASE": list,
          "DATA": "max",
          "CORRETOR": "last",
          "EQUIPE": "last",
          "ORIGEM": "last"
      })
)

# FLAGS
df_hist["TEVE_ANALISE"] = df_hist["STATUS_BASE"].apply(lambda x: STATUS_ANALISE in x)
df_hist["TEVE_REANALISE"] = df_hist["STATUS_BASE"].apply(lambda x: STATUS_REANALISE in x)
df_hist["TEVE_APROVACAO"] = df_hist["STATUS_BASE"].apply(
    lambda x: any(s in x for s in STATUS_APROVADO)
)
df_hist["TEVE_VENDA_GERADA"] = df_hist["STATUS_BASE"].apply(
    lambda x: STATUS_VENDA_GERADA in x
)
df_hist["TEVE_VENDA_INFORMADA"] = df_hist["STATUS_BASE"].apply(
    lambda x: STATUS_VENDA_INFORMADA in x and STATUS_VENDA_GERADA not in x
)
df_hist["DESISTIU"] = df_hist["STATUS_BASE"].apply(lambda x: STATUS_DESISTIU in x)

# =============================
# KPIs
# =============================
total_leads = len(df_hist)
analises = df_hist["TEVE_ANALISE"].sum()
reanalises = df_hist["TEVE_REANALISE"].sum()
aprovados = df_hist["TEVE_APROVACAO"].sum()

if tipo_venda == "Apenas Vendas Geradas":
    vendas = df_hist["TEVE_VENDA_GERADA"].sum()
else:
    vendas = (
        df_hist["TEVE_VENDA_GERADA"] |
        df_hist["TEVE_VENDA_INFORMADA"]
    ).sum()

# =============================
# CONVERSÕES
# =============================
def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b else "0.0%"

# =============================
# CARDS
# =============================
st.subheader("📊 Performance e Conversão")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", total_leads)
c2.metric("Análises (EM ANÁLISE)", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lead → Análise", pct(analises, total_leads))
c2.metric("Análise → Aprovação", pct(aprovados, analises))
c3.metric("Análise → Venda", pct(vendas, analises))
c4.metric("Aprovação → Venda", pct(vendas, aprovados))

# =============================
# TABELA – ÚLTIMA MOVIMENTAÇÃO
# =============================
st.subheader("📋 Leads da Origem Selecionada")

df_ultima = (
    df.sort_values("DATA")
      .groupby("CLIENTE", as_index=False)
      .last()[["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]]
      .rename(columns={"DATA": "ULTIMA_ATUALIZACAO"})
)

st.dataframe(
    df_ultima.sort_values("ULTIMA_ATUALIZACAO", ascending=False),
    use_container_width=True
)
