# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (BASE LIMPA)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date

from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="📊", layout="wide")

# Logo
try:
    st.image("logo_mr.png", width=120)
except:
    pass

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA (MESMA FONTE)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base_label(label):
    if label is None:
        return pd.NaT
    s = str(label).strip().upper()
    parts = s.split()
    if len(parts) < 2:
        return pd.NaT
    mes = MESES.get(parts[0])
    try:
        ano = int(parts[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARREGAR PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base_label)

    df["CLIENTE"] = df["CLIENTE"].astype(str).str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper().str.strip()
    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()

    df["STATUS_BASE"] = ""
    df.loc[df["STATUS_RAW"].str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[df["STATUS_RAW"].str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[df["STATUS_RAW"].str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[df["STATUS_RAW"].str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[df["STATUS_RAW"].str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[df["STATUS_RAW"].str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[df["STATUS_RAW"].str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]

    # ÚLTIMA ATUALIZAÇÃO POR CLIENTE
    df = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()

    return df

# =========================================================
# CARREGAR CRM (ORIGEM + CAMPANHA)
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm_ultimos_1000():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados, pagina = [], 1
    try:
        while len(dados) < 1000:
            r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
            if r.status_code != 200:
                break
            js = r.json()
            if not js.get("data"):
                break
            dados.extend(js["data"])
            pagina += 1
    except:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df["CAMPANHA"].astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# CARGA
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm_ultimos_1000()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df["CAMPANHA"] = df["CAMPANHA"].fillna("-")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo_periodo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_filtrado = df.copy()

if modo_periodo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        (df_filtrado["DATA"].min().date(), df_filtrado["DATA"].max().date())
    )
    df_filtrado = df_filtrado[
        (df_filtrado["DATA"].dt.date >= ini) &
        (df_filtrado["DATA"].dt.date <= fim)
    ]
else:
    bases = sorted(df_filtrado["DATA_BASE_LABEL"].dropna().unique().tolist())
    bases_sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if bases_sel:
        df_filtrado = df_filtrado[df_filtrado["DATA_BASE_LABEL"].isin(bases_sel)]

equipes = sorted(df_filtrado["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["TODAS"] + equipes)
if equipe_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

corretores = sorted(df_filtrado["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["TODOS"] + corretores)
if corretor_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

# =========================================================
# STATUS ATUAL
# =========================================================
st.subheader("📌 Status Atual do Funil")

kpi = df_filtrado["STATUS_BASE"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", int(kpi.get("ANALISE", 0)))
c2.metric("Reanálise", int(kpi.get("REANALISE", 0)))
c3.metric("Pendência", int(kpi.get("PENDENCIA", 0)))
c4.metric("Reprovado", int(kpi.get("REPROVADO", 0)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", int(kpi.get("APROVADO", 0)))
c6.metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
c7.metric("Desistiu", int(kpi.get("DESISTIU", 0)))
c8.metric("Leads no Funil", int(len(df_filtrado)))

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df_filtrado["ORIGEM"].unique())
origem_sel = st.selectbox("Origem", origens)

df_o = df_filtrado if origem_sel == "TODAS" else df_filtrado[df_filtrado["ORIGEM"] == origem_sel]

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
aprovados = df_o["STATUS_BASE"].isin(["APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"]).sum()
vendas = df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"]).sum()
reanalises = (df_o["STATUS_BASE"] == "REANALISE").sum()

def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b else "0%"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c1.metric("Lead → Análise", pct(analises, leads))
c2.metric("Análise → Aprovação", pct(aprovados, analises))
c3.metric("Análise → Venda", pct(vendas, analises))
c4.metric("Aprovação → Venda", pct(vendas, aprovados))

# =========================================================
# TABELA DE LEADS
# =========================================================
st.subheader("📋 Leads da Origem Selecionada")

tabela = df_o[["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]].copy()
tabela = tabela.sort_values("DATA", ascending=False)
tabela.rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}, inplace=True)

st.dataframe(tabela, use_container_width=True)
