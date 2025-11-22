import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ranking por Corretor – MR Imóveis",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Ranking por Corretor – MR Imóveis")

st.caption(
    "Ranking de corretores em análises, aprovações, vendas e VGV "
    "(sempre considerando a ÚLTIMA data base da planilha, sem contar venda duplicada do mesmo cliente)."
)

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA (dia do movimento)
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # DATA BASE (data de fechamento / foto da base)
    possiveis_data_base = ["DATA BASE", "DATA_BASE", "DT BASE", "DATABASE"]
    col_db = None
    for c in possiveis_data_base:
        if c in df.columns:
            col_db = c
            break

    if col_db is not None:
        df["DATA_BASE"] = limpar_para_data(df[col_db])
    else:
        # fallback: se não tiver coluna específica, usa o próprio DIA
        df["DATA_BASE"] = df["DIA"]

    # Equipe / Corretor
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

    # Situação / Status
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

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # Nome / CPF para chave de cliente (anti-duplicidade de venda)
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

    # Chave de cliente (nome + CPF) para controle de venda única
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# ---------------------------------------------------------
# IDENTIFICA A ÚLTIMA DATA BASE
# ---------------------------------------------------------
datas_base_validas = df["DATA_BASE"].dropna()
if datas_base_validas.empty:
    data_base_max = None
else:
    data_base_max = datas_base_validas.max()

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

if data_base_max is not None:
    st.sidebar.markdown(
        f"**Data base utilizada:** {data_base_max.strftime('%d/%m/%Y')}"
    )
else:
    st.sidebar.markdown("**Data base utilizada:** não encontrada na planilha")

# Filtro de equipe
lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe (opcional)", ["Todas"] + lista_equipes)

# ---------------------------------------------------------
# APLICA FILTRO DE DATA BASE E EQUIPE
# ---------------------------------------------------------
df_base = df.copy()

if data_base_max is not None:
    df_base = df_base[df_base["DATA_BASE"] == data_base_max]

if equipe_sel != "Todas":
    df_base = df_base[df_base["EQUIPE"] == equipe_sel]

registros_filtrados = len(df_base)

if data_base_max is not None:
    st.caption(
        f"Data base considerada: **{data_base_max.strftime('%d/%m/%Y')}** • "
        f"Registros: **{registros_filtrados}**"
    )
else:
    st.caption(f"Registros considerados: **{registros_filtrados}**")

if equipe_sel != "Todas":
    st.caption(f"Equipe filtrada: **{equipe_sel}**")

