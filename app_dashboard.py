import streamlit as st
import pandas as pd
import requests
from datetime import timedelta, datetime

from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Imobiliária – MR Imóveis",
    page_icon="🏠",
    layout="wide",
)

# ---------------------------------------------------------
# ESTILOS GERAIS (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --mr-bg: #020617;
        --mr-bg-card: #020617;
        --mr-bg-card-soft: #020617;
        --mr-accent: #38bdf8;
        --mr-accent-soft: rgba(56,189,248,0.15);
        --mr-text: #e5e7eb;
        --mr-text-soft: #9ca3af;
        --mr-border-soft: rgba(148,163,184,0.3);
    }

    .stApp {
        background: #020617;
        color: var(--mr-text);
    }

    h1, h2, h3 { color: #e5e7eb; }

    div[data-testid="stMetric"] {
        background: #020617;
        padding: 18px;
        border-radius: 16px;
        border: 1px solid var(--mr-border-soft);
    }

    section[data-testid="stSidebar"] {
        background: #020617;
        border-right: 1px solid rgba(148,163,184,0.25);
    }

    .mr-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_data(serie):
    return pd.to_datetime(serie, errors="coerce", dayfirst=True)

def carregar_dados_planilha():
    CSV_URL = st.secrets["planilha_comercial"]["csv_url"]
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    # DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # Normalização
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )

    if "SITUAÇÃO" in df.columns:
        df["SITUAÇÃO"] = (
            df["SITUAÇÃO"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if "DATA BASE" in df.columns:
        df["DATA BASE"] = (
            df["DATA BASE"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.strip()
        )

    return df

# ---------------------------------------------------------
# CARREGAMENTO DOS DADOS
# ---------------------------------------------------------
df = carregar_dados_planilha()

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = df["DIA"].dropna()
data_min = dias_validos.min()
data_max = dias_validos.max()

# ---------------------------------------------------------
# PERÍODO INTELIGENTE (ÚLTIMA DATA BASE)
# ---------------------------------------------------------
data_ini_default = data_min
data_fim_default = data_max

if "DATA BASE" in df.columns:
    df_valid = df[df["DIA"].notna()].copy()
    if not df_valid.empty:
        try:
            ultima_data = df_valid["DIA"].max()
            idx_ultima = df_valid["DIA"].idxmax()
            ultima_base = str(df_valid.loc[idx_ultima, "DATA BASE"]).strip()

            df_mes = df_valid[df_valid["DATA BASE"] == ultima_base]
            if not df_mes.empty:
                data_ini_default = df_mes["DIA"].min()
                data_fim_default = df_mes["DIA"].max()
        except:
            data_ini_default = max(data_min, data_max - timedelta(days=30))
            data_fim_default = data_max
else:
    data_ini_default = max(data_min, data_max - timedelta(days=30))
    data_fim_default = data_max

periodo = st.sidebar.date_input(
    "Período",
    value=(data_ini_default, data_fim_default),
    min_value=data_min,
    max_value=data_max,
)

data_ini, data_fim = periodo

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

if equipe_sel == "Todas":
    base_cor = df
else:
    base_cor = df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# ---------------------------------------------------------
# FILTRAGEM PRINCIPAL
# ---------------------------------------------------------
df_filtrado = df[
    (df["DIA"] >= data_ini) &
    (df["DIA"] <= data_fim)
].copy()

if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)

# ---------------------------------------------------------
# TÍTULO + LOGO
# ---------------------------------------------------------
col_title, col_logo = st.columns([0.8, 0.2])

with col_title:
    st.title("📊 Dashboard Imobiliária – MR Imóveis")
    st.caption(
        f"Período: {data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')} • "
        f"{registros_filtrados} registros"
    )

with col_logo:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except:
        pass

df_status = df_filtrado.copy()

# ---------------------------------------------------------
# KPIs PRINCIPAIS
# ---------------------------------------------------------
em_analise = (df_status["SITUAÇÃO"] == "EM ANÁLISE").sum()
reanalisando = (df_status["SITUAÇÃO"] == "REANÁLISE").sum()
aprovados = df_status["SITUAÇÃO"].isin(["APROVAÇÃO","APROVADO","APROVADO BACEN","APROVADO CAIXA"]).sum()
reprovados = df_status["SITUAÇÃO"].isin(["REPROVAÇÃO","REPROVADO"]).sum()

vendas_geradas = (df_status["SITUAÇÃO"] == "VENDA GERADA").sum()
vendas_informadas = (df_status["SITUAÇÃO"] == "VENDA INFORMADA").sum()
total_vendas = vendas_geradas + vendas_informadas

total_analises = len(df_status)
taxa_aprov = aprovados / total_analises * 100 if total_analises > 0 else 0
taxa_vendas_analise = total_vendas / total_analises * 100 if total_analises > 0 else 0

st.markdown("### 📈 Indicadores de Performance")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Em Análise", em_analise)
col2.metric("Reanálise", reanalisando)
col3.metric("Aprovações", aprovados)
col4.metric("Reprovações", reprovados)

col5, col6, col7 = st.columns(3)
col5.metric("Vendas GERADAS", vendas_geradas)
col6.metric("Vendas INFORMADAS", vendas_informadas)
col7.metric("Total de Vendas", total_vendas)

col8, col9 = st.columns(2)
col8.metric("Aprovação / Análises", f"{taxa_aprov:.1f}%")
col9.metric("Vendas / Análises", f"{taxa_vendas_analise:.1f}%")

# ---------------------------------------------------------
# VGV
# ---------------------------------------------------------
st.markdown("### 💰 VGV")

if "VALOR DO IMÓVEL" in df_status.columns:
    df_status["VALOR_NUM"] = (
        df_status["VALOR DO IMÓVEL"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
        .fillna(0)
    )
    vgv_total = df_status[df_status["SITUAÇÃO"].isin(["VENDA GERADA","VENDA INFORMADA"])]["VALOR_NUM"].sum()
else:
    vgv_total = 0

st.metric("VGV Total", f"R$ {vgv_total:,.2f}")

# ---------------------------------------------------------
# RANKING DE CORRETORES
# ---------------------------------------------------------
st.markdown("### 🏆 Ranking de Corretores")

df_rank = (
    df_status.groupby("CORRETOR")
    .agg(
        Analises=("SITUAÇÃO", "count"),
        Aprovacoes=("SITUAÇÃO", lambda x: (x.isin(["APROVAÇÃO","APROVADO","APROVADO BACEN","APROVADO CAIXA"])).sum()),
        VG=("SITUAÇÃO", lambda x: (x == "VENDA GERADA").sum()),
        VI=("SITUAÇÃO", lambda x: (x == "VENDA INFORMADA").sum()),
    )
    .reset_index()
)

df_rank["Total Vendas"] = df_rank["VG"] + df_rank["VI"]
df_rank = df_rank.sort_values(by="Total Vendas", ascending=False)

st.dataframe(df_rank, hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# TABELA DETALHADA
# ---------------------------------------------------------
st.markdown("### 📋 Tabela Detalhada")

colunas = [c for c in [
    "DIA","DATA BASE","SEMANA","CORRETOR","EQUIPE","CLIENTE",
    "CPF","CONSTRUTORA","EMPREENDIMENTO","RENDA","SITUAÇÃO"
] if c in df_status.columns]

st.dataframe(df_status[colunas], hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("Dashboard MR Imóveis • Desenvolvido em Streamlit • Atualização automática")
