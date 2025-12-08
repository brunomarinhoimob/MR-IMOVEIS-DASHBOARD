import streamlit as st
import pandas as pd
from datetime import datetime

# ----------------------------------------------------
# CONFIGURAÇÃO (DEIXAR A CONFIG PRINCIPAL NO app.py!)
# ----------------------------------------------------
st.markdown(
    """
    <style>
        /* Centralizar tudo */
        .centered {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        /* Card principal */
        .card {
            background-color: #111111;
            padding: 60px 40px;
            border-radius: 28px;
            width: 80%;
            max-width: 650px;
            box-shadow: 0px 0px 25px rgba(0,0,0,0.45);
        }

        /* Frase com fonte menor */
        .phrase {
            font-size: 22px;
            color: #e8e8e8;
            font-weight: 500;
            margin-top: 20px;
            line-height: 1.3;
        }

        /* Infos do mês e atualização */
        .info {
            margin-top: 35px;
            font-size: 16px;
            color: #cfcfcf;
        }

        .logo {
            width: 260px;
            margin-bottom: 15px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# CARREGAR PLANILHA E OBTER O MÊS COMERCIAL
# ----------------------------------------------------

def obter_mes_comercial():
    """
    Retorna o mês comercial baseado na última data_base da planilha.
    """

    try:
        # 🔧 Ajustar o caminho da planilha aqui:
        # df = pd.read_excel("app_dashboard/planilhas/base_vendas.xlsx")

        # -------- Exemplo para simulação (REMOVER DEPOIS) --------
        datas_exemplo = pd.DataFrame({"data_base": ["2025-12-03", "2025-12-05", "2025-12-01"]})
        df = datas_exemplo
        # ---------------------------------------------------------

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
# LAYOUT DA TELA HOME
# ----------------------------------------------------

st.markdown('<div class="centered">', unsafe_allow_html=True)

# CARD
st.markdown('<div class="card">', unsafe_allow_html=True)

# LOGO
st.image("app_dashboard/logo_mr.png", use_container_width=False, width=260)

# FRASE DE IMPACTO – fonte menor
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
st.markdown('</div>', unsafe_allow_html=True)  # fecha centrado
