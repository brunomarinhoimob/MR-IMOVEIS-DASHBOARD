import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes em Análise – MR Imóveis",
    page_icon="📑",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO MR IMÓVEIS
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    try:
        st.image(LOGO_PATH, use_container_width=True)
    except Exception:
        st.write("MR Imóveis")

with col_tit:
    st.markdown("## Clientes em Análise / Reanálise")
    st.caption(
        "Aqui você acompanha somente clientes cujo **status atual** está como "
        "**EM ANÁLISE** ou **REANÁLISE**, filtrados por período e equipe."
    )


# ---------------------------------------------------------
# FUNÇÃO PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


# ---------------------------------------------------------
# CONFIG DA PLANILHA (MESMO LINK DA PÁGINA CLIENTES MR)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # STATUS
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = None
    for c in possiveis_cols_situacao:
        if c in df.columns:
            col_situacao = c
            break

    df["STATUS_BASE"] = ""
    if col_situacao:
        st_raw = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[st_raw.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[st_raw.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[st_raw.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[st_raw.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[st_raw.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[st_raw.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # Nome
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    if col_nome:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )
    else:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar a planilha.")
    st.stop()


# ---------------------------------------------------------
# PREPARAÇÃO DOS DADOS
# ---------------------------------------------------------
if "NOME_CLIENTE_BASE" in df.columns:
    col_cliente = "NOME_CLIENTE_BASE"
elif "CLIENTE" in df.columns:
    col_cliente = "CLIENTE"
else:
    st.error("Não encontrei a coluna de cliente.")
    st.stop()

if "DIA" not in df.columns:
    st.error("Não encontrei a coluna DIA.")
    st.stop()


df_valid = df.dropna(subset=["DIA"]).copy()
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

status_em_analise = ["EM ANÁLISE", "REANÁLISE"]
df_em_analise_atual = df_status_atual[
    df_status_atual["STATUS_BASE"].isin(status_em_analise)
].copy()

if df_em_analise_atual.empty:
    st.info("Nenhum cliente em análise no momento.")
    st.stop()


# ---------------------------------------------------------
# SELETOR DE PERÍODO (7 / 15 / 30 / 60 / 90 DIAS)
# ---------------------------------------------------------
st.markdown("### 📅 Período de análise")

periodo = st.radio(
    "Selecione o período:",
    [7, 15, 30, 60, 90],
    index=2,  # default 30 dias
    horizontal=True,
)

data_ref = df_valid["DIA"].max()
limite_tempo = data_ref - timedelta(days=periodo)

df_em_analise_atual = df_em_analise_atual[
    df_em_analise_atual["DIA"] >= limite_tempo
].copy()

if df_em_analise_atual.empty:
    st.info(f"Não existem clientes em análise nos últimos {periodo} dias.")
    st.stop()


# ---------------------------------------------------------
# FILTRO POR EQUIPE
# ---------------------------------------------------------
if "EQUIPE" in df_em_analise_atual.columns:
    equipes = (
        df_em_analise_atual["EQUIPE"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    equipe_sel = st.selectbox(
        "Filtrar por equipe:",
        options=["Todas"] + equipes,
        index=0,
    )

    if equipe_sel != "Todas":
        df_filtrado = df_em_analise_atual[
            df_em_analise_atual["EQUIPE"] == equipe_sel
        ].copy()
    else:
        df_filtrado = df_em_analise_atual.copy()
else:
    st.warning("Coluna 'EQUIPE' não encontrada.")
    df_filtrado = df_em_analise_atual.copy()

if df_filtrado.empty:
    st.info("Nenhum cliente encontrado dentro desse filtro.")
    st.stop()


# ---------------------------------------------------------
# KPIs
# ---------------------------------------------------------
total = len(df_filtrado)
qtd_em = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
qtd_re = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()

k1, k2, k3 = st.columns(3)
k1.metric("Total em Análise", total)
k2.metric("Em Análise", qtd_em)
k3.metric("Reanálise", qtd_re)

st.markdown("---")


# ---------------------------------------------------------
# TABELA DETALHADA
# ---------------------------------------------------------
colunas_preferidas = [
    col_cliente,
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "DIA",
]

colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]

st.markdown("### 📋 Lista de clientes em análise")
st.dataframe(
    df_filtrado[colunas_existentes].sort_values("DIA", ascending=False),
    use_container_width=True,
)


# ---------------------------------------------------------
# RESUMO POR EQUIPE
# ---------------------------------------------------------
if "EQUIPE" in df_filtrado.columns:
    st.markdown("### 👥 Clientes em análise por equipe")

    resumo_equipe = (
        df_filtrado.groupby("EQUIPE")[col_cliente]
        .nunique()
        .reset_index(name="Qtde Clientes")
        .sort_values("Qtde Clientes", ascending=False)
    )

    st.dataframe(resumo_equipe, use_container_width=True)
