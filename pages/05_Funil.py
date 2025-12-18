import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
import io
from datetime import date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (TEM QUE SER O 1º st.* DO ARQUIVO)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil MR Imóveis – Visão Geral",
    page_icon="🧩",
    layout="wide",
)

# ---------------------------------------------------------
# 🔒 BLOQUEIO DE LOGIN
# ---------------------------------------------------------
if "logado" not in st.session_state or not st.session_state.get("logado", False):
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

# ---------------------------------------------------------
# PLANILHA (SEM IMPORTAR app_dashboard)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=600)
def carregar_dados_planilha() -> pd.DataFrame:
    """
    Carrega a planilha via export CSV (robusto contra redirect do Google).
    """
    r = requests.get(
        CSV_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    # Se o Google mandar erro, cai aqui
    r.raise_for_status()

    # Se vier HTML, geralmente é login/permissão
    head = (r.text or "").lower()[:400]
    if "<html" in head:
        raise RuntimeError(
            "O Google devolveu HTML (provável login/permissão). "
            "Confere se a planilha está compartilhada como 'Qualquer pessoa com o link: Leitor'."
        )

    return pd.read_csv(io.StringIO(r.text))

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def mes_ano_ptbr_para_date(texto: str):
    """Converte 'novembro 2025' -> date(2025, 11, 1)."""
    if not isinstance(texto, str):
        return pd.NaT

    t = texto.strip().lower()
    if not t:
        return pd.NaT

    partes = t.split()
    if len(partes) != 2:
        return pd.NaT

    mes_nome, ano_str = partes[0], partes[1]

    mapa_meses = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }

    mes = mapa_meses.get(mes_nome)
    if mes is None:
        return pd.NaT

    try:
        ano = int(ano_str)
        return date(ano, mes, 1)
    except:
        return pd.NaT


