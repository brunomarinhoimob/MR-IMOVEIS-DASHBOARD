import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil de Vendas – MR Imóveis",
    page_icon="🔻",
    layout="wide",
)

st.title("🔻 Funil de Vendas – MR Imóveis")

st.caption(
    "Veja o funil completo da imobiliária (análises → aprovações → vendas), "
    "planeje metas com base no histórico e compare o funil por equipe."
)

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
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


def format_currency(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def conta_analises(s: pd.Series) -> int:
    # Análises totais (EM + RE) – volume
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()


def conta_analises_base(s: pd.Series) -> int:
    # Análises usadas como BASE (só EM ANÁLISE)
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(s: pd.Series) -> int:
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(s: pd.Series) -> int:
    return (s == "APROVADO").sum()


@st.cache_data(ttl=60)
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
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
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV (OBSERVAÇÕES)
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # NOME / CPF BASE PARA CHAVE DO CLIENTE
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
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


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    """
    Uma venda por cliente (último status).
    Se tiver VENDA INFORMADA e depois VENDA GERADA, fica só a GERADA.
    """
    df_v = df_scope[df_scope["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("")
    )

    df_v = df_v.sort_values("DIA")  # ordem cronológica
    df_v_ult = df_v.groupby("CHAVE_CLIENTE").tail(1)
    return df_v_ult


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# Leads do Supremo carregados no app principal (se tiver)
df_leads = st.session_state.get("df_leads", pd.DataFrame())

# ---------------------------------------------------------
# SIDEBAR – PERÍODO E EQUIPE
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = df["DIA"].dropna()
if dias_validos.empty:
    hoje = date.today()
    data_min = hoje - timedelta(days=30)
    data_max = hoje
else:
    data_min = dias_validos.min()
    data_max = dias_validos.max()

data_ini_default = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini, data_fim = data_ini_default, data_max

lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox(
    "Equipe (para funil detalhado)",
    ["Todas"] + lista_equipes,
)

# ---------------------------------------------------------
# APLICA PERÍODO
# ---------------------------------------------------------
df_periodo = df.copy()
dt_all = limpar_para_data(df_periodo["DIA"])
mask_periodo = (dt_all >= data_ini) & (dt_all <= data_fim)
df_periodo = df_periodo[mask_periodo]

registros_filtrados = len(df_periodo)

st.caption(
    f"Período filtrado: **{data_ini.strftime('%d/%m/%Y')}** até "
    f"**{data_fim.strftime('%d/%m/%Y')}** • "
    f"Registros considerados: **{registros_filtrados}**"
)

if df_periodo.empty:
    st.warning("Não há registros para o período selecionado.")
    st.stop()

df_vendas_unicas_periodo = obter_vendas_unicas(df_periodo)

# LEADS NO PERÍODO (IMOBILIÁRIA INTEIRA)
total_leads_periodo = None
if not df_leads.empty and "data_captura" in df_leads.columns:
    df_leads_use = df_leads.dropna(subset=["data_captura"]).copy()
    df_leads_use["data_captura"] = pd.to_datetime(
        df_leads_use["data_captura"], errors="coerce"
    )
    df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date
    mask_leads = (
        (df_leads_use["data_captura_date"] >= data_ini)
        & (df_leads_use["data_captura_date"] <= data_fim)
    )
    total_leads_periodo = int(mask_leads.sum())

# ---------------------------------------------------------
# FUNIL GERAL DA IMOBILIÁRIA
# ---------------------------------------------------------
st.markdown("## 🏢 Funil Geral da Imobiliária")

analises_em = conta_analises_base(df_periodo["STATUS_BASE"])    # só EM ANÁLISE
reanalises_total = conta_reanalises(df_periodo["STATUS_BASE"])  # REANÁLISE
analises_total = conta_analises(df_periodo["STATUS_BASE"])      # EM + RE (volume)
aprov_total = conta_aprovacoes(df_periodo["STATUS_BASE"])

vendas_total = len(df_vendas_unicas_periodo)
vgv_total = df_vendas_unicas_periodo["VGV"].sum() if not df_vendas_unicas_periodo.empty else 0.0

taxa_aprov_analise = aprov_total / analises_em * 100 if analises_em > 0 else 0
taxa_venda_analise = vendas_total / analises_em * 100 if analises_em > 0 else 0
taxa_venda_aprov = vendas_total / aprov_total * 100 if aprov_total > 0 else 0

media_leads_por_analise = None
if (total_leads_periodo is not None) and total_leads_periodo > 0 and analises_em > 0:
    media_leads_por_analise = total_leads_periodo / analises_em

# ---------- NOVOS KPI's ----------
# 1) IPC: vendas / corretores ativos nos últimos 30 dias (imobiliária inteira)
corretores_ativos_30 = 0
ipc_val = None

dias_all = df["DIA"].dropna()
if not dias_all.empty:
    data_max_all = dias_all.max()
    inicio_30 = data_max_all - timedelta(days=30)
    df_30d = df[(df["DIA"] >= inicio_30) & (df["DIA"] <= data_max_all)].copy()
    corretores_ativos_30 = df_30d["CORRETOR"].dropna().nunique()

if corretores_ativos_30 > 0:
    ipc_val = vendas_total / corretores_ativos_30

# 2) Equipe produtiva: % de corretores que venderam no período
corretores_totais_periodo = df_periodo["CORRETOR"].dropna().nunique()
corretores_com_venda_periodo = (
    df_vendas_unicas_periodo["CORRETOR"].dropna().nunique()
    if not df_vendas_unicas_periodo.empty
    else 0
)
equipe_produtiva_pct = (
    (corretores_com_venda_periodo / corretores_totais_periodo) * 100
    if corretores_totais_periodo > 0
    else 0
)

# ---------- MÉTRICAS VISUAIS ----------
col_leads_card, col1, col2, col3, col4, col5 = st.columns(6)
with col_leads_card:
    st.metric("Leads (CRM)", "-" if total_leads_periodo is None else total_leads_periodo)
with col1:
    st.metric("Análises (só EM)", analises_em)
with col2:
    st.metric("Reanálises", reanalises_total)
with col3:
    st.metric("Análises (EM + RE)", analises_total)
with col4:
    st.metric("Aprovações", aprov_total)
with col5:
    st.metric("Vendas (Total)", vendas_total)

col_vgv, col_ipc, col_t1, col_t2 = st.columns(4)
with col_vgv:
    st.metric("VGV Total", format_currency(vgv_total))
with col_ipc:
    st.metric(
        "IPC (vendas/corretor - 30 dias)",
        f"{ipc_val:.2f}" if ipc_val is not None else "—",
        help=(
            "Soma das vendas do período filtrado dividida pela quantidade "
            "de corretores ativos na imobiliária nos últimos 30 dias."
        ),
    )
with col_t1:
    st.metric("Taxa Aprov./Análises (só EM)", f"{taxa_aprov_analise:.1f}%")
with col_t2:
    st.metric("Taxa Vendas/Análises (só EM)", f"{taxa_venda_analise:.1f}%")

col_tx_va, col_eq_prod = st.columns(2)
with col_tx_va:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")
with col_eq_prod:
    st.metric(
        "Equipe produtiva",
        f"{equipe_produtiva_pct:.1f}%",
        help=(
            "Porcentagem de corretores que fizeram pelo menos 1 venda "
            "no período filtrado."
        ),
    )

if media_leads_por_analise is not None:
    st.caption(f"Média de {media_leads_por_analise:.1f} leads por análise (só EM).")
else:
    st.caption("Média de leads por análise indisponível para o período selecionado.")

# ---------------------------------------------------------
# TABELA + GRÁFICO DO FUNIL GERAL
# ---------------------------------------------------------
df_funil_geral = pd.DataFrame(
    {
        "Etapa": ["Análises (só EM)", "Aprovações", "Vendas"],
        "Quantidade": [analises_em, aprov_total, vendas_total],
        "Conversão da etapa anterior (%)": [
            100.0 if analises_em > 0 else 0.0,
            taxa_aprov_analise if analises_em > 0 else 0.0,
            taxa_venda_aprov if aprov_total > 0 else 0.0,
        ],
    }
)

st.markdown("### 📋 Tabela do Funil Geral")
st.dataframe(
    df_funil_geral.style.format(
        {"Conversão da etapa anterior (%)": "{:.1f}%".format}
    ),
    use_container_width=True,
    hide_index=True,
)

st.markdown("### 📊 Gráfico do Funil Geral (Análises → Aprovações → Vendas)")
chart_funil = (
    alt.Chart(df_funil_geral)
    .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
    .encode(
        x=alt.X("Quantidade:Q", title="Quantidade"),
        y=alt.Y(
            "Etapa:N",
            sort=["Análises (só EM)", "Aprovações", "Vendas"],
            title="Etapa",
        ),
        tooltip=[
            "Etapa",
            "Quantidade",
            alt.Tooltip(
                "Conversão da etapa anterior (%)",
                title="Conversão",
                format=".1f",
            ),
        ],
    )
    .properties(height=300)
)
st.altair_chart(chart_funil, use_container_width=True)

# ---------------------------------------------------------
# PLANEJAMENTO – ÚLTIMOS 3 MESES (IMOBILIÁRIA)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Planejamento de Vendas da Imobiliária (base últimos 3 meses)")

if df["DIA"].isna().all():
    st.info("Não há datas válidas na base para calcular os últimos 3 meses.")
else:
    dt_all = pd.to_datetime(df["DIA"], errors="coerce")
    ref_date = dt_all.max()

    if pd.isna(ref_date):
        st.info("Não foi possível identificar a data de referência na base.")
    else:
        limite_3m = ref_date - pd.DateOffset(months=3)
        mask_3m = (dt_all >= limite_3m) & (dt_all <= ref_date)
        df_3m = df[mask_3m].copy()

        if df_3m.empty:
            st.info(
                f"A base não possui registros nos últimos 3 meses "
                f"(janela usada: {limite_3m.date().strftime('%d/%m/%Y')} "
                f"até {ref_date.date().strftime('%d/%m/%Y')})."
            )
        else:
            analises_3m_base = conta_analises_base(df_3m["STATUS_BASE"])
            aprov_3m = conta_aprovacoes(df_3m["STATUS_BASE"])
            df_vendas_3m = obter_vendas_unicas(df_3m)
            vendas_3m = len(df_vendas_3m)

            if vendas_3m > 0:
                media_analise_por_venda_3m = (
                    analises_3m_base / vendas_3m if analises_3m_base > 0 else 0
                )
                media_aprov_por_venda_3m = (
                    aprov_3m / vendas_3m if aprov_3m > 0 else 0
                )
            else:
                media_analise_por_venda_3m = 0
                media_aprov_por_venda_3m = 0

            c_hist1, c_hist2, c_hist3 = st.columns(3)
            with c_hist1:
                st.metric("Análises (3m – só EM)", analises_3m_base)
            with c_hist2:
                st.metric("Aprovações (últimos 3 meses)", aprov_3m)
            with c_hist3:
                st.metric("Vendas (últimos 3 meses)", vendas_3m)

            c_hist4, c_hist5 = st.columns(2)
            with c_hist4:
                st.metric(
                    "Média de ANÁLISES por venda (3m, só EM)",
                    f"{media_analise_por_venda_3m:.1f}" if vendas_3m > 0 else "—",
                )
            with c_hist5:
                st.metric(
                    "Média de APROVAÇÕES por venda (3m)",
                    f"{media_aprov_por_venda_3m:.1f}" if vendas_3m > 0 else "—",
                )

            st.caption(
                f"Janela histórica usada: de {limite_3m.date().strftime('%d/%m/%Y')} "
                f"até {ref_date.date().strftime('%d/%m/%Y')}."
            )

            st.markdown("### 📌 Situação atual no período filtrado")
            c_at1, c_at2 = st.columns(2)
            with c_at1:
                st.metric("Análises já feitas no período (só EM)", analises_em)
            with c_at2:
                st.metric("Vendas já realizadas no período", vendas_total)

            st.markdown("### 🎯 Quantas análises/aprovações preciso para bater a meta de vendas da imobiliária?")
            vendas_planejadas = st.number_input(
                "Vendas desejadas no mês (imobiliária inteira)",
                min_value=0,
                value=10,
                step=1,
                key="vendas_planejadas_imob",
            )

            if vendas_planejadas > 0 and vendas_3m > 0:
                analises_necessarias = media_analise_por_venda_3m * vendas_planejadas
                aprovacoes_necessarias = media_aprov_por_venda_3m * vendas_planejadas

                analises_necessarias_int = int(np.ceil(analises_necessarias))
                aprovacoes_necessarias_int = int(np.ceil(aprovacoes_necessarias))

                c_calc1, c_calc2, c_calc3 = st.columns(3)
                with c_calc1:
                    st.metric("Meta de vendas (mês)", vendas_planejadas)
                with c_calc2:
                    st.metric(
                        "Análises necessárias (aprox.)",
                        f"{analises_necessarias_int} análises",
                        help=f"Cálculo: {media_analise_por_venda_3m:.2f} análises/venda × {vendas_planejadas}",
                    )
                with c_calc3:
                    st.metric(
                        "Aprovações necessárias (aprox.)",
                        f"{aprovacoes_necessarias_int} aprovações",
                        help=f"Cálculo: {media_aprov_por_venda_3m:.2f} aprovações/venda × {vendas_planejadas}",
                    )

                st.caption(
                    "Os números são aproximados e arredondados para cima, "
                    "baseados no comportamento real da imobiliária nos últimos 3 meses."
                )
            elif vendas_planejadas > 0 and vendas_3m == 0:
                st.info(
                    "Ainda não há vendas registradas nos últimos 3 meses para calcular as médias por venda."
                )

# ---------------------------------------------------------
# FUNIL POR EQUIPE (VISÃO COMPARATIVA)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 👥 Funil por Equipe (comparativo)")

rank_eq_funil = (
    df_periodo.groupby("EQUIPE")
    .agg(
        ANALISES=("STATUS_BASE", conta_analises),
        ANALISES_BASE=("STATUS_BASE", conta_analises_base),
        REANALISES=("STATUS_BASE", conta_reanalises),
        APROVACOES=("STATUS_BASE", conta_aprovacoes),
    )
    .reset_index()
)

if not df_vendas_unicas_periodo.empty:
    vendas_eq = df_vendas_unicas_periodo.groupby("EQUIPE").size().rename("VENDAS")
    vgv_eq = df_vendas_unicas_periodo.groupby("EQUIPE")["VGV"].sum().rename("VGV")
    rank_eq_funil = rank_eq_funil.merge(vendas_eq, on="EQUIPE", how="left")
    rank_eq_funil = rank_eq_funil.merge(vgv_eq, on="EQUIPE", how="left")
else:
    rank_eq_funil["VENDAS"] = 0
    rank_eq_funil["VGV"] = 0.0

rank_eq_funil["VENDAS"] = rank_eq_funil["VENDAS"].fillna(0).astype(int)
rank_eq_funil["VGV"] = rank_eq_funil["VGV"].fillna(0.0)

rank_eq_funil = rank_eq_funil[
    (rank_eq_funil["ANALISES"] > 0)
    | (rank_eq_funil["APROVACOES"] > 0)
    | (rank_eq_funil["VENDAS"] > 0)
    | (rank_eq_funil["VGV"] > 0)
]

if rank_eq_funil.empty:
    st.info("Nenhuma equipe com movimentação no período selecionado.")
else:
    rank_eq_funil["TAXA_APROV_ANALISES"] = np.where(
        rank_eq_funil["ANALISES_BASE"] > 0,
        rank_eq_funil["APROVACOES"] / rank_eq_funil["ANALISES_BASE"] * 100,
        0,
    )
    rank_eq_funil["TAXA_VENDAS_ANALISES"] = np.where(
        rank_eq_funil["ANALISES_BASE"] > 0,
        rank_eq_funil["VENDAS"] / rank_eq_funil["ANALISES_BASE"] * 100,
        0,
    )
    rank_eq_funil["TAXA_VENDAS_APROV"] = np.where(
        rank_eq_funil["APROVACOES"] > 0,
        rank_eq_funil["VENDAS"] / rank_eq_funil["APROVACOES"] * 100,
        0,
    )

    # ordena por VGV e depois VENDAS
    rank_eq_funil = rank_eq_funil.sort_values(["VGV", "VENDAS"], ascending=False)

    st.markdown("### 📋 Tabela do Funil por Equipe")

    # ORDEM DAS COLUNAS – IGUAL AO PRINT
    colunas_ordem = [
        "EQUIPE",
        "VGV",
        "VENDAS",
        "ANALISES",
        "ANALISES_BASE",
        "REANALISES",
        "APROVACOES",
        "TAXA_APROV_ANALISES",
        "TAXA_VENDAS_ANALISES",
        "TAXA_VENDAS_APROV",
    ]
    colunas_existentes = [c for c in colunas_ordem if c in rank_eq_funil.columns]
    tabela_eq = rank_eq_funil[colunas_existentes].copy()

    renomear = {
        "EQUIPE": "EQUIPE",
        "VGV": "VGV",
        "VENDAS": "VENDAS",
        "ANALISES": "ANÁLISES (EM + RE)",
        "ANALISES_BASE": "ANÁLISES (só EM)",
        "REANALISES": "REANÁLISES",
        "APROVACOES": "APROVAÇÕES",
        "TAXA_APROV_ANALISES": "% Aprov./Análises (só EM)",
        "TAXA_VENDAS_ANALISES": "% Vendas/Análises (só EM)",
        "TAXA_VENDAS_APROV": "% Vendas/Aprovações",
    }
    tabela_eq = tabela_eq.rename(columns=renomear)

    format_dict = {
        "VGV": "R$ {:,.2f}".format,
        "% Aprov./Análises (só EM)": "{:.1f}%".format,
        "% Vendas/Análises (só EM)": "{:.1f}%".format,
        "% Vendas/Aprovações": "{:.1f}%".format,
    }

    st.dataframe(
        tabela_eq.style.format(format_dict),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 💰 VGV por Equipe")
    chart_eq_vgv = (
        alt.Chart(rank_eq_funil)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("VGV:Q", title="VGV (R$)"),
            y=alt.Y("EQUIPE:N", sort="-x", title="Equipe"),
            tooltip=[
                alt.Tooltip("EQUIPE:N", title="Equipe"),
                alt.Tooltip("ANALISES_BASE:Q", title="Análises (só EM)"),
                alt.Tooltip("REANALISES:Q", title="Reanálises"),
                alt.Tooltip("ANALISES:Q", title="Análises (EM + RE)"),
                alt.Tooltip("APROVACOES:Q", title="Aprovações"),
                alt.Tooltip("VENDAS:Q", title="Vendas"),
                alt.Tooltip("VGV:Q", title="VGV", format=",.2f"),
                alt.Tooltip(
                    "TAXA_APROV_ANALISES:Q",
                    title="% Aprov./Análises (só EM)",
                    format=".1f",
                ),
                alt.Tooltip(
                    "TAXA_VENDAS_ANALISES:Q",
                    title="% Vendas/Análises (só EM)",
                    format=".1f",
                ),
                alt.Tooltip(
                    "TAXA_VENDAS_APROV:Q",
                    title="% Vendas/Aprovações",
                    format=".1f",
                ),
            ],
        )
        .properties(height=400)
    )
    st.altair_chart(chart_eq_vgv, use_container_width=True)

# ---------------------------------------------------------
# FUNIL DETALHADO + PLANEJAMENTO POR EQUIPE
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🔍 Funil detalhado e planejamento por equipe")

if equipe_sel == "Todas":
    st.info("Selecione uma equipe específica na barra lateral para ver o funil e o planejamento dessa equipe.")
else:
    df_eq = df_periodo[df_periodo["EQUIPE"] == equipe_sel]
    if df_eq.empty:
        st.warning(f"A equipe **{equipe_sel}** não possui registros no período selecionado.")
    else:
        analises_eq_em = conta_analises_base(df_eq["STATUS_BASE"])
        reanalises_eq = conta_reanalises(df_eq["STATUS_BASE"])
        analises_eq_total = conta_analises(df_eq["STATUS_BASE"])
        aprov_eq = conta_aprovacoes(df_eq["STATUS_BASE"])

        df_eq_vendas_unicas = obter_vendas_unicas(df_eq)
        vendas_eq = len(df_eq_vendas_unicas)
        vgv_eq = df_eq_vendas_unicas["VGV"].sum() if not df_eq_vendas_unicas.empty else 0.0

        taxa_aprov_eq = aprov_eq / analises_eq_em * 100 if analises_eq_em > 0 else 0
        taxa_venda_analises_eq = vendas_eq / analises_eq_em * 100 if analises_eq_em > 0 else 0
        taxa_venda_aprov_eq = vendas_eq / aprov_eq * 100 if aprov_eq > 0 else 0

        st.markdown(f"### Equipe: **{equipe_sel}**")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Análises (só EM)", analises_eq_em)
        with c2:
            st.metric("Reanálises", reanalises_eq)
        with c3:
            st.metric("Análises (EM + RE)", analises_eq_total)
        with c4:
            st.metric("Aprovações", aprov_eq)
        with c5:
            st.metric("Vendas (Total)", vendas_eq)

        c6, c7, c8 = st.columns(3)
        with c6:
            st.metric("VGV da equipe", format_currency(vgv_eq))
        with c7:
            st.metric("Taxa Aprov./Análises (só EM)", f"{taxa_aprov_eq:.1f}%")
        with c8:
            st.metric("Taxa Vendas/Análises (só EM)", f"{taxa_venda_analises_eq:.1f}%")

        c9, = st.columns(1)
        with c9:
            st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov_eq:.1f}%")

        # Planejamento 3 meses por equipe
        st.markdown("### 📊 Planejamento de vendas dessa equipe (base últimos 3 meses)")

        df_eq_full = df[df["EQUIPE"] == equipe_sel].copy()
        if df_eq_full["DIA"].isna().all():
            st.info("Não há datas válidas na base para calcular os últimos 3 meses dessa equipe.")
        else:
            dt_eq_all = pd.to_datetime(df_eq_full["DIA"], errors="coerce")
            ref_date_eq = dt_eq_all.max()

            if pd.isna(ref_date_eq):
                st.info("Não foi possível identificar a data de referência da equipe na base.")
            else:
                limite_3m_eq = ref_date_eq - pd.DateOffset(months=3)
                mask_3m_eq = (dt_eq_all >= limite_3m_eq) & (dt_eq_all <= ref_date_eq)
                df_eq_3m = df_eq_full[mask_3m_eq].copy()

                if df_eq_3m.empty:
                    st.info(
                        f"A equipe **{equipe_sel}** não possui registros nos últimos 3 meses "
                        f"(janela usada: {limite_3m_eq.date().strftime('%d/%m/%Y')} "
                        f"até {ref_date_eq.date().strftime('%d/%m/%Y')})."
                    )
                else:
                    analises_eq_3m_base = conta_analises_base(df_eq_3m["STATUS_BASE"])
                    aprov_eq_3m = conta_aprovacoes(df_eq_3m["STATUS_BASE"])
                    df_eq_vendas_3m = obter_vendas_unicas(df_eq_3m)
                    vendas_eq_3m = len(df_eq_vendas_3m)

                    if vendas_eq_3m > 0:
                        media_analise_por_venda_eq = (
                            analises_eq_3m_base / vendas_eq_3m
                            if analises_eq_3m_base > 0
                            else 0
                        )
                        media_aprov_por_venda_eq = (
                            aprov_eq_3m / vendas_eq_3m if aprov_eq_3m > 0 else 0
                        )
                    else:
                        media_analise_por_venda_eq = 0
                        media_aprov_por_venda_eq = 0

                    h1, h2, h3 = st.columns(3)
                    with h1:
                        st.metric("Análises (3m – só EM)", analises_eq_3m_base)
                    with h2:
                        st.metric("Aprovações (3m – equipe)", aprov_eq_3m)
                    with h3:
                        st.metric("Vendas (3m – equipe)", vendas_eq_3m)

                    h4, h5 = st.columns(2)
                    with h4:
                        st.metric(
                            "Média de ANÁLISES por venda (equipe, 3m, só EM)",
                            f"{media_analise_por_venda_eq:.1f}" if vendas_eq_3m > 0 else "—",
                        )
                    with h5:
                        st.metric(
                            "Média de APROVAÇÕES por venda (equipe, 3m)",
                            f"{media_aprov_por_venda_eq:.1f}" if vendas_eq_3m > 0 else "—",
                        )

                    st.caption(
                        f"Janela histórica usada para a equipe **{equipe_sel}**: "
                        f"de {limite_3m_eq.date().strftime('%d/%m/%Y')} "
                        f"até {ref_date_eq.date().strftime('%d/%m/%Y')}."
                    )

                    st.markdown("#### 🎯 Quantas análises/aprovações essa equipe precisa para bater a meta de vendas?")
                    vendas_planejadas_eq = st.number_input(
                        f"Vendas desejadas no mês para a equipe {equipe_sel}",
                        min_value=0,
                        value=5,
                        step=1,
                        key="vendas_planejadas_equipe",
                    )

                    if vendas_planejadas_eq > 0 and vendas_eq_3m > 0:
                        analises_eq_necessarias = media_analise_por_venda_eq * vendas_planejadas_eq
                        aprovacoes_eq_necessarias = media_aprov_por_venda_eq * vendas_planejadas_eq

                        analises_eq_necessarias_int = int(np.ceil(analises_eq_necessarias))
                        aprovacoes_eq_necessarias_int = int(np.ceil(aprovacoes_eq_necessarias))

                        c_eq1, c_eq2, c_eq3 = st.columns(3)
                        with c_eq1:
                            st.metric("Meta de vendas (equipe)", vendas_planejadas_eq)
                        with c_eq2:
                            st.metric(
                                "Análises necessárias (aprox.)",
                                f"{analises_eq_necessarias_int} análises",
                                help=(
                                    f"Cálculo: {media_analise_por_venda_eq:.2f} análises/venda "
                                    f"× {vendas_planejadas_eq}"
                                ),
                            )
                        with c_eq3:
                            st.metric(
                                "Aprovações necessárias (aprox.)",
                                f"{aprovacoes_eq_necessarias_int} aprovações",
                                help=(
                                    f"Cálculo: {media_aprov_por_venda_eq:.2f} aprovações/venda "
                                    f"× {vendas_planejadas_eq}"
                                ),
                            )

                        st.caption(
                            "Os números são aproximados e arredondados para cima, "
                            "baseados no histórico real dessa equipe nos últimos 3 meses."
                        )
                    elif vendas_planejadas_eq > 0 and vendas_eq_3m == 0:
                        st.info(
                            f"A equipe **{equipe_sel}** ainda não possui vendas registradas nos últimos 3 meses "
                            "para calcular as médias por venda."
                        )
