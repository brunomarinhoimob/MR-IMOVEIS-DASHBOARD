import streamlit as st
import pandas as pd

# =========================================================
# CARREGAMENTO DA PLANILHA (SEM QUALQUER FILTRO)
# =========================================================
@st.cache_data(ttl=60)
def carregar_dados_planilha(_refresh_key=None) -> pd.DataFrame:

    """
    Lê a planilha INTEIRA, sem filtros de data, mês ou base.
    Qualquer filtro deve ser feito SOMENTE nas páginas.
    """

    SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
    GID = "1574157905"

    url = (
        f"https://docs.google.com/spreadsheets/d/"
        f"{SHEET_ID}/export?format=csv&gid={GID}"
    )

    df = pd.read_csv(
        url,
        dtype=str,          # NÃO inferir tipos
        keep_default_na=False
    )

    # normaliza colunas
    df.columns = df.columns.str.upper().str.strip()

    return df
