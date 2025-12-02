import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, datetime, timedelta

from app_dashboard import carregar_dados_planilha
from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Corretores – Visão Geral",
    page_icon="🧑‍💼",
    layout="wide",
)

# ---------------------------------------------------------
# CARREGAMENTO DE DADOS
# ---------------------------------------------------------
# Usa a função padrão do app para carregar a planilha principal
df_planilha = carregar_dados_planilha()

if df_planilha is None or df_planilha.empty:
    st.error("Não foi possível carregar os dados da planilha principal.")
    st.stop()

# Normaliza colunas essenciais
df_planilha = df_planilha.copy()

if "DIA" in df_planilha.columns:
    df_planilha["DIA"] = pd.to_datetime(df_planilha["DIA"], errors="coerce")
elif "DATA" in df_planilha.columns:
    df_planilha["DIA"] = pd.to_datetime(df_planilha["DATA"], errors="coerce")
else:
    df_planilha["DIA"] = pd.NaT

# Normaliza corretor e equipe
df_planilha["CORRETOR_NORM"] = (
    df_planilha.get("CORRETOR", "NÃO INFORMADO")
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)
df_planilha["EQUIPE_NORM"] = (
    df_planilha.get("EQUIPE", "SEM EQUIPE")
    .fillna("SEM EQUIPE")
    .astype(str)
    .str.upper()
    .str.strip()
)

