# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (OFICIAL)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads • Origem & Conversão",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# GOOGLE SHEETS
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def limpar_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce").dt.date

def mes_ano_para_date(valor):
    meses = {
        "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
        "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
        "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
        "NOVEMBRO": 11, "DEZEMBRO": 12,
    }
    try:
        p = str(valor).upper().split()
        return datetime(int(p[-1]), meses[p[0]], 1).date()
    except:
        return pd.NaT

def normalizar_nome(v):
    if pd.isna(v):
        return ""
    return str(v).upper().strip().replace("  ", " ")

# =========================================================
# PLANILHA – FUNIL
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    df["DIA"] = limpar_data(df["DATA"])
    df["DATA_BASE"] = df["DATA BASE"].apply(mes_ano_para_date)
    df["DATA_BASE_LABEL"] = df["DATA BASE"].astype(str)

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper()

    df = df[df["STATUS_RAW"].str.contains(
        "ANÁLISE|REANÁLISE|APROV|REPROV|VENDA|DESIST|PEND",
        regex=True
    )]

    df["NOME_CLIENTE"] = df["CLIENTE"].astype(str).str.upper().str.strip()
    df["CHAVE"] = df["NOME_CLIENTE"]

    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper()
    df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper()

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

    # Último status do cliente
    df = df.sort_values("DIA")
    df = df.groupby("CHAVE").tail(1)

    return df

df_plan = carregar_planilha()

# =========================================================
# SIDEBAR – FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_plan["DIA"].min(), df_plan["DIA"].max())
    )
    df_plan = df_plan[(df_plan["DIA"] >= ini) & (df_plan["DIA"] <= fim)]
else:
    bases = st.sidebar.multiselect(
        "Data Base",
        sorted(df_plan["DATA_BASE_LABEL"].unique()),
        default=df_plan["DATA_BASE_LABEL"].unique()
    )
    df_plan = df_plan[df_plan["DATA_BASE_LABEL"].isin(bases)]

