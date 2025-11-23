import streamlit as st
import pandas as pd
from datetime import date, datetime

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Análises Diárias – MR Imóveis",
    page_icon="📅",
    layout="wide",
)

# ---------------------------------------------------------
# ESTILO / CSS
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #050814;
        color: #f5f5f5;
    }

    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }

    .top-banner {
        background: linear-gradient(90deg, #111827, #1f2937);
        padding: 18px 24px;
        border-radius: 20px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.6);
        margin-bottom: 1.5rem;
        border: 1px solid #1f2937;
    }

    .top-banner-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }

    .top-banner-subtitle {
        font-size: 0.95rem;
        color: #9ca3af;
        margin-top: 4px;
        margin-bottom: 0;
    }

    .metric-card {
        background: #111827;
        padding: 16px 20px;
        border-radius: 18px;
        box-shadow: 0 14px 30px rgba(0,0,0,0.55);
        border: 1px solid #1f2937;
        text-align: left;
        margin-bottom: 1rem;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
    }

    .metric-helper {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 4px;
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }

    .section-subtitle {
        font-size: 0.85rem;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }

    .rank-header {
        display: flex;
        align-items: baseline;
        gap: 8px;
    }

    .rank-header span.badge {
        background: #1f2937;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: #9ca3af;
        border: 1px solid #374151;
    }

    .motivational-text {
        font-size: 1rem;
        margin-bottom: 1.5rem;
        color: #e5e7eb;
    }

    .motivational-text span.number {
        font-weight: 700;
        color: #38bdf8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Meta refresh para TV (30 segundos)
st.markdown(
    """
    <meta http-equiv="refresh" content="30">
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CONSTANTES – PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def carregar_dados() -> pd.DataFrame:
    """
    Carrega a base diretamente da planilha (sem cache).
    Essa tela é para TV, então a atualização é em tempo quase real.
    """
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes das colunas
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

    # SITUAÇÃO BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        # As demais situações até podem existir, mas não são usadas neste painel

    return df


def formatar_data_br(d: date) -> str:
    if pd.isna(d):
        return "-"
    return d.strftime("%d/%m/%Y")


def criar_coluna_rank(n: int) -> list:
    """
    Gera uma lista de textos de classificação com medalhas para o TOP 3.
    1 -> 🥇 1º, 2 -> 🥈 2º, 3 -> 🥉 3º, demais -> "4º", "5º"...
    """
    ranks = []
    for i in range(n):
        pos = i + 1
        if pos == 1:
            ranks.append("🥇 1º")
        elif pos == 2:
            ranks.append("🥈 2º")
        elif pos == 3:
            ranks.append("🥉 3º")
        else:
            ranks.append(f"{pos}º")
    return ranks


# ---------------------------------------------------------
# CARREGAR BASE
# ---------------------------------------------------------
df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – SELEÇÃO DO DIA
# ---------------------------------------------------------
st.sidebar.title("Filtro do dia 📅")

dias_validos = df["DIA"].dropna()
if dias_validos.empty:
    st.warning("Ainda não há datas válidas na base.")
    st.stop()

data_min = dias_validos.min()
data_max = dias_validos.max()

# Dia padrão: último dia disponível na base
dia_default = data_max

dia_selecionado = st.sidebar.date_input(
    "Selecione o dia",
    value=dia_default,
    min_value=data_min,
    max_value=data_max,
)

# ---------------------------------------------------------
# FILTRAR BASE PARA O DIA
# ---------------------------------------------------------
df_dia = df[df["DIA"] == dia_selecionado].copy()

# Apenas EM ANÁLISE (sem considerar reanálise)
df_em_analise = df_dia[df_dia["STATUS_BASE"] == "EM ANÁLISE"].copy()

# ---------------------------------------------------------
# CABEÇALHO – BANNER
# ---------------------------------------------------------
col_top_left, col_top_right = st.columns([3, 1])

with col_top_left:
    st.markdown(
        f"""
        <div class="top-banner">
            <div class="top-banner-title">
                📅 Análises Diárias – Gestão à Vista
            </div>
            <p class="top-banner-subtitle">
                Dia <strong>{formatar_data_br(dia_selecionado)}</strong> • 
                Atualiza automaticamente a cada <strong>30 segundos</strong> para acompanhamento em TV.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_top_right:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except Exception:
        pass

# ---------------------------------------------------------
# SE NÃO TIVER ANÁLISES NO DIA
# ---------------------------------------------------------
total_analises = len(df_em_analise)

if total_analises == 0:
    st.markdown(
        """
        <p class="motivational-text">
        Ainda não temos análises cadastradas em <strong>EM ANÁLISE</strong> para este dia.
        Assim que subir a primeira análise, o painel acende na TV. 😉
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------
# MÉTRICAS PRINCIPAIS
# ---------------------------------------------------------
equipes_ativas = df_em_analise["EQUIPE"].nunique()
corretores_ativos = df_em_analise["CORRETOR"].nunique()

st.markdown(
    f"""
    <p class="motivational-text">
        Hoje já registramos <span class="number">{total_analises}</span> análises em 
        <strong>EM ANÁLISE</strong>. Ritmo de foguete rumo à meta! 🚀
    </p>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Análises no dia</div>
            <div class="metric-value">{total_analises}</div>
            <div class="metric-helper">Status: EM ANÁLISE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Equipes ativas</div>
            <div class="metric-value">{equipes_ativas}</div>
            <div class="metric-helper">Subiram pelo menos 1 análise</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Corretores ativos</div>
            <div class="metric-value">{corretores_ativos}</div>
            <div class="metric-helper">Subiram pelo menos 1 análise</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# RANKINGS – EQUIPES E CORRETORES
# ---------------------------------------------------------
st.markdown("")

col_eq, col_cor = st.columns(2)

# -------------------- EQUIPES ----------------------------
with col_eq:
    st.markdown(
        """
        <div class="rank-header">
            <div class="section-title">📌 Análises por Equipe (no dia)</div>
            <span class="badge">Top equipes em EM ANÁLISE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_equipes = df_em_analise.groupby("EQUIPE").size().reset_index(name="ANÁLISES")
    df_equipes = df_equipes.sort_values("ANÁLISES", ascending=False).reset_index(
        drop=True
    )

    df_equipes.insert(0, "POSIÇÃO", criar_coluna_rank(len(df_equipes)))
    df_equipes = df_equipes.rename(
        columns={
            "EQUIPE": "Equipe",
            "ANÁLISES": "Análises no dia",
        }
    )

    st.dataframe(
        df_equipes,
        use_container_width=True,
        hide_index=True,
    )

# -------------------- CORRETORES -------------------------
with col_cor:
    st.markdown(
        """
        <div class="rank-header">
            <div class="section-title">👥 Ranking de Corretores (no dia)</div>
            <span class="badge">Quem está puxando as análises</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_corretor = (
        df_em_analise.groupby("CORRETOR")
        .size()
        .reset_index(name="ANÁLISES")
    )
    df_corretor = df_corretor.sort_values("ANÁLISES", ascending=False).reset_index(
        drop=True
    )

    df_corretor.insert(0, "POSIÇÃO", criar_coluna_rank(len(df_corretor)))
    df_corretor = df_corretor.rename(
        columns={
            "CORRETOR": "Corretor",
            "ANÁLISES": "Análises no dia",
        }
    )

    st.dataframe(
        df_corretor,
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------
# RODAPÉ
# ---------------------------------------------------------
st.markdown("---")
st.caption(
    "Dashboard MR Imóveis • Tela de Gestão à Vista de Análises Diárias • Atualização automática a cada 30s"
)
