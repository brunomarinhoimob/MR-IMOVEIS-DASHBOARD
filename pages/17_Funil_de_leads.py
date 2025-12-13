# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (MR IMÓVEIS)
# =========================================================

import streamlit as st
import pandas as pd
from datetime import date

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="Funil de Leads | MR Imóveis", layout="wide")

# Logo MR
st.image("logo_mr.png", width=120)

st.title("🎯 Funil de Leads – Origem, Status e Conversão")

# ---------------------------------------------------------
# PLANILHA OFICIAL (NÃO ALTERAR)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data_base(label):
    try:
        mes, ano = label.upper().split()
        return date(int(ano), MESES.get(mes, 1), 1)
    except:
        return pd.NaT

# ---------------------------------------------------------
# LOAD DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_csv(URL_PLANILHA, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATA"])

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "")
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    # Normalização de status
    df["STATUS_BASE"] = ""
    mapa = {
        "EM ANÁLISE": "ANALISE",
        "REANÁLISE": "REANALISE",
        "APROVADO BACEN": "APROVADO_BACEN",
        "APROV": "APROVADO",
        "REPROV": "REPROVADO",
        "PEND": "PENDENCIA",
        "VENDA GERADA": "VENDA_GERADA",
        "VENDA INFORMADA": "VENDA_INFORMADA",
        "DESIST": "DESISTIU",
    }

    for k, v in mapa.items():
        df.loc[df["SITUAÇÃO"].str.contains(k), "STATUS_BASE"] = v

    df = df[df["STATUS_BASE"] != ""]

    return df

df_raw = carregar_dados()

# ---------------------------------------------------------
# FILTROS
# ---------------------------------------------------------
st.sidebar.header("🎛️ Filtros")

modo_periodo = st.sidebar.radio("Tipo de Período", ["DIA", "DATA BASE"])

df = df_raw.copy()

if modo_periodo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        (df["DATA"].min().date(), df["DATA"].max().date())
    )
    df = df[(df["DATA"].dt.date >= ini) & (df["DATA"].dt.date <= fim)]
else:
    bases = sorted(df["DATA_BASE_LABEL"].dropna().unique())
    sel_bases = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel_bases:
        df = df[df["DATA_BASE_LABEL"].isin(sel_bases)]

equipes = ["TODAS"] + sorted(df["EQUIPE"].unique())
eq = st.sidebar.selectbox("Equipe", equipes)
if eq != "TODAS":
    df = df[df["EQUIPE"] == eq]

corretores = ["TODOS"] + sorted(df["CORRETOR"].unique())
cor = st.sidebar.selectbox("Corretor", corretores)
if cor != "TODOS":
    df = df[df["CORRETOR"] == cor]

# ---------------------------------------------------------
# STATUS ATUAL DO FUNIL
# ---------------------------------------------------------
st.subheader("📌 Status Atual do Funil")

# Última movimentação por cliente
df_ultimo = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", (df_ultimo["STATUS_BASE"] == "ANALISE").sum())
c2.metric("Reanálises", (df_ultimo["STATUS_BASE"] == "REANALISE").sum())
c3.metric("Pendências", (df_ultimo["STATUS_BASE"] == "PENDENCIA").sum())
c4.metric("Vendas Geradas", (df_ultimo["STATUS_BASE"] == "VENDA_GERADA").sum())

st.metric("Leads Ativos no Funil", df_ultimo["CLIENTE"].nunique())

# ---------------------------------------------------------
# PERFORMANCE E CONVERSÃO POR ORIGEM
# ---------------------------------------------------------
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df["ORIGEM"].dropna().unique()) if "ORIGEM" in df.columns else ["TODAS"]
origem = st.selectbox("Origem", origens)

df_o = df if origem == "TODAS" else df[df["ORIGEM"] == origem]

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Geradas + Informadas", "Apenas Vendas Geradas"],
    horizontal=True
)

# Contagens corretas
total_leads = df_o["CLIENTE"].nunique()
total_analises = df_o[df_o["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
total_reanalises = df_o[df_o["STATUS_BASE"] == "REANALISE"]["CLIENTE"].nunique()

total_aprovados = df_o[
    df_o["STATUS_BASE"].isin([
        "APROVADO", "APROVADO_BACEN", "VENDA_INFORMADA", "VENDA_GERADA"
    ])
]["CLIENTE"].nunique()

if tipo_venda == "Apenas Vendas Geradas":
    total_vendas = df_o[df_o["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()
else:
    total_vendas = df_o[
        df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])
    ]["CLIENTE"].nunique()

def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b > 0 else "0%"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", total_leads)
c2.metric("Análises", total_analises)
c3.metric("Reanálises", total_reanalises)
c4.metric("Vendas", total_vendas)

c1.metric("Lead → Análise", pct(total_analises, total_leads))
c2.metric("Análise → Aprovação", pct(total_aprovados, total_analises))
c3.metric("Análise → Venda", pct(total_vendas, total_analises))
c4.metric("Aprovação → Venda", pct(total_vendas, total_aprovados))

# ---------------------------------------------------------
# TABELA – ÚLTIMA ATUALIZAÇÃO DO LEAD
# ---------------------------------------------------------
st.subheader("📋 Leads da Origem Selecionada")

st.dataframe(
    df_ultimo.sort_values("DATA", ascending=False)[
        ["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]
    ].rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}),
    use_container_width=True
)

# ---------------------------------------------------------
# AUDITORIA RÁPIDA DE LEAD
# ---------------------------------------------------------
st.subheader("🔎 Auditoria Rápida de Lead")

modo_busca = st.radio("Buscar por:", ["Nome", "CPF"], horizontal=True)
texto = st.text_input("Digite para buscar")

if texto:
    if modo_busca == "Nome":
        df_cliente = df[df["CLIENTE"].str.contains(texto.upper(), na=False)]
    else:
        df_cliente = df[df["CPF"].str.contains(texto, na=False)]

    if not df_cliente.empty:
        atual = df_cliente.sort_values("DATA").iloc[-1]

        c1, c2, c3 = st.columns(3)
        c1.metric("Situação Atual", atual["STATUS_BASE"])
        c2.metric("Corretor", atual["CORRETOR"])
        c3.metric("Última Atualização", atual["DATA"].strftime("%d/%m/%Y"))

        st.markdown("### 🧾 Linha do Tempo do Lead")
        st.dataframe(
            df_cliente.sort_values("DATA")[["DATA", "STATUS_BASE", "SITUAÇÃO"]],
            use_container_width=True
        )
