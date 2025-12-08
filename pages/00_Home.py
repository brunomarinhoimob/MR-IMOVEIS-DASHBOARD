import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------
# CAMINHO DA LOGO (ROBUSTO)
# ----------------------------------------------------
# __file__ -> .../SEU_REPO/pages/00_Home.py
# parent   -> .../SEU_REPO/pages
# parent.parent -> .../SEU_REPO
# logo em: .../SEU_REPO/app_dashboard/logo_mr.png
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = PROJECT_ROOT / "app_dashboard" / "logo_mr.png"

# Se sua logo estiver direto na raiz do projeto (ex.: /logo_mr.png),
# comente a linha de cima e descomente esta:
# LOGO_PATH = PROJECT_ROOT / "logo_mr.png"

# ----------------------------------------------------
# ESTILOS VISUAIS
# ----------------------------------------------------
st.markdown(
    """
    <style>
        .centered {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .card {
            background-color: #111111;
            padding: 55px 40px;
            border-radius: 28px;
            width: 82%;
            max-width: 650px;
            box-shadow: 0px 0px 25px rgba(0,0,0,0.45);
        }

        .logo {
            width: 260px;
            margin-bottom: 20px;
        }

        .phrase {
            font-size: 20px;      /* frase menor pra destacar a logo */
            color: #e8e8e8;
            font-weight: 500;
            margin-top: 10px;
            line-height: 1.35;
        }

        .info {
            margin-top: 35px;
            font-size: 16px;
            color: #cfcfcf;
            line-height: 1.6;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# FUNÇÃO PARA BUSCAR MÊS COMERCIAL REAL DA PLANILHA
# ----------------------------------------------------
def obter_mes_comercial():
    """
    Pega a última data_base da planilha e converte para mês comercial.
    """

    try:
        # ⬇️ AJUSTE AQUI SE A PLANILHA ESTIVER EM OUTRO LOCAL
        df = pd.read_excel(PROJECT_ROOT / "app_dashboard" / "planilhas" / "base_vendas.xlsx")

        df["data_base"] = pd.to_datetime(df["data_base"], errors="coerce")
        ultima_data = df["data_base"].max()

        if pd.isna(ultima_data):
            return "Indefinido"

        return ultima_data.strftime("%B/%Y").capitalize()

    except Exception:
        return "Indefinido"


mes_comercial = obter_mes_comercial()
ultima_atualizacao = datetime.now().strftime("%d/%m/%Y • %H:%M")

# ----------------------------------------------------
# LAYOUT DA HOME
# ----------------------------------------------------
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)

# LOGO MR (com try/except pra não quebrar o app se der ruim)
try:
    st.image(str(LOGO_PATH), use_container_width=False, width=260)
except Exception:
    st.markdown(
        "<div class='phrase'><b>[Logo MR não encontrada no caminho configurado]</b></div>",
        unsafe_allow_html=True,
    )

# FRASE INSTITUCIONAL
st.markdown(
    """
    <div class="phrase">
        Nenhum de nós é tão bom quanto todos nós juntos.
    </div>
    """,
    unsafe_allow_html=True
)

# INFORMAÇÕES DO MÊS E ATUALIZAÇÃO
st.markdown(
    f"""
    <div class="info">
        <b>Mês comercial:</b> {mes_comercial}<br>
        <b>Última atualização:</b> {ultima_atualizacao}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)  # fecha card
st.markdown('</div>', unsafe_allow_html=True)  # fecha centered
