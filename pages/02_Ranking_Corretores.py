import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# (Em app multipage, isso aqui só é considerado se não tiver no app principal)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ranking por Corretor – MR Imóveis",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Ranking por Corretor – MR Imóveis")

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA (DIA)
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

    # STATUS_BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao is not None:
        s = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[s.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV (OBSERVAÇÕES)
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0.0

    # Nome / CPF base para chave de cliente
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

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

# ---------------------------------------------------------
# CARREGAR BASE
# ---------------------------------------------------------
df = carregar_dados()

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

# Garante que temos pelo menos algumas datas válidas
dias_validos = df["DIA"].dropna()
if dias_validos.empty:
    st.error("Não foi possível identificar datas válidas na planilha.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – FILTROS (PERÍODO + EQUIPE + TIPO DE VENDA)
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

data_min = dias_validos.min()
data_max = dias_validos.max()
data_ini_default = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período (DIA)",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)
data_ini, data_fim = periodo

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe (opcional)", ["Todas"] + lista_equipes)

# NOVO FILTRO – tipo de venda a considerar
opcao_venda = st.sidebar.radio(
    "Tipo de venda para o ranking",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA"),
    index=0,
)

if opcao_venda == "Só VENDA GERADA":
    status_venda_considerado = ["VENDA GERADA"]
    desc_venda = "apenas VENDA GERADA"
else:
    status_venda_considerado = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_venda = "VENDA GERADA + VENDA INFORMADA"

# Filtra pela janela de datas selecionada
df_ref = df[
    (df["DIA"] >= data_ini) &
    (df["DIA"] <= data_fim)
].copy()

if equipe_sel != "Todas":
    df_ref = df_ref[df_ref["EQUIPE"] == equipe_sel]

registros_ref = len(df_ref)

st.caption(
    f"Período: {data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
    + ("" if equipe_sel == "Todas" else f" • Equipe: {equipe_sel}")
    + f" • Registros na base: {registros_ref}"
    + f" • Vendas consideradas no ranking: {desc_venda}"
)

if df_ref.empty:
    st.warning("Sem registros para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# CÁLCULOS DE RANKING
# ---------------------------------------------------------

# Análises = EM ANÁLISE + REANÁLISE
mask_analises = df_ref["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])
df_analises = df_ref[mask_analises]

analises_por_corretor = (
    df_analises.groupby("CORRETOR").size().rename("ANALISES")
)

# Aprovações
df_aprov = df_ref[df_ref["STATUS_BASE"] == "APROVADO"]
aprov_por_corretor = df_aprov.groupby("CORRETOR").size().rename("APROVACOES")

# Vendas (1 por cliente) e VGV – usando o filtro de tipo de venda escolhido
df_vendas = df_ref[df_ref["STATUS_BASE"].isin(status_venda_considerado)].copy()

if not df_vendas.empty:
    df_vendas["CHAVE_CLIENTE"] = (
        df_vendas["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_vendas["CPF_CLIENTE_BASE"].fillna("")
    )
    df_vendas = df_vendas.sort_values("DIA")
    # 1 registro por cliente (o último do período)
    df_vendas_ult = df_vendas.groupby("CHAVE_CLIENTE").tail(1)
else:
    df_vendas_ult = df_vendas.copy()

vendas_por_corretor = (
    df_vendas_ult.groupby("CORRETOR").size().rename("VENDAS")
    if not df_vendas_ult.empty
    else pd.Series(dtype=int, name="VENDAS")
)

vgv_por_corretor = (
    df_vendas_ult.groupby("CORRETOR")["VGV"].sum().rename("VGV")
    if not df_vendas_ult.empty
    else pd.Series(dtype=float, name="VGV")
)

# Junta tudo
ranking = (
    pd.concat(
        [analises_por_corretor, aprov_por_corretor, vendas_por_corretor, vgv_por_corretor],
        axis=1,
    )
    .fillna(0)
    .reset_index()
)

if ranking.empty:
    st.warning("Não há dados suficientes para montar o ranking.")
    st.stop()

# Garante tipos
ranking["ANALISES"] = ranking["ANALISES"].astype(int)
ranking["APROVACOES"] = ranking["APROVACOES"].astype(int)
ranking["VENDAS"] = ranking["VENDAS"].astype(int)
ranking["VGV"] = ranking["VGV"].astype(float)

# Taxas
ranking["TAXA_APROV_ANALISES"] = np.where(
    ranking["ANALISES"] > 0,
    ranking["APROVACOES"] / ranking["ANALISES"] * 100,
    0.0,
)
ranking["TAXA_VENDAS_ANALISES"] = np.where(
    ranking["ANALISES"] > 0,
    ranking["VENDAS"] / ranking["ANALISES"] * 100,
    0.0,
)

# Ordenação do ranking: VGV, VENDAS, APROVACOES, ANALISES
ranking = ranking.sort_values(
    by=["VGV", "VENDAS", "APROVACOES", "ANALISES"],
    ascending=[False, False, False, False],
).reset_index(drop=True)

# Posição com medalhas
posicoes = []
for i in range(len(ranking)):
    pos = i + 1
    if pos == 1:
        posicoes.append("🥇 1º")
    elif pos == 2:
        posicoes.append("🥈 2º")
    elif pos == 3:
        posicoes.append("🥉 3º")
    else:
        posicoes.append(f"{pos}º")

ranking["POSICAO"] = posicoes

# ---------------------------------------------------------
# FORMATAÇÃO
# ---------------------------------------------------------
def formata_moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ranking["VGV_FMT"] = ranking["VGV"].apply(formata_moeda)
ranking["TAXA_APROV_ANALISES_FMT"] = ranking["TAXA_APROV_ANALISES"].map(lambda v: f"{v:.1f}%")
ranking["TAXA_VENDAS_ANALISES_FMT"] = ranking["TAXA_VENDAS_ANALISES"].map(lambda v: f"{v:.1f}%")

ranking_exibe = ranking[
    [
        "POSICAO",
        "CORRETOR",
        "VGV_FMT",
        "VENDAS",
        "ANALISES",
        "APROVACOES",
        "TAXA_APROV_ANALISES_FMT",
        "TAXA_VENDAS_ANALISES_FMT",
    ]
].rename(
    columns={
        "POSICAO": "POSIÇÃO",
        "CORRETOR": "CORRETOR",
        "VGV_FMT": "VGV",
        "VENDAS": "VENDAS",
        "ANALISES": "ANÁLISES",
        "APROVACOES": "APROVAÇÕES",
        "TAXA_APROV_ANALISES_FMT": "TAXA_APROV_ANALISES",
        "TAXA_VENDAS_ANALISES_FMT": "TAXA_VENDAS_ANALISES",
    }
)

# ---------------------------------------------------------
# EXIBIÇÃO DA TABELA
# ---------------------------------------------------------
st.markdown("### 📊 Tabela detalhada do ranking por corretor")

st.dataframe(
    ranking_exibe,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# GRÁFICO DE BARRAS – VGV POR CORRETOR
# ---------------------------------------------------------
chart_data = ranking.copy()

chart = (
    alt.Chart(chart_data)
    .mark_bar()
    .encode(
        x=alt.X("CORRETOR:N", sort="-y", title="Corretor"),
        y=alt.Y("VGV:Q", title="VGV"),
        tooltip=[
            alt.Tooltip("CORRETOR:N", title="Corretor"),
            alt.Tooltip("VGV:Q", title="VGV", format=",.2f"),
            alt.Tooltip("VENDAS:Q", title="Vendas"),
            alt.Tooltip("ANALISES:Q", title="Análises"),
            alt.Tooltip("APROVACOES:Q", title="Aprovações"),
            alt.Tooltip("TAXA_APROV_ANALISES:Q", title="% Aprov./Análises", format=".1f"),
            alt.Tooltip("TAXA_VENDAS_ANALISES:Q", title="% Vendas/Análises", format=".1f"),
        ],
    )
    .properties(height=500)
)

st.altair_chart(chart, use_container_width=True)

st.markdown(
    "<hr><p style='text-align:center;color:#666;'>"
    "Ranking por corretor baseado em análises, aprovações, vendas (1 por cliente) e VGV, "
    "filtrado pelo período selecionado e pelo tipo de venda escolhido na barra lateral."
    "</p>",
    unsafe_allow_html=True,
)
