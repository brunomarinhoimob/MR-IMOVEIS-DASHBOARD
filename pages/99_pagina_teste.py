import streamlit as st

# ⬇️ AJUSTA AQUI O CAMINHO DA LOGO DA MR
# Exemplo: "images/logo_mr.png" ou "assets/logo_mr.png"
LOGO_MR_PATH = "images/logo_mr.png"  # 👉 TROCA PELO CAMINHO CERTO

st.set_page_config(
    page_title="MR Imóveis | Painel",
    layout="wide",
    page_icon="🏠",
)

# ====== ESTILO GLOBAL (DEIXAR INSTAGRAMÁVEL) ======
custom_css = """
<style>
/* Fundo geral com degradê estilo Instagram/Dark */
.stApp {
    background: radial-gradient(circle at top left, #1f2937 0%, #020617 45%, #000000 100%) !important;
    color: #f9fafb !important;
    font-family: "Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Esconde o rodapé padrão do Streamlit */
footer {visibility: hidden;}
header {visibility: hidden;}

/* Centralização do conteúdo principal */
.main-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

/* Card principal de boas-vindas */
.hero-card {
    background: rgba(15, 23, 42, 0.85);
    border-radius: 24px;
    padding: 32px 40px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65);
    border: 1px solid rgba(148, 163, 184, 0.35);
    backdrop-filter: blur(14px);
}

/* Título principal */
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}

/* Destaque em gradiente no título */
.hero-highlight {
    background: linear-gradient(120deg, #38bdf8, #e5e7eb, #facc15);
    -webkit-background-clip: text;
    color: transparent;
}

/* Subtítulo */
.hero-subtitle {
    font-size: 1.05rem;
    color: #cbd5f5;
    margin-bottom: 1.5rem;
}

/* Linha de “frase de efeito” */
.hero-tagline {
    font-size: 0.90rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: #9ca3af;
    margin-bottom: 1.0rem;
}

/* Cards de KPI estilo Instagram */
.kpi-card {
    background: radial-gradient(circle at top left, #111827 0%, #020617 45%, #000000 100%);
    border-radius: 20px;
    padding: 20px 22px;
    border: 1px solid rgba(55, 65, 81, 0.9);
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.75);
}

.kpi-label {
    font-size: 0.85rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #9ca3af;
    margin-bottom: 0.35rem;
}

.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e5e7eb;
    margin-bottom: 0.25rem;
}

.kpi-detail {
    font-size: 0.85rem;
    color: #6b7280;
}

/* Botões estilizados */
.stButton>button {
    border-radius: 999px;
    padding: 0.55rem 1.7rem;
    border: 1px solid rgba(148, 163, 184, 0.5);
    background: linear-gradient(120deg, #0f172a, #020617);
    color: #e5e7eb;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    box-shadow: 0 14px 30px rgba(0, 0, 0, 0.7);
}

.stButton>button:hover {
    border-color: #38bdf8;
    transform: translateY(-1px);
    box-shadow: 0 18px 40px rgba(56, 189, 248, 0.25);
}

/* Linha discreta no final */
.footer-note {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 1.5rem;
    text-align: center;
}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# ====== LAYOUT ======
st.markdown('<div class="main-container">', unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 3], vertical_alignment="center")

with col_logo:
    try:
        st.image(
            LOGO_MR_PATH,
            use_column_width=True,
        )
    except Exception:
        st.markdown(
            "<p style='color:#9ca3af;font-size:0.8rem;'>⚠️ Ajuste o caminho da logo em <code>LOGO_MR_PATH</code>.</p>",
            unsafe_allow_html=True,
        )

with col_title:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-tagline">Painel de Performance · MR Imóveis</div>
            <div class="hero-title">
                <span class="hero-highlight">MR IMÓVEIS</span><br/>
                Gestão de Resultados em Alto Nível
            </div>
            <div class="hero-subtitle">
                Foco em <strong>VGV, produtividade e conversão</strong> — tudo em um só lugar.
                Essa é a tela pra você bater o olho, sentir o momento da equipe e decidir o próximo passo.
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Botões de navegação (só exemplo de fluxo visual)
    col_b1, col_b2, col_b3 = st.columns([1.2, 1.2, 1.2])
    with col_b1:
        st.button("🚀 Funil de Vendas")
    with col_b2:
        st.button("📊 Dash Equipe")
    with col_b3:
        st.button("🧩 Indicadores")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")  # espaçamento

# ====== CARDS KPI ESTILO INSTAGRAM ======
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="kpi-card">
            <div class="kpi-label">VGV do mês</div>
            <div class="kpi-value">R$ ---,--</div>
            <div class="kpi-detail">Meta batida quando passar a linha dos 100%.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="kpi-card">
            <div class="kpi-label">Vendas</div>
            <div class="kpi-value">--</div>
            <div class="kpi-detail">Quantidade total de unidades vendidas no período.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="kpi-card">
            <div class="kpi-label">Análises de crédito</div>
            <div class="kpi-value">--</div>
            <div class="kpi-detail">Quanto mais análise de qualidade, mais chance de venda.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="footer-note">
        Página inicial instagramável para o dashboard MR Imóveis · pensada para print, palco e resultado.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('</div>', unsafe_allow_html=True)
