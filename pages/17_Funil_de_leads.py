# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# UTILIDADES
# =========================================================
MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base(label):
    if not label or pd.isna(label):
        return pd.NaT
    p = str(label).upper().split()
    if len(p) < 2:
        return pd.NaT
    mes = MESES.get(p[0])
    try:
        ano = int(p[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARGA PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()
    df["STATUS_BASE"] = ""

    regras = [
        ("APROVADO BACEN", "APROVADO_BACEN"),
        ("EM ANÁLISE", "ANALISE"),
        ("REANÁLISE", "REANALISE"),
        ("VENDA GERADA", "VENDA_GERADA"),
        ("VENDA INFORMADA", "VENDA_INFORMADA"),
        ("REPROV", "REPROVADO"),
        ("PEND", "PENDENCIA"),
        ("DESIST", "DESISTIU"),
        ("APROVA", "APROVADO"),
    ]

    for chave, valor in regras:
        mask = df["STATUS_RAW"].str.contains(chave, na=False)
        df.loc[mask & (df["STATUS_BASE"] == ""), "STATUS_BASE"] = valor

    return df[df["STATUS_BASE"] != ""]

# =========================================================
# CARGA CRM
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados, pagina = [], 1
    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
        if r.status_code != 200:
            break
        js = r.json()
        if not js.get("data"):
            break
        dados.extend(js["data"])
        pagina += 1

    if not dados:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA", "CORRETOR"])

    df = pd.DataFrame(dados)
    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")
    df["CORRETOR"] = df.get("nome_corretor", "").fillna("")

    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df["CAMPANHA"].astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM", "CAMPANHA", "CORRETOR"]]

# =========================================================
# DATASETS
# =========================================================
df_hist = carregar_planilha()
df_crm = carregar_crm()

df_hist = df_hist.merge(df_crm, on="CLIENTE", how="left")
df_hist["ORIGEM"] = df_hist["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df_hist["CAMPANHA"] = df_hist["CAMPANHA"].fillna("-")
df_hist["CORRETOR_CRM"] = df_hist["CORRETOR_y"].fillna("")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_f = df_hist.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique(), key=parse_data_base)
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origem = st.selectbox("Origem", ["TODAS"] + sorted(df_f["ORIGEM"].unique()))
df_o = df_f if origem == "TODAS" else df_f[df_f["ORIGEM"] == origem]

leads = df_o["CLIENTE"].nunique()
analises = df_o[df_o["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
aprovados = df_o[df_o["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique()
vendas = df_o[df_o["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
c8.metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")

# =========================================================
# 🔥 RESUMO DE LEADS (SUPREMO CRM)
# =========================================================
st.markdown("---")
st.subheader("📊 Resumo de Leads (Supremo CRM)")

df_crm_o = df_crm if origem == "TODAS" else df_crm[df_crm["ORIGEM"] == origem]

leads_recebidos = df_crm_o["CLIENTE"].nunique()
leads_distribuidos = df_crm_o[df_crm_o["CORRETOR"] != ""]["CLIENTE"].nunique()
corretores_com_lead = df_crm_o[df_crm_o["CORRETOR"] != ""]["CORRETOR"].nunique()
media_por_corretor = round(leads_distribuidos / corretores_com_lead, 1) if corretores_com_lead else 0

c1, c2, c3 = st.columns(3)
c1.metric("Leads Recebidos (CRM)", leads_recebidos)
c2.metric("Leads Distribuídos", leads_distribuidos)
c3.metric("Média por Corretor", media_por_corretor)
