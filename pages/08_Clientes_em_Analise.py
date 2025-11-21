import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

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
        "Aqui você acompanha apenas os clientes cujo **status atual** na planilha "
        "está como **EM ANÁLISE** ou **REANÁLISE**, independente de quantas "
        "linhas anteriores eles já tiveram (aprovado, venda, etc.)."
    )


# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA – MESMA DA PÁGINA DE CLIENTES
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS (MESMA LÓGICA DA PÁGINA CLIENTES MR)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
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
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # CONSTRUTORA / EMPREENDIMENTO
    possiveis_construtora = ["CONSTRUTORA", "INCORPORADORA"]
    possiveis_empreend = ["EMPREENDIMENTO", "PRODUTO", "IMÓVEL", "IMOVEL"]

    col_construtora = None
    for c in possiveis_construtora:
        if c in df.columns:
            col_construtora = c
            break

    col_empreend = None
    for c in possiveis_empreend:
        if c in df.columns:
            col_empreend = c
            break

    if col_construtora is None:
        df["CONSTRUTORA_BASE"] = "NÃO INFORMADO"
    else:
        df["CONSTRUTORA_BASE"] = (
            df[col_construtora].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_empreend is None:
        df["EMPREENDIMENTO_BASE"] = "NÃO INFORMADO"
    else:
        df["EMPREENDIMENTO_BASE"] = (
            df[col_empreend].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    # STATUS BASE + SITUAÇÃO ORIGINAL
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
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

        df["SITUACAO_ORIGINAL"] = (
            df[col_situacao].fillna("").astype(str).str.upper().str.strip()
        )
    else:
        df["SITUACAO_ORIGINAL"] = "NÃO INFORMADO"

    # OBSERVAÇÕES / VGV
    if "OBSERVAÇÕES" in df.columns:
        df["OBSERVACOES_RAW"] = (
            df["OBSERVAÇÕES"].fillna("").astype(str).str.strip()
        )
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["OBSERVACOES_RAW"] = ""
        df["VGV"] = 0.0

    # NOME / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    col_cpf = None
    for c in possiveis_cpf:
        if c in df.columns:
            col_cpf = c
            break

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link.")
    st.stop()

# ---------------------------------------------------------
# LÓGICA: PEGAR APENAS STATUS ATUAL EM ANÁLISE / REANÁLISE
# ---------------------------------------------------------

# coluna de cliente
if "NOME_CLIENTE_BASE" in df.columns:
    col_cliente = "NOME_CLIENTE_BASE"
elif "CLIENTE" in df.columns:
    col_cliente = "CLIENTE"
else:
    st.error("Não encontrei coluna de cliente (NOME_CLIENTE_BASE / CLIENTE).")
    st.stop()

if "DIA" not in df.columns:
    st.error("Não encontrei coluna DIA.")
    st.stop()

# Ordena por cliente + data
df_valid = df.dropna(subset=["DIA"]).copy()
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

# Último registro de cada cliente = status atual
df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

# Filtra EM ANÁLISE / REANÁLISE
status_em_analise = ["EM ANÁLISE", "REANÁLISE"]
df_em_analise_atual = df_status_atual[
    df_status_atual["STATUS_BASE"].isin(status_em_analise)
].copy()

if df_em_analise_atual.empty:
    st.success("No momento, nenhum cliente está com status EM ANÁLISE ou REANÁLISE. 👏")
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

    equipe_selecionada = st.selectbox(
        "Filtrar por equipe:",
        options=["Todas"] + equipes,
        index=0,
    )

    if equipe_selecionada != "Todas":
        df_filtrado = df_em_analise_atual[
            df_em_analise_atual["EQUIPE"] == equipe_selecionada
        ].copy()
    else:
        df_filtrado = df_em_analise_atual.copy()
else:
    st.warning("Coluna 'EQUIPE' não encontrada. Filtro por equipe desativado.")
    df_filtrado = df_em_analise_atual.copy()

if df_filtrado.empty:
    st.info("Não há clientes em análise para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# KPIs
# ---------------------------------------------------------
total_em_analise = len(df_filtrado)
qtd_em_analise = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
qtd_reanalise = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()

c1, c2, c3 = st.columns(3)
c1.metric("Total em Análise (atual)", total_em_analise)
c2.metric("Em Análise", int(qtd_em_analise))
c3.metric("Reanálise", int(qtd_reanalise))

st.markdown("---")

# ---------------------------------------------------------
# TABELA DETALHADA
# ---------------------------------------------------------
colunas_preferidas = [
    col_cliente,
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "DIA",
]
colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]

st.markdown("### 📋 Lista de clientes em análise (status atual)")
st.dataframe(
    df_filtrado[colunas_existentes].sort_values("DIA", ascending=False),
    use_container_width=True,
)

# ---------------------------------------------------------
# RESUMO POR EQUIPE
# ---------------------------------------------------------
if "EQUIPE" in df_filtrado.columns:
    st.markdown("### 👥 Quantidade de clientes em análise por equipe")
    resumo_equipe = (
        df_filtrado.groupby("EQUIPE")[col_cliente]
        .nunique()
        .reset_index(name="Qtde Clientes")
        .sort_values("Qtde Clientes", ascending=False)
    )
    st.dataframe(resumo_equipe, use_container_width=True)
