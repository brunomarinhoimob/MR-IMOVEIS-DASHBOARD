import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd

from utils.data_loader import carregar_dados_planilha
from utils.bootstrap import iniciar_app
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes MR",
    page_icon="👥",
    layout="wide"
)

# ---------------------------------------------------------
# AUTO REFRESH
# ---------------------------------------------------------
st_autorefresh(interval=30 * 1000, key="auto_refresh_clientes")

# ---------------------------------------------------------
# BOOTSTRAP (LOGIN + NOTIFICAÇÕES)
# ---------------------------------------------------------
iniciar_app()

# =========================================================
# CONTEXTO DO USUÁRIO
# =========================================================
perfil = st.session_state.get("perfil")
nome_corretor_logado = (
    st.session_state.get("nome_usuario", "")
    .upper()
    .strip()
)

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def badge_status(texto):
    texto = (texto or "").upper()
    cores = {
        "EM ANÁLISE": "#2563eb",
        "REANÁLISE": "#9333ea",
        "APROVADO": "#16a34a",
        "APROVADO BACEN": "#f97316",
        "REPROVADO": "#dc2626",
        "VENDA GERADA": "#15803d",
        "VENDA INFORMADA": "#166534",
        "DESISTIU": "#6b7280",
    }
    cor = cores.get(texto, "#374151")
    return f"<span style='background:{cor};color:white;padding:4px 10px;border-radius:12px;font-size:0.85rem;font-weight:600'>{texto}</span>"

def obter_status_atual(grupo):
    grupo = grupo.sort_values("DIA").copy()

    desist = grupo["SITUACAO_ORIGINAL"].str.contains("DESIST", na=False)
    if desist.any():
        grupo = grupo.loc[grupo[desist].index[-1]:]

    vendas = grupo[grupo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]

    return grupo.iloc[-1]

def formatar_observacao(linha):
    texto = (
        linha.get("OBSERVAÇÕES 2")
        if "OBSERVAÇÕES 2" in linha and not pd.isna(linha.get("OBSERVAÇÕES 2"))
        else linha.get("OBSERVAÇÕES")
        if "OBSERVAÇÕES" in linha and not pd.isna(linha.get("OBSERVAÇÕES"))
        else None
    )

    if texto is None:
        return None

    texto = str(texto).strip()
    if texto == "" or texto.lower() == "nan":
        return None

    return texto

# =========================================================
# CARREGAR BASE
# =========================================================
@st.cache_data(ttl=60)
def carregar_base():
    df = carregar_dados_planilha()
    df.columns = df.columns.str.upper().str.strip()

    # Data
    if "DIA" in df:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    # -----------------------------------------------------
    # NOME DO CLIENTE (PRIORIDADE = CLIENTE)
    # -----------------------------------------------------
    if "CLIENTE" in df.columns:
        df["NOME_CLIENTE_BASE"] = (
            df["CLIENTE"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    elif "NOME_CLIENTE_BASE" in df.columns:
        df["NOME_CLIENTE_BASE"] = (
            df["NOME_CLIENTE_BASE"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    elif "NOME" in df.columns:
        df["NOME_CLIENTE_BASE"] = (
            df["NOME"]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["NOME_CLIENTE_BASE"] = ""

    # CPF
    if "CPF_CLIENTE_BASE" in df.columns:
        df["CPF_CLIENTE_BASE"] = (
            df["CPF_CLIENTE_BASE"]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )
    elif "CPF" in df.columns:
        df["CPF_CLIENTE_BASE"] = (
            df["CPF"]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )
    else:
        df["CPF_CLIENTE_BASE"] = ""

    df["CORRETOR"] = df.get("CORRETOR", "").fillna("").astype(str).str.upper().str.strip()
    df["EQUIPE"] = df.get("EQUIPE", "").fillna("").astype(str).str.upper()
    df["CONSTRUTORA"] = df.get("CONSTRUTORA", "").fillna("").astype(str).str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO", "").fillna("").astype(str).str.upper()

    col_sit = next((c for c in ["SITUACAO", "SITUAÇÃO", "STATUS"] if c in df), None)
    df["SITUACAO_ORIGINAL"] = df[col_sit].fillna("").astype(str) if col_sit else ""
    df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    df["CHAVE"] = df["NOME_CLIENTE_BASE"] + "|" + df["CPF_CLIENTE_BASE"]

    return df

df = carregar_base()

# =========================================================
# BUSCA
# =========================================================
st.markdown("## 👥 Clientes – MR")
col1, col2 = st.columns([1, 2])

with col1:
    cpf_busca = st.text_input("CPF do cliente")

with col2:
    nome_busca = st.text_input("Nome do cliente")

if not cpf_busca and not nome_busca:
    st.info("Informe CPF ou nome para buscar.")
    st.stop()

mask = pd.Series(False, index=df.index)

if cpf_busca:
    cpf = cpf_busca.replace(".", "").replace("-", "").strip()
    mask = df["CPF_CLIENTE_BASE"] == cpf

if nome_busca:
    nome = nome_busca.upper().strip()
    mask = mask | df["NOME_CLIENTE_BASE"].str.contains(nome, na=False)

resultado = df[mask].copy()

# ---------------------------------------------------------
# TRAVA DE POSSE
# ---------------------------------------------------------
if perfil == "corretor":
    resultado = resultado[
        (resultado["CORRETOR"] == nome_corretor_logado)
        | (resultado["CORRETOR"] == "")
        | (resultado["CORRETOR"].isna())
    ]

# =========================================================
# EXIBIÇÃO
# =========================================================
if resultado.empty:
    st.warning("Cliente não encontrado ou não pertence à sua carteira.")
    st.stop()

for (chave, corretor), grupo in resultado.groupby(["CHAVE", "CORRETOR"]):
    grupo = grupo.sort_values("DIA").copy()
    ultima = obter_status_atual(grupo)

    st.markdown("---")
    st.markdown(f"### 👤 {ultima['NOME_CLIENTE_BASE']}")
    st.write(f"**CPF:** `{ultima['CPF_CLIENTE_BASE'] or 'NÃO INFORMADO'}`")

    if pd.notna(ultima["DIA"]):
        st.write(f"**Última movimentação:** {ultima['DIA'].strftime('%d/%m/%Y')}")

    st.markdown(
        f"**Situação atual:** {badge_status(ultima['SITUACAO_ORIGINAL'])}",
        unsafe_allow_html=True
    )

    st.write(f"**Corretor:** `{ultima['CORRETOR'] or 'NÃO DEFINIDO'}`")
    st.write(f"**Construtora:** `{ultima['CONSTRUTORA'] or 'NÃO INFORMADO'}`")
    st.write(f"**Empreendimento:** `{ultima['EMPREENDIMENTO'] or 'NÃO INFORMADO'}`")

    obs_final = formatar_observacao(ultima)
    if obs_final:
        st.markdown("### 📝 Observação do cliente")
        st.info(obs_final)

    st.markdown("#### 📜 Linha do tempo do cliente")
    hist = grupo[["DIA", "SITUACAO_ORIGINAL"]].copy()
    hist["DIA"] = hist["DIA"].dt.strftime("%d/%m/%Y")
    hist = hist.rename(columns={"DIA": "Data", "SITUACAO_ORIGINAL": "Situação"})
    st.dataframe(hist, use_container_width=True, hide_index=True)