# Status base (STATUS_BASE já vem do app principal normalmente)
if "STATUS_BASE" in df_planilha.columns:
    df_planilha["STATUS_BASE_NORM"] = (
        df_planilha["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
    )
else:
    # fallback a partir de SITUAÇÃO/SITUAÇÃO ATUAL etc.
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next(
        (c for c in possiveis_cols_situacao if c in df_planilha.columns), None
    )
    if col_situacao:
        status = (
            df_planilha[col_situacao]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        status = pd.Series("", index=df_planilha.index)

    df_planilha["STATUS_BASE_NORM"] = ""
    df_planilha.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE_NORM"] = "EM ANÁLISE"
    df_planilha.loc[status.str.contains("REANÁLISE"), "STATUS_BASE_NORM"] = "REANÁLISE"
    df_planilha.loc[status.str.contains("APROVA"), "STATUS_BASE_NORM"] = "APROVADO"
    df_planilha.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE_NORM"] = "VENDA GERADA"
    df_planilha.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE_NORM"] = "VENDA INFORMADA"

# Garante VGV
if "VGV" not in df_planilha.columns:
    if "OBSERVAÇÕES" in df_planilha.columns:
        df_planilha["VGV"] = pd.to_numeric(
            df_planilha["OBSERVAÇÕES"], errors="coerce"
        ).fillna(0.0)
    else:
        df_planilha["VGV"] = 0.0
else:
    df_planilha["VGV"] = pd.to_numeric(df_planilha["VGV"], errors="coerce").fillna(0.0)

# ---------------------------------------------------------
# CSS PERSONALIZADO
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .top-banner {
        background: linear-gradient(90deg, #111827, #1f2937);
        padding: 1.2rem 1.5rem;
        border-radius: 1rem;
        border: 1px solid #374151;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
    }
    .top-banner-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f9fafb;
    }
    .top-banner-subtitle {
        font-size: 0.85rem;
        color: #d1d5db;
        margin-top: 0.2rem;
    }
    .motivational-text {
        font-size: 0.85rem;
        color: #e5e7eb;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: #111827;
        border-radius: 0.9rem;
        padding: 0.9rem 1.1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 10px 25px rgba(15,23,42,0.45);
        height: 100%;
    }
    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 0.2rem;
        color: #f9fafb;
    }
    .metric-help {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 0.45rem;
    }
    .status-pill {
        border-radius: 999px;
        padding: 0.15rem 0.6rem;
        font-size: 0.7rem;
    }
    .status-ativo {
        background-color: rgba(16,185,129,0.12);
        color: #6ee7b7;
    }
    .status-inativo {
        background-color: rgba(248,113,113,0.12);
        color: #fecaca;
    }
    .status-alerta {
        background-color: rgba(251,191,36,0.12);
        color: #facc15;
    }
    .small-badge {
        font-size: 0.7rem;
        padding: 0.05rem 0.35rem;
        border-radius: 999px;
        border: 1px solid #374151;
        color: #9ca3af;
    }

    .dataframe thead tr th {
        background-color: #020617;
        color: #e5e7eb;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .dataframe tbody tr:nth-child(even) {
        background-color: #020617;
    }
    .dataframe tbody tr:nth-child(odd) {
        background-color: #020617;
    }
    .dataframe tbody tr:hover {
        background-color: #111827;
    }
    .dataframe tbody tr td {
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CONSTANTES / ENDPOINTS
# ---------------------------------------------------------
BASE_URL_CORRETORES = "https://api.supremocrm.com.br/v1/corretores"


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_date(col_serie):
    if col_serie is None:
        return pd.NaT
    s = pd.to_datetime(col_serie, errors="coerce")
    return s.dt.date


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_corretores_supremo(pagina=1, por_pagina=100):
    """
    Busca lista de corretores ativos no Supremo CRM para comparar com a planilha.
    """
    headers = {
        "Authorization": f"Bearer {TOKEN_SUPREMO}",
        "Content-Type": "application/json",
    }

    params = {
        "pagina": pagina,
        "por_pagina": por_pagina,
    }

    url = BASE_URL_CORRETORES

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            return pd.DataFrame()

        data_json = resp.json()
        dados = data_json.get("data", [])
        if not dados:
            return pd.DataFrame()

        df_corr = pd.DataFrame(dados)

        df_corr["nome_norm"] = (
            df_corr.get("nome", "")
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
        df_corr["status_norm"] = (
            df_corr.get("status", "")
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

        # Considera ativos somente status "ATIVO"
        df_corr["ATIVO_CRM"] = df_corr["status_norm"] == "ATIVO"

        return df_corr
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_todos_corretores_supremo():
    """
    Pagina na API até trazer todos os corretores.
    """
    pagina_atual = 1
    por_pagina = 100
    dfs = []

    while True:
        df_page = buscar_corretores_supremo(pagina=pagina_atual, por_pagina=por_pagina)
        if df_page.empty:
            break

        dfs.append(df_page)

        pagina_atual += 1
        # Simples trava de segurança para não passar de 20 páginas
        if pagina_atual > 20:
            break

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)
    return df_all


@st.cache_data(ttl=3600, show_spinner=False)
def preparar_base_corretores_supremo():
    df_corr = buscar_todos_corretores_supremo()
    if df_corr.empty:
        return pd.DataFrame()

    # Nome base
    df_corr["NOME_CRM"] = (
        df_corr.get("nome", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
    df_corr["NOME_CRM_BASE"] = df_corr["NOME_CRM"]

    return df_corr


# ---------------------------------------------------------
# LEADS DO CRM (df_leads no session_state)
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame()).copy()

# ---------------------------------------------------------
# PREPARAR BASE DE CORRETORES CRM
# ---------------------------------------------------------
df_corretores_crm = preparar_base_corretores_supremo()

# ---------------------------------------------------------
# AJUSTE LEADS
# ---------------------------------------------------------
if not df_leads.empty:
    if "data_captura_date" not in df_leads.columns and "data_captura" in df_leads.columns:
        df_leads["data_captura"] = pd.to_datetime(
            df_leads["data_captura"], errors="coerce"
        )
        df_leads["data_captura_date"] = df_leads["data_captura"].dt.date
    elif "data_captura_date" not in df_leads.columns:
        df_leads["data_captura_date"] = pd.NaT

    if "nome_corretor_norm" not in df_leads.columns and "nome_corretor" in df_leads.columns:
        df_leads["nome_corretor_norm"] = (
            df_leads["nome_corretor"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    elif "nome_corretor_norm" not in df_leads.columns:
        df_leads["nome_corretor_norm"] = "NÃO INFORMADO"

    if "equipe_lead_norm" not in df_leads.columns and "nome_equipe" in df_leads.columns:
        df_leads["equipe_lead_norm"] = (
            df_leads["nome_equipe"]
            .fillna("SEM EQUIPE")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    elif "equipe_lead_norm" not in df_leads.columns:
        df_leads["equipe_lead_norm"] = "SEM EQUIPE"

# ---------------------------------------------------------
# CORRETORES ATIVOS / INATIVOS (via planilha + CRM)
# ---------------------------------------------------------
# Corretores com qualquer movimento na planilha
corretores_planilha = (
    df_planilha["CORRETOR_NORM"].dropna().unique().tolist()
)

# Corretores CRM
if not df_corretores_crm.empty:
    df_corretores_crm["NOME_CRM_BASE"] = (
        df_corretores_crm["NOME_CRM_BASE"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
    corretores_ativos_crm = df_corretores_crm.loc[
        df_corretores_crm["ATIVO_CRM"], "NOME_CRM_BASE"
    ].tolist()
else:
    corretores_ativos_crm = []

# Marcamos quais corretores da planilha também estão ativos no CRM
corretores_ativos_norm = [
    c for c in corretores_planilha if c in corretores_ativos_crm
]

# Corretores considerados "inativos" pelo CRM
corretores_inativos_norm = [
    c for c in corretores_planilha if c not in corretores_ativos_crm
]

# ---------------------------------------------------------
# CÁLCULO DE ÚLTIMO MOVIMENTO POR CORRETOR (para saber quem está parado)
# ---------------------------------------------------------
df_ult_mov = (
    df_planilha.groupby("CORRETOR_NORM")["DIA"]
    .max()
    .reset_index()
    .rename(columns={"DIA": "ULTIMA_DATA"})
)

hoje = date.today()
df_ult_mov["ULTIMA_DATA_DATE"] = pd.to_datetime(df_ult_mov["ULTIMA_DATA"]).dt.date
df_ult_mov["DIAS_SEM_MOV"] = (hoje - df_ult_mov["ULTIMA_DATA_DATE"]).dt.days

corretores_inativos_30 = df_ult_mov.loc[
    df_ult_mov["DIAS_SEM_MOV"] > 30, "CORRETOR_NORM"
].tolist()

# ---------------------------------------------------------
# FILTROS
# ---------------------------------------------------------
hoje = date.today()
data_ini_padrao = hoje - timedelta(days=60)
data_fim_padrao = hoje

with st.sidebar:
    st.markdown("### Filtros da visão de corretores")

    data_ini = st.date_input(
        "Período inicial",
        value=data_ini_padrao,
        min_value=hoje - timedelta(days=365),
        max_value=hoje,
    )
    data_fim = st.date_input(
        "Período final",
        value=data_fim_padrao,
        min_value=hoje - timedelta(days=365),
        max_value=hoje,
    )

    if data_ini > data_fim:
        st.warning("Período inválido: data inicial maior que data final. Ajustando...")
        data_ini, data_fim = data_fim, data_ini

    equipes_disponiveis = (
        df_planilha["EQUIPE_NORM"].dropna().sort_values().unique().tolist()
    )
    equipes_disponiveis = [e for e in equipes_disponiveis if e != "SEM EQUIPE"]

    equipe_selecionada = st.selectbox(
        "Filtrar por equipe (planilha)",
        options=["TODAS"] + equipes_disponiveis,
        index=0,
    )

    corretores_disponiveis = (
        df_planilha["CORRETOR_NORM"].dropna().sort_values().unique().tolist()
    )
    corretores_disponiveis = [
        c
        for c in corretores_disponiveis
        if c != "NÃO INFORMADO"
        and (not corretores_ativos_norm or c in corretores_ativos_norm)
        and (c not in corretores_inativos_30)
    ]

    corretor_selecionado = st.selectbox(
        "Filtrar por corretor (planilha)",
        options=["TODOS"] + corretores_disponiveis,
        index=0,
    )

    opcao_tipo_venda = st.radio(
        "Tipo de venda considerada",
        ("VENDA GERADA + INFORMADA", "Só VENDA GERADA", "Só VENDA INFORMADA"),
        index=0,
    )

# Mapeia a opção para a lista de status de venda considerada
if opcao_tipo_venda == "Só VENDA GERADA":
    status_vendas_considerados = ["VENDA GERADA"]
elif opcao_tipo_venda == "Só VENDA INFORMADA":
    status_vendas_considerados = ["VENDA INFORMADA"]
else:
    status_vendas_considerados = ["VENDA GERADA", "VENDA INFORMADA"]

# ---------------------------------------------------------
# FILTRAR PLANILHA PELO PERÍODO
# ---------------------------------------------------------
mask_periodo = (
    (df_planilha["DIA"].dt.date >= data_ini)
    & (df_planilha["DIA"].dt.date <= data_fim)
)
df_plan_periodo = df_planilha.loc[mask_periodo].copy()

if equipe_selecionada != "TODAS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["EQUIPE_NORM"] == equipe_selecionada
    ]

if corretor_selecionado != "TODOS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["CORRETOR_NORM"] == corretor_selecionado
    ]

# Limita planilha apenas a corretores que existem na base de corretores_planilha
df_plan_periodo = df_plan_periodo[
    df_plan_periodo["CORRETOR_NORM"].isin(corretores_planilha)
]

# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------
col_header_left, col_header_right = st.columns([3, 1])

with col_header_left:
    st.markdown(
        f"""
        <div class="top-banner">
            <div>
                <div class="top-banner-title">
                    🧑‍💼 Corretores – Visão Geral
                </div>
                <p class="top-banner-subtitle">
                    Integrando <strong>planilha de produção</strong> e <strong>leads</strong> para enxergar a performance da equipe.
                    <br>
                    Período analisado: <strong>{data_ini.strftime('%d/%m/%Y')}</strong> até <strong>{data_fim.strftime('%d/%m/%Y')}</strong>.
                    <br>
                    Vendas consideradas: <strong>{opcao_tipo_venda}</strong>.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_header_right:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except Exception:
        pass

st.markdown(
    """
    <p class="motivational-text">
        <strong>Ninguém é tão bom quanto todos nós juntos!</strong> 🤝✨<br>
        Aqui você enxerga quem está jogando o jogo de verdade: CRM, leads, análises e vendas.
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# INDICADORES GERAIS
# ---------------------------------------------------------
df_rank_base = df_plan_periodo.copy()

# Remove corretores CRM inativos e também inativos >30 dias (planilha + CRM)
if corretores_ativos_norm:
    df_rank_base = df_rank_base[
        df_rank_base["CORRETOR_NORM"].isin(corretores_ativos_norm)
    ]

if corretores_inativos_30:
    df_rank_base = df_rank_base[
        ~df_rank_base["CORRETOR_NORM"].isin(corretores_inativos_30)
    ]

if "STATUS_BASE_NORM" not in df_rank_base.columns:
    df_rank_base["STATUS_BASE_NORM"] = ""

df_rank_base["IS_ANALISE"] = df_rank_base["STATUS_BASE_NORM"].isin(
    ["EM ANÁLISE", "REANÁLISE"]
)
df_rank_base["IS_APROV"] = df_rank_base["STATUS_BASE_NORM"].str.contains(
    "APROV", na=False
)

# Tipo registro (garantir que exista)
if "TIPO_REGISTRO" in df_rank_base.columns:
    df_rank_base["TIPO_REGISTRO"] = (
        df_rank_base["TIPO_REGISTRO"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_rank_base["TIPO_REGISTRO"] = ""

# ---------------------------------------------------------
# VENDA / VGV – usando STATUS_BASE e VGV da planilha
# ---------------------------------------------------------
df_rank_base["IS_VENDA"] = df_rank_base["STATUS_BASE_NORM"].isin(status_vendas_considerados)

df_rank_base["VGV_VENDA"] = np.where(
    df_rank_base["IS_VENDA"], df_rank_base["VGV"], 0.0
)

# Indicadores gerais
total_analises = int(df_rank_base["IS_ANALISE"].sum())
total_aprovacoes = int(df_rank_base["IS_APROV"].sum())
total_vendas = int(df_rank_base["IS_VENDA"].sum())
total_vgv = float(df_rank_base["VGV_VENDA"].sum())

qtde_corretores_com_movimento = int(
    df_rank_base.loc[
        (df_rank_base["IS_ANALISE"])
        | (df_rank_base["IS_APROV"])
        | (df_rank_base["IS_VENDA"])
    ]["CORRETOR_NORM"]
    .nunique()
)

# Leads no período
if not df_leads.empty:
    df_leads_use = df_leads.dropna(subset=["data_captura_date"]).copy()
    mask_leads_periodo = (
        (df_leads_use["data_captura_date"] >= data_ini)
        & (df_leads_use["data_captura_date"] <= data_fim)
    )
    df_leads_periodo = df_leads_use.loc[mask_leads_periodo].copy()

    if equipe_selecionada != "TODAS":
        df_leads_periodo = df_leads_periodo[
            df_leads_periodo["equipe_lead_norm"] == equipe_selecionada
        ]

    if corretor_selecionado != "TODOS":
        df_leads_periodo = df_leads_periodo[
            df_leads_periodo["nome_corretor_norm"] == corretor_selecionado
        ]

    # tira corretores considerados inativos >30 dias
    if corretores_inativos_30:
        df_leads_periodo = df_leads_periodo[
            ~df_leads_periodo["nome_corretor_norm"].isin(corretores_inativos_30)
        ]
else:
    df_leads_periodo = pd.DataFrame(columns=df_leads.columns)

total_leads_periodo = len(df_leads_periodo)

df_corretores_crm_ativos = df_corretores_crm[
    df_corretores_crm["ATIVO_CRM"]
].copy()
qtde_corretores_crm_ativos = df_corretores_crm_ativos["NOME_CRM_BASE"].nunique()

# ---------------------------------------------------------
# CARDS PRINCIPAIS
# ---------------------------------------------------------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Corretores ativos no CRM</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{qtde_corretores_crm_ativos}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Corretores marcados como "ATIVO" no Supremo CRM.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Corretores com movimento</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{qtde_corretores_com_movimento}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Quantidade de corretores com alguma análise, aprovação ou venda no período.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Produção do período</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{total_vendas} vendas</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-help">{total_analises} análises • {total_aprovacoes} aprovações • VGV R$ {total_vgv:,.0f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Leads capturados</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{total_leads_periodo}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Leads do período considerando filtros.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PAINEL DE CORRETORES (TABELA)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Painel de Corretores")

agrup_cols = ["CORRETOR_NORM", "EQUIPE_NORM"]

df_rank = (
    df_rank_base.groupby(agrup_cols)
    .agg(
        ANALISES=("IS_ANALISE", "sum"),
        APROVACOES=("IS_APROV", "sum"),
        VENDAS=("IS_VENDA", "sum"),
        VGV=("VGV_VENDA", "sum"),
    )
    .reset_index()
)

# Junta com leads por corretor no período
if not df_leads_periodo.empty:
    df_leads_corr = (
        df_leads_periodo.groupby("nome_corretor_norm")
        .size()
        .reset_index(name="LEADS")
    )
    df_leads_corr["nome_corretor_norm"] = (
        df_leads_corr["nome_corretor_norm"].astype(str).str.upper().str.strip()
    )
else:
    df_leads_corr = pd.DataFrame(columns=["nome_corretor_norm", "LEADS"])

df_rank = df_rank.merge(
    df_leads_corr,
    left_on="CORRETOR_NORM",
    right_on="nome_corretor_norm",
    how="left",
)
df_rank["LEADS"] = df_rank["LEADS"].fillna(0).astype(int)
df_rank = df_rank.drop(columns=["nome_corretor_norm"], errors="ignore")

# Conversões
df_rank["CONV_ANALISE_VENDA"] = np.where(
    df_rank["ANALISES"] > 0,
    df_rank["VENDAS"] / df_rank["ANALISES"] * 100,
    0.0,
)
df_rank["CONV_APROV_VENDA"] = np.where(
    df_rank["APROVACOES"] > 0,
    df_rank["VENDAS"] / df_rank["APROVACOES"] * 100,
    0.0,
)

# Dias sem movimento
df_rank = df_rank.merge(
    df_ult_mov[["CORRETOR_NORM", "DIAS_SEM_MOV"]],
    on="CORRETOR_NORM",
    how="left",
)

# Ordenação
df_rank = df_rank.sort_values(["EQUIPE_NORM", "VGV"], ascending=[True, False])

# Tabela final para visualização
df_tabela = df_rank.copy()
df_tabela["DIAS_SEM_MOV"] = df_tabela["DIAS_SEM_MOV"].fillna(999).astype(int)
df_tabela["DIAS_SEM_MOV_TXT"] = np.where(
    df_tabela["DIAS_SEM_MOV"] == 999,
    "Sem info",
    df_tabela["DIAS_SEM_MOV"].astype(str) + " dias",
)

# Ajuste de colunas para visualização
colunas_exibir = [
    "EQUIPE_NORM",
    "CORRETOR_NORM",
    "LEADS",
    "ANALISES",
    "APROVACOES",
    "VENDAS",
    "VGV",
    "CONV_ANALISE_VENDA",
    "CONV_APROV_VENDA",
    "DIAS_SEM_MOV_TXT",
]

df_tabela_view = df_tabela[colunas_exibir].copy()

df_tabela_view = df_tabela_view.rename(
    columns={
        "EQUIPE_NORM": "Equipe",
        "CORRETOR_NORM": "Corretor (planilha)",
        "LEADS": "Leads",
        "ANALISES": "Análises",
        "APROVACOES": "Aprovações",
        "VENDAS": "Vendas",
        "VGV": "VGV",
        "CONV_ANALISE_VENDA": "% Conv. Análise → Venda",
        "CONV_APROV_VENDA": "% Conv. Aprov. → Venda",
        "DIAS_SEM_MOV_TXT": "Dias sem movimento",
    }
)

st.dataframe(
    df_tabela_view.style.format(
        {
            "VGV": "R$ {:,.2f}".format,
            "% Conv. Análise → Venda": "{:.1f}%".format,
            "% Conv. Aprov. → Venda": "{:.1f}%".format,
        }
    ),
    use_container_width=True,
    hide_index=True,
)
