# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", layout="wide")
st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# CONFIG PLANILHA
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATA"])

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "DATA BASE", "SITUAÇÃO"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.upper().str.strip()

    # Normaliza status
    df["STATUS_BASE"] = ""
    df.loc[df["SITUAÇÃO"].str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[df["SITUAÇÃO"].str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[df["SITUAÇÃO"].str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[df["SITUAÇÃO"].str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[df["SITUAÇÃO"].str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[df["SITUAÇÃO"].str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[df["SITUAÇÃO"].str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[df["SITUAÇÃO"].str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[df["SITUAÇÃO"].str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]

    return df

@st.cache_data(ttl=900)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dados, pagina = [], 1

    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=15)
        if r.status_code != 200:
            break
        js = r.json()
        if not js.get("data"):
            break
        dados.extend(js["data"])
        pagina += 1

    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM"])

    df["CLIENTE"] = df["nome_pessoa"].str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["ORIGEM"] = df["ORIGEM"].str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA
# =========================================================
df = carregar_planilha()
df = df.merge(carregar_crm(), on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTROS
# =========================================================
st.subheader("🎛️ Filtros")

c1, c2, c3, c4 = st.columns(4)

data_min, data_max = df["DATA"].min(), df["DATA"].max()
periodo = c1.date_input(
    "Período",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

data_base_sel = c2.selectbox(
    "Data Base",
    ["TODAS"] + sorted(df["DATA BASE"].dropna().unique())
)

equipe_sel = c3.selectbox(
    "Equipe",
    ["TODAS"] + sorted(df["EQUIPE"].dropna().unique())
)

corretor_sel = c4.selectbox(
    "Corretor",
    ["TODOS"] + sorted(df["CORRETOR"].dropna().unique())
)

df_filtro = df[
    (df["DATA"].between(pd.to_datetime(periodo[0]), pd.to_datetime(periodo[1])))
]

if data_base_sel != "TODAS":
    df_filtro = df_filtro[df_filtro["DATA BASE"] == data_base_sel]

if equipe_sel != "TODAS":
    df_filtro = df_filtro[df_filtro["EQUIPE"] == equipe_sel]

if corretor_sel != "TODOS":
    df_filtro = df_filtro[df_filtro["CORRETOR"] == corretor_sel]

# =========================================================
# FUNIL ATUAL (ESTOQUE)
# =========================================================
st.divider()
st.subheader("📌 Status Atual do Funil")

df_ultimo = (
    df.sort_values("DATA")
      .groupby("CLIENTE", as_index=False)
      .last()
)

if equipe_sel != "TODAS":
    df_ultimo = df_ultimo[df_ultimo["EQUIPE"] == equipe_sel]

if corretor_sel != "TODOS":
    df_ultimo = df_ultimo[df_ultimo["CORRETOR"] == corretor_sel]

cards = {
    "Em Análise": (df_ultimo["STATUS_BASE"] == "ANALISE").sum(),
    "Reanálise": (df_ultimo["STATUS_BASE"] == "REANALISE").sum(),
    "Aprovados": df_ultimo["STATUS_BASE"].isin(["APROVADO", "APROVADO_BACEN"]).sum(),
    "Pendências": (df_ultimo["STATUS_BASE"] == "PENDENCIA").sum(),
    "Reprovados": (df_ultimo["STATUS_BASE"] == "REPROVADO").sum(),
    "Vendas Geradas": (df_ultimo["STATUS_BASE"] == "VENDA_GERADA").sum(),
    "Vendas Informadas": (df_ultimo["STATUS_BASE"] == "VENDA_INFORMADA").sum(),
}

cols = st.columns(4)
for i, (k, v) in enumerate(cards.items()):
    cols[i % 4].metric(k, v)

# =========================================================
# PERFORMANCE E CONVERSÃO POR ORIGEM
# =========================================================
st.divider()
st.subheader("🎯 Performance e Conversão por Origem")

origem_sel = st.selectbox(
    "Origem",
    ["TODAS"] + sorted(df_filtro["ORIGEM"].unique())
)

df_o = df_filtro if origem_sel == "TODAS" else df_filtro[df_filtro["ORIGEM"] == origem_sel]

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Informadas + Geradas", "Apenas Vendas Geradas"],
    horizontal=True
)

analises = df_o[df_o["STATUS_BASE"] == "ANALISE"]
reanalises = df_o[df_o["STATUS_BASE"] == "REANALISE"]

aprovados = df_o[df_o["STATUS_BASE"].isin(
    ["APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"]
)]

if tipo_venda == "Apenas Vendas Geradas":
    vendas = df_o[df_o["STATUS_BASE"] == "VENDA_GERADA"]
else:
    vendas = df_o[df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", df_o["CLIENTE"].nunique())
c2.metric("Análises", len(analises))
c3.metric("Reanálises", len(reanalises))
c4.metric("Vendas", len(vendas))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{len(analises)/df_o['CLIENTE'].nunique()*100 if len(df_o) else 0:.1f}%")
c6.metric("Análise → Aprovação", f"{len(aprovados)/len(analises)*100 if len(analises) else 0:.1f}%")
c7.metric("Análise → Venda", f"{len(vendas)/len(analises)*100 if len(analises) else 0:.1f}%")
c8.metric("Aprovação → Venda", f"{len(vendas)/len(aprovados)*100 if len(aprovados) else 0:.1f}%")

# =========================================================
# TABELA DE LEADS DA ORIGEM
# =========================================================
st.divider()
st.subheader("📋 Leads da Origem Selecionada")

st.dataframe(
    df_o[["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]]
    .sort_values("DATA", ascending=False),
    use_container_width=True
)