equipes = sorted(df_plan["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + equipes)
if equipe_sel != "Todas":
    df_plan = df_plan[df_plan["EQUIPE"] == equipe_sel]

corretores = sorted(df_plan["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + corretores)
if corretor_sel != "Todos":
    df_plan = df_plan[df_plan["CORRETOR"] == corretor_sel]

# =========================================================
# CRM – ÚLTIMOS 1000 LEADS (CACHE 30 MIN)
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm_ultimos_1000():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados = []
    pagina = 1

    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
        if r.status_code != 200:
            break

        js = r.json()
        if "data" not in js or not js["data"]:
            break

        for lead in js["data"]:
            dados.append(lead)
            if len(dados) >= 1000:
                break

        pagina += 1

    df = pd.DataFrame(dados)

    df["CHAVE"] = (
        df["nome_pessoa"].astype(str).str.upper().str.strip()
        if "nome_pessoa" in df.columns
        else ""
    )

    df["ORIGEM"] = (
        df["nome_origem"].fillna("SEM ORIGEM").astype(str)
        if "nome_origem" in df.columns
        else "SEM ORIGEM"
    )

    df["CAMPANHA"] = (
        df["nome_campanha"].fillna("SEM CAMPANHA").astype(str)
        if "nome_campanha" in df.columns
        else "SEM CAMPANHA"
    )

    df["CORRETOR"] = (
        df["nome_corretor"].fillna("SEM CORRETOR").astype(str).str.upper()
        if "nome_corretor" in df.columns
        else "SEM CORRETOR"
    )

    df["EQUIPE"] = (
        df["nome_equipe"].fillna("SEM EQUIPE").astype(str).str.upper()
        if "nome_equipe" in df.columns
        else "SEM EQUIPE"
    )

    return df

df_crm = carregar_crm_ultimos_1000()

# =========================================================
# CRUZAMENTO
# =========================================================
df = df_plan.merge(
    df_crm[["CHAVE", "ORIGEM", "CAMPANHA"]],
    on="CHAVE",
    how="left"
)

df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df["CAMPANHA"] = df["CAMPANHA"].fillna("-")

# =========================================================
# KPIs – STATUS ATUAL
# =========================================================
st.subheader("📊 Status Atual do Funil")

kpi = df["STATUS_BASE"].value_counts()
df_vendas_validas = df[~df["STATUS_BASE"].isin(["DESISTIU"])]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", kpi.get("ANALISE", 0))
c2.metric("Reanálises", kpi.get("REANALISE", 0))
c3.metric("Pendências", kpi.get("PENDENCIA", 0))
c4.metric("Reprovados", kpi.get("REPROVADO", 0))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovados", kpi.get("APROVADO", 0))
c6.metric("Aprovados Bacen", kpi.get("APROVADO_BACEN", 0))
c7.metric("Desistidos", kpi.get("DESISTIU", 0))
c8.metric("Leads no Funil", len(df))

c9, c10 = st.columns(2)
c9.metric("Vendas Informadas", (df_vendas_validas["STATUS_BASE"] == "VENDA_INFORMADA").sum())
c10.metric("Vendas Geradas", (df_vendas_validas["STATUS_BASE"] == "VENDA_GERADA").sum())

# =========================================================
# SELETOR DE ORIGEM + CARDS
# =========================================================
st.subheader("📌 Performance por Origem")

origem_sel = st.selectbox("Selecione a Origem", sorted(df["ORIGEM"].unique()))
df_origem = df[df["ORIGEM"] == origem_sel]

status_o = df_origem["STATUS_BASE"].value_counts()
df_vendas_origem = df_origem[~df_origem["STATUS_BASE"].isin(["DESISTIU"])]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", len(df_origem))
c2.metric("Análise", status_o.get("ANALISE", 0))
c3.metric("Reanálise", status_o.get("REANALISE", 0))
c4.metric("Pendência", status_o.get("PENDENCIA", 0))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", status_o.get("APROVADO", 0))
c6.metric("Aprovado Bacen", status_o.get("APROVADO_BACEN", 0))
c7.metric("Reprovado", status_o.get("REPROVADO", 0))
c8.metric("Desistiu", status_o.get("DESISTIU", 0))

c9, c10 = st.columns(2)
c9.metric("Venda Informada", (df_vendas_origem["STATUS_BASE"] == "VENDA_INFORMADA").sum())
c10.metric("Venda Gerada", (df_vendas_origem["STATUS_BASE"] == "VENDA_GERADA").sum())

# =========================================================
# 📈 CONVERSÃO POR ORIGEM
# =========================================================
st.subheader("📈 Taxa de Conversão por Origem")

conv = (
    df
    .groupby("ORIGEM")
    .agg(
        LEADS=("STATUS_BASE", "count"),
        APROVADOS=("STATUS_BASE", lambda x: (x == "APROVADO").sum()),
        VENDAS=("STATUS_BASE", lambda x: (x == "VENDA_GERADA").sum()),
    )
    .reset_index()
)

conv["TX_APROVACAO_%"] = (conv["APROVADOS"] / conv["LEADS"] * 100).round(1)
conv["TX_VENDA_%"] = (conv["VENDAS"] / conv["LEADS"] * 100).round(1)

st.dataframe(conv, use_container_width=True)

# =========================================================
# 👥 ORIGEM × CORRETOR
# =========================================================
st.subheader("👥 Origem × Corretor")

origem_corretor = (
    df
    .groupby(["ORIGEM", "CORRETOR"])
    .agg(
        LEADS=("STATUS_BASE", "count"),
        VENDAS=("STATUS_BASE", lambda x: (x == "VENDA_GERADA").sum())
    )
    .reset_index()
    .sort_values("VENDAS", ascending=False)
)

st.dataframe(origem_corretor, use_container_width=True)

# =========================================================
# 🚨 ALERTAS AUTOMÁTICOS
# =========================================================
st.subheader("🚨 Alertas Automáticos")

alertas = conv[
    (conv["LEADS"] >= 10) &
    (conv["TX_APROVACAO_%"] < 10)
]

if alertas.empty:
    st.success("Nenhum alerta crítico no período 🎯")
else:
    st.warning("Origens com baixa taxa de aprovação")
    st.dataframe(alertas, use_container_width=True)

# =========================================================
# 📋 AUDITORIA FINAL
# =========================================================
st.subheader("🧾 Auditoria Final")

st.dataframe(
    df[[
        "NOME_CLIENTE",
        "STATUS_BASE",
        "ORIGEM",
        "CAMPANHA",
        "CORRETOR",
        "EQUIPE",
        "DIA",
        "DATA_BASE_LABEL",
    ]].sort_values("DIA", ascending=False),
    use_container_width=True
)