def conta_analises_total(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()


def conta_analises_base(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    # "APROVADO BACEN" NÃO entra aqui, pq não é igual a "APROVADO"
    return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame, status_venda=None, status_final_map=None):
    """
    1 venda por cliente.
    Remove DESISTIU (se status_final_map for passado).
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(status_venda)].copy()
    if df_v.empty:
        return df_v

    # Nome
    possiveis_nome = ["NOME_CLIENTE_BASE", "NOME", "CLIENTE", "NOME CLIENTE"]
    for c in possiveis_nome:
        if c in df_v.columns:
            df_v["NOME_CLIENTE_BASE"] = (
                df_v[c].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
            )
            break
    else:
        df_v["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    # CPF
    possiveis_cpf = ["CPF_CLIENTE_BASE", "CPF", "CPF CLIENTE"]
    for c in possiveis_cpf:
        if c in df_v.columns:
            df_v["CPF_CLIENTE_BASE"] = (
                df_v[c].fillna("").astype(str).str.replace(r"\D", "", regex=True)
            )
            break
    else:
        df_v["CPF_CLIENTE_BASE"] = ""

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO").astype(str)
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("").astype(str)
    )

    # remove DESISTIU
    if status_final_map is not None:
        df_v = df_v.merge(status_final_map, on="CHAVE_CLIENTE", how="left")
        df_v = df_v[df_v["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if df_v.empty:
        return df_v

    df_v = df_v.sort_values("DIA")
    df_ult = df_v.groupby("CHAVE_CLIENTE").tail(1).copy()
    return df_ult


def format_currency(v: float) -> str:
    try:
        v = float(v)
    except:
        v = 0.0
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------
# CARREGAMENTO GERAL DA PLANILHA
# ---------------------------------------------------------
try:
    df_global = carregar_dados_planilha()
except Exception as e:
    st.error(f"Erro ao carregar a planilha: {e}")
    st.stop()

if df_global.empty:
    st.error("Planilha vazia ou não carregou.")
    st.stop()

# Padroniza datas
df_global["DIA"] = pd.to_datetime(df_global.get("DIA"), errors="coerce")

# DATA BASE
if "DATA BASE" in df_global.columns:
    base_raw = df_global["DATA BASE"].astype(str).str.strip()
    df_global["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)
    df_global["DATA_BASE_LABEL"] = df_global["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    df_global["DATA_BASE"] = df_global["DIA"]
    df_global["DATA_BASE_LABEL"] = df_global["DIA"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )

# STATUS_BASE padronizado
df_global["STATUS_BASE"] = (
    df_global.get("STATUS_BASE", "")
    .fillna("")
    .astype(str)
    .str.upper()
)
df_global.loc[df_global["STATUS_BASE"].str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

# Nome / CPF / CHAVE_CLIENTE
possiveis_nome = ["NOME_CLIENTE_BASE", "NOME", "CLIENTE"]
col_nome = next((c for c in possiveis_nome if c in df_global.columns), None)

if col_nome:
    df_global["NOME_CLIENTE_BASE"] = (
        df_global[col_nome]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_global["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

possiveis_cpf = ["CPF_CLIENTE_BASE", "CPF", "CPF CLIENTE"]
col_cpf = next((c for c in possiveis_cpf if c in df_global.columns), None)

if col_cpf:
    df_global["CPF_CLIENTE_BASE"] = (
        df_global[col_cpf]
        .fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )
else:
    df_global["CPF_CLIENTE_BASE"] = ""

df_global["CHAVE_CLIENTE"] = (
    df_global["NOME_CLIENTE_BASE"].astype(str)
    + " | "
    + df_global["CPF_CLIENTE_BASE"].astype(str)
)

# STATUS FINAL por cliente
df_ord = df_global.sort_values("DIA")
status_final_por_cliente = (
    df_ord.groupby("CHAVE_CLIENTE")["STATUS_BASE"]
    .last()
    .fillna("")
    .astype(str)
    .str.upper()
)
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"

# ---------------------------------------------------------
# LISTAS DE EQUIPES E CORRETORES
# ---------------------------------------------------------
if "EQUIPE" not in df_global.columns:
    st.error("A planilha não possui a coluna 'EQUIPE'.")
    st.stop()

if "CORRETOR" not in df_global.columns:
    st.error("A planilha não possui a coluna 'CORRETOR'.")
    st.stop()

lista_equipes = sorted(df_global["EQUIPE"].dropna().astype(str).unique())

mapa_corretores = (
    df_global[["EQUIPE", "CORRETOR"]]
    .dropna()
    .astype(str)
    .drop_duplicates()
)

# ---------------------------------------------------------
# SIDEBAR – SELETOR DE VISÃO (MR / EQUIPE / CORRETOR)
# ---------------------------------------------------------
st.sidebar.title("Visão da análise")

visao = st.sidebar.radio(
    "Selecione a visão:",
    ["MR IMÓVEIS", "Equipe", "Corretor"],
    index=0
)

equipe_sel = None
corretor_sel = None

if visao == "Equipe":
    equipe_sel = st.sidebar.selectbox("Selecione a equipe:", lista_equipes)

if visao == "Corretor":
    equipe_sel = st.sidebar.selectbox("Equipe do corretor:", lista_equipes)
    lista_corr = (
        mapa_corretores[mapa_corretores["EQUIPE"] == equipe_sel]["CORRETOR"]
        .dropna()
        .astype(str)
        .unique()
    )
    corretor_sel = st.sidebar.selectbox("Selecione o corretor:", lista_corr)

# ---------------------------------------------------------
# DEFINIÇÃO DO DATAFRAME BASE (df_view) DEPENDENDO DA VISÃO
# ---------------------------------------------------------
if visao == "MR IMÓVEIS":
    df_view = df_global.copy()
elif visao == "Equipe":
    df_view = df_global[df_global["EQUIPE"] == equipe_sel].copy()
elif visao == "Corretor":
    df_view = df_global[
        (df_global["EQUIPE"] == equipe_sel)
        & (df_global["CORRETOR"] == corretor_sel)
    ].copy()
else:
    df_view = df_global.copy()

if df_view.empty:
    st.warning("Não há dados para a seleção atual.")
    st.stop()

# ---------------------------------------------------------
# FILTRO AUTOMÁTICO PARA CORRETOR LOGADO
# ---------------------------------------------------------
if st.session_state.get("perfil") == "corretor":
    nome_corretor_logado = (
        st.session_state.get("nome_usuario", "")
        .upper()
        .strip()
    )
    df_view = df_view[
        df_view["CORRETOR"].astype(str).str.upper().str.strip() == nome_corretor_logado
    ]

if df_view.empty:
    st.warning("Sem dados para o corretor logado nesta visão.")
    st.stop()

# ---------------------------------------------------------
# IDENTIFICA A ÚLTIMA DATA BASE (ATUAL) E LISTA DE BASES
# ---------------------------------------------------------
bases_validas = pd.to_datetime(df_view["DATA_BASE"], errors="coerce").dropna()
if bases_validas.empty:
    st.error("Não há DATA BASE válida para a visão atual.")
    st.stop()

DATA_BASE_ATUAL = bases_validas.max()
DATA_BASE_ATUAL_LABEL = pd.Timestamp(DATA_BASE_ATUAL).strftime("%m/%Y")

bases_unicas = sorted(bases_validas.unique())
bases_labels = [pd.Timestamp(b).strftime("%m/%Y") for b in bases_unicas]

idx_default_base = (
    bases_labels.index(DATA_BASE_ATUAL_LABEL)
    if DATA_BASE_ATUAL_LABEL in bases_labels
    else len(bases_labels) - 1
)

col_t1, col_t2 = st.columns([3, 1])
with col_t2:
    base_label_escolhida = st.selectbox(
        "Data base (apenas este painel):",
        options=bases_labels,
        index=idx_default_base,
    )

idx_sel = bases_labels.index(base_label_escolhida)
DATA_BASE_PAINEL = pd.Timestamp(bases_unicas[idx_sel])
DATA_BASE_PAINEL_LABEL = base_label_escolhida

with col_t1:
    st.markdown(f"## 🟦 Funil da Data Base – {DATA_BASE_PAINEL_LABEL}")

df_base_atual = df_view[
    pd.to_datetime(df_view["DATA_BASE"], errors="coerce") == DATA_BASE_ATUAL
].copy()

# ---------------------------------------------------------
# 🔥 PAINEL 1 — FUNIL DA DATA BASE SELECIONADA
# ---------------------------------------------------------
df_painel = df_view[
    pd.to_datetime(df_view["DATA_BASE"], errors="coerce") == DATA_BASE_PAINEL
].copy()

if df_painel.empty:
    analises_em = 0
    reanalises = 0
    analises_total = 0
    aprovacoes = 0
    vendas = 0
    vgv_total = 0
    ipc = 0
else:
    status_atual = df_painel["STATUS_BASE"].fillna("").astype(str).str.upper()

    analises_em = conta_analises_base(status_atual)
    reanalises = conta_reanalises(status_atual)
    analises_total = conta_analises_total(status_atual)
    aprovacoes = conta_aprovacoes(status_atual)

    df_vendas_atual = obter_vendas_unicas(
        df_painel,
        status_venda=["VENDA GERADA"],
        status_final_map=status_final_por_cliente
    )
    vendas = len(df_vendas_atual)

    if vendas > 0 and "VGV" in df_vendas_atual.columns:
        df_vendas_atual["VGV"] = pd.to_numeric(df_vendas_atual["VGV"], errors="coerce").fillna(0)
        vgv_total = float(df_vendas_atual["VGV"].sum())
    else:
        vgv_total = 0.0

    if visao == "Corretor":
        ipc = vendas
    else:
        corretores_ativos = df_painel["CORRETOR"].dropna().astype(str).nunique()
        ipc = (vendas / corretores_ativos) if corretores_ativos > 0 else 0

# ---------------------------------------------------------
# 🔥 LEADS DO CRM (apenas período da data base selecionada)
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame())

total_leads = None
conv_leads_analise = None
leads_por_analise = None

if not df_leads.empty:
    df_leads_use = df_leads.copy()
    df_leads_use["data_captura"] = pd.to_datetime(df_leads_use.get("data_captura"), errors="coerce")
    df_leads_use = df_leads_use.dropna(subset=["data_captura"])
    df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date

    df_leads_use["CORRETOR_KEY"] = (
        df_leads_use.get("nome_corretor", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    mapa_cor = (
        df_global[["CORRETOR", "EQUIPE"]]
        .dropna()
        .astype(str)
        .drop_duplicates()
    )
    mapa_cor["CORRETOR_KEY"] = mapa_cor["CORRETOR"].str.upper().str.strip()

    df_leads_merge = df_leads_use.merge(
        mapa_cor[["CORRETOR_KEY", "EQUIPE"]],
        on="CORRETOR_KEY",
        how="left"
    )

    if visao == "MR IMÓVEIS":
        df_leads_filtrado = df_leads_merge.copy()
    elif visao == "Equipe":
        df_leads_filtrado = df_leads_merge[df_leads_merge["EQUIPE"] == equipe_sel]
    elif visao == "Corretor":
        df_leads_filtrado = df_leads_merge[df_leads_merge["CORRETOR_KEY"] == corretor_sel.upper().strip()]
    else:
        df_leads_filtrado = df_leads_merge.copy()

    dias_validos = df_painel["DIA"].dropna()
    if not dias_validos.empty:
        dia_ini = dias_validos.min().date()
        dia_fim = dias_validos.max().date()
    else:
        dia_ini = date.today()
        dia_fim = date.today()

    mask_periodo = (
        (df_leads_filtrado["data_captura_date"] >= dia_ini)
        & (df_leads_filtrado["data_captura_date"] <= dia_fim)
    )
    df_leads_periodo = df_leads_filtrado[mask_periodo].copy()

    total_leads = len(df_leads_periodo)
    if total_leads > 0:
        conv_leads_analise = (analises_em / total_leads * 100) if analises_em else 0
        leads_por_analise = (total_leads / analises_em) if analises_em else None
    else:
        conv_leads_analise = 0
        leads_por_analise = None

# ---------------------------------------------------------
# EXIBIÇÃO DO PAINEL 1
# ---------------------------------------------------------
st.markdown("### 🔎 Indicadores principais da data base selecionada")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Análises (EM)", analises_em)
with col2:
    st.metric("Reanálises", reanalises)
with col3:
    st.metric("Análises (EM + RE)", analises_total)

col4, col5, col6 = st.columns(3)
with col4:
    st.metric("Aprovações", aprovacoes)
with col5:
    st.metric("Vendas (únicas GERADAS)", vendas)
with col6:
    st.metric("VGV Total", format_currency(vgv_total))

col7, col8, col9 = st.columns(3)
with col7:
    st.metric("Taxa Aprov./Análises", f"{(aprovacoes/analises_em*100 if analises_em else 0):.1f}%")
with col8:
    st.metric("Taxa Vendas/Análises", f"{(vendas/analises_em*100 if analises_em else 0):.1f}%")
with col9:
    st.metric("IPC (vendas/corretor)", f"{ipc:.2f}")

st.markdown("### 📞 Leads CRM na data base selecionada")

col10, col11, col12 = st.columns(3)
with col10:
    st.metric("Leads capturados", total_leads if total_leads is not None else "—")
with col11:
    st.metric("Leads → Análises (EM)", f"{conv_leads_analise:.1f}%" if conv_leads_analise is not None else "—")
with col12:
    st.metric("Leads por análise", f"{leads_por_analise:.1f}" if leads_por_analise is not None else "—")

st.markdown("---")

# ---------------------------------------------------------
# 🔥 PAINEL 2 — HISTÓRICO DAS 3 ÚLTIMAS DATA BASE ANTERIORES
# ---------------------------------------------------------
st.markdown(f"## 📊 Histórico dos Últimos 3 Meses (Base: {DATA_BASE_ATUAL_LABEL})")

# defaults (evita NameError no gráfico)
analises_por_venda = 0.0
aprov_por_venda = 0.0
meta_vendas = 0
analises_necessarias = 0
aprovacoes_necessarias = 0

bases_view = sorted(pd.to_datetime(df_view["DATA_BASE"], errors="coerce").dropna().unique())

if DATA_BASE_ATUAL in bases_view:
    idx_atual = bases_view.index(DATA_BASE_ATUAL)
    idx_ini = max(0, idx_atual - 3)
    bases_hist = bases_view[idx_ini:idx_atual]
else:
    bases_hist = []

df_3m = df_view[
    pd.to_datetime(df_view["DATA_BASE"], errors="coerce").isin(bases_hist)
].copy()

if df_3m.empty:
    st.info("Nenhum registro encontrado para as 3 últimas data base anteriores.")
    vendas_3m = 0
else:
    status_3m = df_3m["STATUS_BASE"].fillna("").astype(str).str.upper()

    analises_em_3m = conta_analises_base(status_3m)
    reanalises_3m = conta_reanalises(status_3m)
    aprovacoes_3m = conta_aprovacoes(status_3m)

    df_vendas_3m = obter_vendas_unicas(
        df_3m,
        status_venda=["VENDA GERADA"],
        status_final_map=status_final_por_cliente
    )
    vendas_3m = len(df_vendas_3m)

    if vendas_3m > 0:
        analises_por_venda = (analises_em_3m / vendas_3m) if analises_em_3m > 0 else 0
        aprov_por_venda = (aprovacoes_3m / vendas_3m) if aprovacoes_3m > 0 else 0

    colH1, colH2, colH3, colH4 = st.columns(4)
    with colH1:
        st.metric("Análises (EM)", analises_em_3m)
    with colH2:
        st.metric("Reanálises", reanalises_3m)
    with colH3:
        st.metric("Aprovações", aprovacoes_3m)
    with colH4:
        st.metric("Vendas (únicas GERADAS)", vendas_3m)

    st.markdown("---")

# ---------------------------------------------------------
# 🔥 PAINEL 3 — PLANEJAMENTO (META)
# ---------------------------------------------------------
st.markdown("## 🎯 Planejamento")

meta_sugerida = int(vendas_3m / 3) if 'vendas_3m' in locals() and vendas_3m > 0 else 3

meta_vendas = st.number_input(
    "Meta de vendas (GERADAS) para o próximo período:",
    min_value=0,
    step=1,
    value=meta_sugerida
)

if analises_por_venda > 0:
    analises_necessarias = int(np.ceil(meta_vendas * analises_por_venda))
else:
    analises_necessarias = st.number_input(
        "Meta de análises (manual, sem histórico suficiente):",
        min_value=0,
        step=1,
        value=0
    )

if aprov_por_venda > 0:
    aprovacoes_necessarias = int(np.ceil(meta_vendas * aprov_por_venda))
else:
    aprovacoes_necessarias = st.number_input(
        "Meta de aprovações (manual, sem histórico suficiente):",
        min_value=0,
        step=1,
        value=0
    )

colP1, colP2, colP3 = st.columns(3)
with colP1:
    st.metric("Meta Vendas (GERADAS)", meta_vendas)
with colP2:
    st.metric("Meta Análises", analises_necessarias)
with colP3:
    st.metric("Meta Aprovações", aprovacoes_necessarias)

st.caption("Vendas = VENDA GERADA. Análises = EM ANÁLISE. Aprovações = APROVADO.")
st.markdown("---")

# ---------------------------------------------------------
# 🔥 META X REAL (GRÁFICO ACUMULADO)
# ---------------------------------------------------------
st.markdown("## 📈 Acompanhamento da Meta — Meta x Real")

indicador = st.selectbox(
    "Indicador para acompanhar:",
    ["Análises", "Aprovações", "Vendas"],
)

# ✅ EIXO DO TEMPO: SEMPRE ATÉ A ÚLTIMA DATA EXISTENTE NA PLANILHA
# (da DATA_BASE_ATUAL) — mesmo que corretor/equipe tenha parado.
df_ref = df_global[
    pd.to_datetime(df_global["DATA_BASE"], errors="coerce") == DATA_BASE_ATUAL
].copy()

datas_ref = df_ref["DIA"].dropna()
if datas_ref.empty:
    st.info("Sem datas válidas na base atual para montar o gráfico.")
    st.stop()

data_ini_ref = datas_ref.min().date()
data_fim_ref = datas_ref.max().date()

# Usuário escolhe só o início (o fim fica travado na última data da planilha)
data_ini = st.date_input(
    "Início do acompanhamento:",
    value=data_ini_ref,
    min_value=data_ini_ref,
    max_value=data_fim_ref
)
data_fim = data_fim_ref

st.caption(f"Fim do gráfico travado na última data da planilha: {data_fim.strftime('%d/%m/%Y')}")

if data_ini > data_fim:
    st.error("A data inicial não pode ser maior que a final.")
else:
    dias_range = pd.date_range(start=data_ini, end=data_fim, freq="D")
    dias_lista = [d.date() for d in dias_range]

    df_range = df_view.copy()
    df_range["DIA_DATA"] = pd.to_datetime(df_range["DIA"], errors="coerce").dt.date
    df_range = df_range[
        (df_range["DIA_DATA"] >= data_ini)
        & (df_range["DIA_DATA"] <= data_fim)
    ].copy()

    status_base_upper = df_range["STATUS_BASE"].fillna("").astype(str).str.upper()

    if indicador == "Análises":
        df_ind = df_range[status_base_upper == "EM ANÁLISE"].copy()
        total_meta = int(analises_necessarias)

    elif indicador == "Aprovações":
        df_ind = df_range[status_base_upper == "APROVADO"].copy()
        total_meta = int(aprovacoes_necessarias)

    else:  # Vendas (GERADAS)
        df_ind = obter_vendas_unicas(
            df_range,
            status_venda=["VENDA GERADA"],
            status_final_map=status_final_por_cliente
        ).copy()
        total_meta = int(meta_vendas)

    if total_meta <= 0:
        st.info("Defina uma meta maior que 0 para visualizar a linha de meta.")
        st.stop()

    if df_ind.empty:
        # Ainda assim, queremos a linha do realizado seguindo zerada (flat em 0)
        cont_por_dia = pd.Series(0, index=dias_lista)
    else:
        df_ind["DIA_DATA"] = pd.to_datetime(df_ind["DIA"], errors="coerce").dt.date
        cont_por_dia = (
            df_ind.groupby("DIA_DATA")
            .size()
            .reindex(dias_lista, fill_value=0)
        )

    df_line = pd.DataFrame(index=pd.to_datetime(dias_lista))
    df_line.index.name = "DIA"

    # ✅ Real acumulado: quando para de produzir, soma 0 e a linha fica reta (exatamente tua lógica)
    df_line["Real"] = cont_por_dia.cumsum().values

    # Meta linear até o fim do período
    df_line["Meta"] = np.linspace(0, total_meta, num=len(df_line), endpoint=True)

    df_plot = df_line.reset_index().melt(
        "DIA", var_name="Série", value_name="Valor"
    )

    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("DIA:T", title="Dia"),
            y=alt.Y("Valor:Q", title="Total Acumulado"),
            color=alt.Color("Série:N", title="")
        )
        .properties(height=350)
    )

    st.altair_chart(chart, use_container_width=True)
    st.caption(
        "Real = acumulado diário (dias sem movimento = +0, linha reta). "
        "Meta = ritmo necessário até a última data da planilha."
    )