if df_base.empty:
    st.warning("Nenhum registro encontrado para a última data base com os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def conta_analises(s):
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

def conta_aprovacoes(s):
    return (s == "APROVADO").sum()

# ---------------------------------------------------------
# BASE PARA ANÁLISE / APROVAÇÃO (POR LINHA)
# ---------------------------------------------------------
base_analise = (
    df_base
    .groupby("CORRETOR")
    .agg(
        ANALISES=("STATUS_BASE", conta_analises),
        APROVACOES=("STATUS_BASE", conta_aprovacoes),
    )
    .reset_index()
)

# ---------------------------------------------------------
# BASE PARA VENDAS / VGV (POR CLIENTE – ANTI-DUPLICIDADE)
# ---------------------------------------------------------
# Ordena por data para pegar a última linha de cada cliente
df_ord = df_base.sort_values("DIA")

# Última movimentação de cada cliente
df_ult = (
    df_ord
    .dropna(subset=["CHAVE_CLIENTE"])
    .groupby("CHAVE_CLIENTE", as_index=False)
    .tail(1)
)

# Considera venda se o status final for VENDA INFORMADA ou VENDA GERADA
mask_venda_final = df_ult["STATUS_BASE"].isin(["VENDA INFORMADA", "VENDA GERADA"])
df_vendas_clientes = df_ult[mask_venda_final].copy()

vendas_cor = (
    df_vendas_clientes
    .groupby("CORRETOR")
    .agg(
        VENDAS=("STATUS_BASE", "size"),
        VGV=("VGV", "sum"),
    )
    .reset_index()
)

# ---------------------------------------------------------
# JUNTA BASES (ANÁLISE + VENDAS)
# ---------------------------------------------------------
rank_cor = pd.merge(base_analise, vendas_cor, on="CORRETOR", how="left")

rank_cor["VENDAS"] = rank_cor["VENDAS"].fillna(0).astype(int)
rank_cor["VGV"] = rank_cor["VGV"].fillna(0.0)

# Taxas
rank_cor["TAXA_APROV_ANALISES"] = np.where(
    rank_cor["ANALISES"] > 0,
    rank_cor["APROVACOES"] / rank_cor["ANALISES"] * 100,
    0,
)

rank_cor["TAXA_VENDAS_ANALISES"] = np.where(
    rank_cor["ANALISES"] > 0,
    rank_cor["VENDAS"] / rank_cor["ANALISES"] * 100,
    0,
)

# Remove corretores totalmente zerados
rank_cor = rank_cor[
    (rank_cor["ANALISES"] > 0)
    | (rank_cor["APROVACOES"] > 0)
    | (rank_cor["VENDAS"] > 0)
    | (rank_cor["VGV"] > 0)
]

# Ordena e cria posição
rank_cor = rank_cor.sort_values(["VENDAS", "VGV"], ascending=False).reset_index(drop=True)
rank_cor.insert(0, "POSICAO_NUM", rank_cor.index + 1)

def format_posicao(pos):
    if pos == 1:
        return "🥇 1º"
    elif pos == 2:
        return "🥈 2º"
    elif pos == 3:
        return "🥉 3º"
    else:
        return f"{pos}º"

rank_cor["POSICAO"] = rank_cor["POSICAO_NUM"].apply(format_posicao)

# ---------------------------------------------------------
# REORGANIZA COLUNAS PARA FICAR IGUAL AO PRINT
# POSICAO | CORRETOR | VGV | VENDAS | ANALISES | APROVACOES | TAXA_APROV_ANALISES | TAXA_VENDAS_ANALISES
# ---------------------------------------------------------
colunas_ordem = [
    "POSICAO",
    "CORRETOR",
    "VGV",
    "VENDAS",
    "ANALISES",
    "APROVACOES",
    "TAXA_APROV_ANALISES",
    "TAXA_VENDAS_ANALISES",
]
rank_cor = rank_cor[colunas_ordem + ["POSICAO_NUM"]]

# ---------------------------------------------------------
# ESTILO DA TABELA
# ---------------------------------------------------------
st.markdown("#### 📋 Tabela detalhada do ranking por corretor")

def zebra_rows(row):
    base_color_even = "#020617"
    base_color_odd = "#0b1120"
    color = base_color_even if row.name % 2 == 0 else base_color_odd
    return [f"background-color: {color}"] * len(row)

def highlight_top3(row):
    if row.name == 0:
        return ["background-color: rgba(250, 204, 21, 0.18); font-weight: bold;"] * len(row)
    elif row.name == 1:
        return ["background-color: rgba(148, 163, 184, 0.25); font-weight: bold;"] * len(row)
    elif row.name == 2:
        return ["background-color: rgba(248, 250, 252, 0.06); font-weight: bold;"] * len(row)
    else:
        return [""] * len(row)

table_styles = [
    {
        "selector": "th",
        "props": [
            ("background-color", "#0f172a"),
            ("color", "#e5e7eb"),
            ("font-weight", "bold"),
            ("text-align", "center"),
            ("padding", "6px 8px"),
        ],
    },
    {
        "selector": "tbody td",
        "props": [
            ("border", "0px solid transparent"),
            ("padding", "4px 8px"),
            ("font-size", "0.9rem"),
        ],
    },
]

styled_rank = (
    rank_cor.drop(columns=["POSICAO_NUM"])
    .style
    .format(
        {
            "VGV": "R$ {:,.2f}".format,
            "TAXA_APROV_ANALISES": "{:.1f}%".format,
            "TAXA_VENDAS_ANALISES": "{:.1f}%".format,
        }
    )
    .set_table_styles(table_styles)
    .apply(zebra_rows, axis=1)
    .apply(highlight_top3, axis=1)
    .set_properties(
        subset=["POSICAO", "VENDAS", "ANALISES", "APROVACOES"],
        **{"text-align": "center"},
    )
    .set_properties(
        subset=["CORRETOR"],
        **{"text-align": "left"},
    )
    .set_properties(
        subset=["VGV", "TAXA_APROV_ANALISES", "TAXA_VENDAS_ANALISES"],
        **{"text-align": "right"},
    )
)

st.dataframe(
    styled_rank,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# GRÁFICO – VGV POR CORRETOR
# ---------------------------------------------------------
st.markdown("#### 💰 VGV por corretor (última data base)")


chart_vgv = (
    alt.Chart(rank_cor)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("VGV:Q", title="VGV (R$)"),
        y=alt.Y("CORRETOR:N", sort="-x", title="Corretor"),
        tooltip=[
            "CORRETOR",
            "ANALISES",
            "APROVACOES",
            "VENDAS",
            alt.Tooltip("VGV:Q", title="VGV"),
            alt.Tooltip("TAXA_APROV_ANALISES:Q", title="% Aprov./Análises", format=".1f"),
            alt.Tooltip("TAXA_VENDAS_ANALISES:Q", title="% Vendas/Análises", format=".1f"),
        ],
    )
    .properties(height=500)
)

st.altair_chart(chart_vgv, use_container_width=True)

st.markdown(
    "<hr><p style='text-align:center;color:#666;'>"
    "Ranking por corretor baseado na ÚLTIMA data base da planilha, considerando análises, aprovações, "
    "vendas (1 por cliente) e VGV."
    "</p>",
    unsafe_allow_html=True,
)
