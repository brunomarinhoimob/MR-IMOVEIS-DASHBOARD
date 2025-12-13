# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date

from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="🎯", layout="wide")
st.title("🎯 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# LINK OFICIAL DA PLANILHA (SEM INVENTAR)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATA"])

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "DATA BASE", "SITUAÇÃO"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    # STATUS BASE
    df["STATUS_BASE"] = ""
    df.loc[df["SITUAÇÃO"].str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[df["SITUAÇÃO"].str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[df["SITUAÇÃO"].str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[df["SITUAÇÃO"].str.contains("APROVADO"), "STATUS_BASE"] = "APROVADO"
    df.loc[df["SITUAÇÃO"].str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[df["SITUAÇÃO"].str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[df["SITUAÇÃO"].str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[df["SITUAÇÃO"].str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[df["SITUAÇÃO"].str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]

    # REGRA: se existe VENDA GERADA, ignora VENDA INFORMADA
    df = df.sort_values("DATA")
    df["FLAG_VENDA_GERADA"] = df.groupby("CLIENTE")["STATUS_BASE"].transform(
        lambda x: "VENDA_GERADA" in x.values
    )
    df = df[~((df["FLAG_VENDA_GERADA"]) & (df["STATUS_BASE"] == "VENDA_INFORMADA"))]

    # ÚLTIMO STATUS DO LEAD
    df = df.groupby("CLIENTE", as_index=False).last()
    return df

@st.cache_data(ttl=600)
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

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CRM").fillna("SEM CRM").str.upper().str.strip()
    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CRM")

# =========================================================
# SIDEBAR – FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Tipo de período", ["DIA", "DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df["DATA"].min().date(), df["DATA"].max().date())
    )
    df = df[(df["DATA"].dt.date >= ini) & (df["DATA"].dt.date <= fim)]
else:
    bases = sorted(df["DATA BASE"].unique().tolist())
    bases_sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    df = df[df["DATA BASE"].isin(bases_sel)]

equipe = st.sidebar.selectbox("Equipe", ["TODAS"] + sorted(df["EQUIPE"].unique()))
if equipe != "TODAS":
    df = df[df["EQUIPE"] == equipe]

corretor = st.sidebar.selectbox("Corretor", ["TODOS"] + sorted(df["CORRETOR"].unique()))
if corretor != "TODOS":
    df = df[df["CORRETOR"] == corretor]

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📊 Performance e Conversão por Origem")

origem = st.selectbox("Origem", ["TODAS"] + sorted(df["ORIGEM"].unique()))
df_o = df if origem == "TODAS" else df[df["ORIGEM"] == origem]

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Geradas + Informadas", "Apenas Vendas Geradas"]
)

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
reanalises = (df_o["STATUS_BASE"] == "REANALISE").sum()
aprovados = df_o["STATUS_BASE"].isin(["APROVADO", "APROVADO_BACEN"]).sum()

if tipo_venda == "Apenas Vendas Geradas":
    vendas = (df_o["STATUS_BASE"] == "VENDA_GERADA").sum()
else:
    vendas = df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"]).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{analises/leads*100:.1f}%" if leads else "0%")
c6.metric("Análise → Aprovação", f"{aprovados/analises*100:.1f}%" if analises else "0%")
c7.metric("Análise → Venda", f"{vendas/analises*100:.1f}%" if analises else "0%")
c8.metric("Aprovação → Venda", f"{vendas/aprovados*100:.1f}%" if aprovados else "0%")

# =========================================================
# TABELA – ÚLTIMA ATUALIZAÇÃO
# =========================================================
st.subheader("📋 Leads da Origem Selecionada")

tabela = df_o.sort_values("DATA", ascending=False)
tabela = tabela[["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]]
tabela.rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}, inplace=True)

st.dataframe(tabela, use_container_width=True)
