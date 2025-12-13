import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Funil de Leads", layout="wide")

# =============================
# CONFIG
# =============================
URL_PLANILHA = "COLE_AQUI_O_MESMO_LINK_DA_99_PAGINA_TESTE"

STATUS_ANALISE = "EM ANÁLISE"
STATUS_APROVADO = "APROVAÇÃO"
STATUS_APROVADO_BACEN = "APROVADO BACEN"
STATUS_REANALISE = "REANÁLISE"
STATUS_REPROVADO = "REPROVAÇÃO"
STATUS_PENDENCIA = "PENDÊNCIA"
STATUS_VENDA_GERADA = "VENDA GERADA"
STATUS_VENDA_INFORMADA = "VENDA INFORMADA"
STATUS_DESISTIU = "DESISTIU"

# =============================
# LOAD
# =============================
@st.cache_data(ttl=1800)
def carregar_dados():
    df = pd.read_csv(URL_PLANILHA, dtype=str)

    df.columns = df.columns.str.upper().str.strip()

    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["SITUAÇÃO"] = df["SITUAÇÃO"].str.upper().str.strip()

    df["ORIGEM_FINAL"] = (
        df.get("ORIGEM")
        .fillna("SEM CADASTRO NO CRM")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    return df

df = carregar_dados()

# =============================
# FILTROS
# =============================
st.title("📊 Funil de Leads – Origem, Status e Conversão")

min_data = df["DATA"].min()
max_data = df["DATA"].max()

data_ini, data_fim = st.date_input(
    "Período",
    value=(min_data.date(), max_data.date())
)

df_filtro = df[
    (df["DATA"] >= pd.to_datetime(data_ini)) &
    (df["DATA"] <= pd.to_datetime(data_fim))
]

origens = ["TODAS"] + sorted(df_filtro["ORIGEM_FINAL"].unique().tolist())
origem_sel = st.selectbox("Origem", origens)

if origem_sel != "TODAS":
    df_filtro = df_filtro[df_filtro["ORIGEM_FINAL"] == origem_sel]

# =============================
# KPIs MACRO (EVENTOS NO PERÍODO)
# =============================
leads_total = df_filtro["CLIENTE"].nunique()

analises = df_filtro[df_filtro["SITUAÇÃO"] == STATUS_ANALISE]["CLIENTE"].nunique()
aprovados = df_filtro[df_filtro["SITUAÇÃO"] == STATUS_APROVADO]["CLIENTE"].nunique()
vendas = df_filtro[
    df_filtro["SITUAÇÃO"].isin([STATUS_VENDA_GERADA, STATUS_VENDA_INFORMADA])
]["CLIENTE"].nunique()

# Conversões corretas
conv_lead_analise = analises / leads_total if leads_total else 0
conv_analise_aprov = aprovados / analises if analises else 0
conv_analise_venda = vendas / analises if analises else 0
conv_aprov_venda = vendas / aprovados if aprovados else 0

# =============================
# CARDS
# =============================
st.subheader("📌 Performance e Conversão")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads_total)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{conv_lead_analise:.1%}")
c6.metric("Análise → Aprovação", f"{conv_analise_aprov:.1%}")
c7.metric("Análise → Venda", f"{conv_analise_venda:.1%}")
c8.metric("Aprovação → Venda", f"{conv_aprov_venda:.1%}")

# =============================
# AUDITORIA DE CLIENTE
# =============================
st.divider()
st.subheader("🔎 Auditoria Rápida de Cliente")

busca = st.text_input("Digite o nome do cliente")

if busca:
    hist = df[df["CLIENTE"].str.contains(busca.upper(), na=False)]

    if not hist.empty:
        cliente = hist.iloc[-1]

        st.markdown(f"### 👤 {cliente['CLIENTE']}")
        st.write(f"**Situação Atual:** {cliente['SITUAÇÃO']}")
        st.write(f"**Corretor:** {cliente.get('CORRETOR')}")
        st.write(f"**Origem:** {cliente['ORIGEM_FINAL']}")

        st.subheader("Histórico")
        st.dataframe(
            hist.sort_values("DATA")[["DATA", "SITUAÇÃO", "OBSERVAÇÕES"]],
            use_container_width=True
        )
    else:
        st.warning("Cliente não encontrado.")
