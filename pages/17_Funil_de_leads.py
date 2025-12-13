import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Funil de Leads", layout="wide")
st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================
# FUNÇÕES
# =========================

def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    return " ".join(str(nome).upper().split())


@st.cache_data(ttl=1800)
def carregar_planilha():
    caminho = "utils/dados_funil.csv"  # <- ARQUIVO LOCAL

    df = pd.read_csv(caminho, dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]

    df["NOME_CLIENTE"] = df["CLIENTE"].apply(normalizar_nome)
    df["STATUS_BASE"] = df["SITUAÇÃO"].str.upper().str.strip()
    df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")

    df = df.dropna(subset=["DIA"])
    return df


@st.cache_data(ttl=1800)
def carregar_crm():
    df = pd.read_json("teste_leads.json")

    df["NOME_CLIENTE"] = df["nome_pessoa"].apply(normalizar_nome)
    df["ORIGEM"] = df.get("nome_origem", "SEM ORIGEM").fillna("SEM ORIGEM").str.upper()
    df["CAMPANHA"] = df.get("nome_campanha", "").fillna("").str.upper()
    df["CORRETOR"] = df.get("nome_corretor", "SEM CORRETOR").fillna("SEM CORRETOR").str.upper()
    df["EQUIPE"] = df.get("nome_equipe", "SEM EQUIPE").fillna("SEM EQUIPE").str.upper()

    return df.tail(1000)


# =========================
# CARGA
# =========================

df_plan = carregar_planilha()
df_crm = carregar_crm()

# =========================
# FILTRO DE DATA (SEGURO)
# =========================

data_inicio, data_fim = st.date_input(
    "📅 Período",
    value=(df_plan["DIA"].min().date(), df_plan["DIA"].max().date()),
    min_value=df_plan["DIA"].min().date(),
    max_value=df_plan["DIA"].max().date(),
)

df_plan = df_plan[
    (df_plan["DIA"].dt.date >= data_inicio) &
    (df_plan["DIA"].dt.date <= data_fim)
]

# =========================
# ÚLTIMO STATUS DO LEAD
# =========================

df_plan = df_plan.sort_values("DIA")
df_plan = df_plan.groupby("NOME_CLIENTE", as_index=False).last()

# =========================
# MERGE CRM
# =========================

df = df_plan.merge(
    df_crm[["NOME_CLIENTE", "ORIGEM", "CAMPANHA", "CORRETOR", "EQUIPE"]],
    on="NOME_CLIENTE",
    how="left"
)

df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================
# KPIs MACRO
# =========================

st.subheader("📌 Status Atual do Funil")

cols = st.columns(4)

def kpi(col, label, value):
    col.metric(label, int(value))

kpi(cols[0], "Em Análise", (df["STATUS_BASE"] == "EM ANÁLISE").sum())
kpi(cols[0], "Reanálise", (df["STATUS_BASE"] == "REANÁLISE").sum())

kpi(cols[1], "Aprovados", (df["STATUS_BASE"] == "APROVAÇÃO").sum())
kpi(cols[1], "Aprovados Bacen", (df["STATUS_BASE"] == "APROVADO BACEN").sum())

kpi(cols[2], "Pendência", (df["STATUS_BASE"] == "PENDÊNCIA").sum())
kpi(cols[2], "Reprovados", (df["STATUS_BASE"] == "REPROVAÇÃO").sum())

kpi(cols[3], "Venda Gerada", (df["STATUS_BASE"] == "VENDA GERADA").sum())
kpi(cols[3], "Venda Informada", (df["STATUS_BASE"] == "VENDA INFORMADA").sum())

st.metric(
    "Leads Ativos no Funil",
    df[~df["STATUS_BASE"].isin(["DESISTIU", "VENDA GERADA"])].shape[0]
)

# =========================
# PERFORMANCE POR ORIGEM
# =========================

st.divider()
st.subheader("📍 Performance por Origem")

origens = ["TODAS"] + sorted(df["ORIGEM"].unique())
origem = st.selectbox("Selecione a origem", origens)

df_f = df if origem == "TODAS" else df[df["ORIGEM"] == origem]

c1, c2, c3, c4 = st.columns(4)

kpi(c1, "Leads", len(df_f))
kpi(c1, "Análises", (df_f["STATUS_BASE"] == "EM ANÁLISE").sum())

kpi(c2, "Aprovados", (df_f["STATUS_BASE"] == "APROVAÇÃO").sum())
kpi(c2, "Vendas Geradas", (df_f["STATUS_BASE"] == "VENDA GERADA").sum())

kpi(c3, "Pendências", (df_f["STATUS_BASE"] == "PENDÊNCIA").sum())
kpi(c3, "Reprovados", (df_f["STATUS_BASE"] == "REPROVAÇÃO").sum())

kpi(c4, "Desistidos", (df_f["STATUS_BASE"] == "DESISTIU").sum())

# =========================
# CONVERSÃO
# =========================

st.divider()
st.subheader("📈 Conversões")

def taxa(a, b):
    return f"{(a/b*100):.1f}%" if b else "0%"

leads = len(df_f)
analises = (df_f["STATUS_BASE"] == "EM ANÁLISE").sum()
aprov = (df_f["STATUS_BASE"] == "APROVAÇÃO").sum()
vendas = (df_f["STATUS_BASE"] == "VENDA GERADA").sum()

x, y, z = st.columns(3)
x.metric("Leads → Análise", taxa(analises, leads))
y.metric("Análise → Aprovação", taxa(aprov, analises))
z.metric("Aprovação → Venda", taxa(vendas, aprov))

# =========================
# AUDITORIA CLIENTE
# =========================

st.divider()
st.subheader("🔎 Auditoria de Cliente")

busca = st.text_input("Buscar cliente")

if busca:
    nome = normalizar_nome(busca)
    df_cli = df[df["NOME_CLIENTE"].str.contains(nome)]

    if df_cli.empty:
        st.info("Cliente não encontrado.")
    else:
        st.dataframe(df_cli, use_container_width=True)
