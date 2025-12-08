import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# =====================================================
# 1. CONFIG E ACESSO AO DF DE LEADS (VINDO DO app_dashboard)
# =====================================================

st.set_page_config(page_title="Atendimento de Leads", page_icon="📞", layout="wide")

st.title("📞 Controle de Atendimento de Leads")
st.caption(
    "Visão simples e operacional do atendimento: leads atendidos, não atendidos, "
    "tempo de atendimento e leads novos."
)

# df_leads deve ser carregado no app_dashboard e guardado em st.session_state["df_leads"]
if "df_leads" not in st.session_state or st.session_state["df_leads"] is None:
    st.error(
        "Nenhum dado de leads encontrado. "
        "Abra primeiro a página principal (app dashboard) para carregar os dados."
    )
    st.stop()

df_raw = st.session_state["df_leads"].copy()

# =====================================================
# 2. NORMALIZAÇÃO DE COLUNAS
# =====================================================

lower_cols = {c.lower(): c for c in df_raw.columns}


def get_col(*opcoes: str):
    """
    Retorna o nome real de coluna a partir de possíveis variações.
    Ex.: get_col('nome', 'nome do lead', 'lead') -> 'Nome do Lead'
    """
    for nome in opcoes:
        nome_lower = nome.lower()
        for col_lower, col_real in lower_cols.items():
            if nome_lower in col_lower:
                return col_real
    return None


col_nome = get_col("nome", "lead", "contato")
col_telefone = get_col("telefone", "celular", "whatsapp")
col_corretor = get_col("corretor", "responsavel", "responsável", "usuario", "usuário")
col_data_captura = get_col("data captura", "data de captura", "data lead", "data entrada", "criado em")
col_data_primeiro = get_col(
    "data com corretor", "data primeiro contato", "primeiro contato", "data atendimento", "data_contato"
)
col_data_ultima = get_col(
    "data última interação",
    "data ultima interação",
    "data ultima interacao",
    "ultima_interacao",
    "última interação",
)
col_situacao = get_col("situação", "situacao", "status")
col_etapa = get_col("etapa", "fase", "pipeline", "funil")


df = df_raw.copy()

df["NOME_LEAD"] = df[col_nome] if col_nome else ""
df["TELEFONE_LEAD"] = df[col_telefone] if col_telefone else ""
df["CORRETOR_EXIBICAO"] = df[col_corretor].fillna("SEM CORRETOR") if col_corretor else "SEM CORRETOR"

# Datas em datetime
for origem, destino in [
    (col_data_captura, "DATA_CAPTURA_DT"),
    (col_data_primeiro, "DATA_COM_CORRETOR_DT"),
    (col_data_ultima, "DATA_ULT_INTERACAO_DT"),
]:
    if origem:
        df[destino] = pd.to_datetime(df[origem], errors="coerce")
    else:
        df[destino] = pd.NaT

# Situação e etapa em maiúsculo (pra facilitar buscas)
df["_SITUACAO_TXT"] = df[col_situacao].fillna("").astype(str).str.upper() if col_situacao else ""
df["_ETAPA_TXT"] = df[col_etapa].fillna("").astype(str).str.upper() if col_etapa else ""

# Lead perdido
padrao_perdido = "(PERD|DESCART|CANCEL|SEM INTERESSE|SEM_INTERESSE)"
df["PERDIDO"] = df["_SITUACAO_TXT"].str.contains(padrao_perdido, regex=True) | df["_ETAPA_TXT"].str.contains(
    padrao_perdido, regex=True
)

# Lead atendido (teve primeiro contato)
df["ATENDIDO"] = df["DATA_COM_CORRETOR_DT"].notna()

# Tempo de atendimento (minutos entre captura e 1º contato)
df["TEMPO_ATEND_MIN"] = (
    (df["DATA_COM_CORRETOR_DT"] - df["DATA_CAPTURA_DT"]).dt.total_seconds() / 60.0
)

# Tempo entre interações (1º contato -> última interação)
df["TEMPO_INTERACOES_MIN"] = (
    (df["DATA_ULT_INTERACAO_DT"] - df["DATA_COM_CORRETOR_DT"]).dt.total_seconds() / 60.0
)


def format_minutes(val):
    if pd.isna(val):
        return "-"
    try:
        val = int(round(val))
        horas = val // 60
        minutos = val % 60
        if horas > 0:
            return f"{horas}h {minutos:02d}min"
        return f"{minutos} min"
    except Exception:
        return "-"


def fmt_dt(dt):
    if pd.isna(dt):
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


# =====================================================
# 3. FILTROS LATERAIS – POR ENQUANTO SEM FILTRAR DATA
# =====================================================

st.sidebar.header("Filtros – Atendimento de Leads")

# mesmo sem usar no filtro, mantemos os campos de data para referência
min_data = df["DATA_CAPTURA_DT"].min()
max_data = df["DATA_CAPTURA_DT"].max()

hoje = date.today()
default_ini = (min_data.date() if pd.notna(min_data) else hoje - timedelta(days=7))
default_fim = (max_data.date() if pd.notna(max_data) else hoje)

data_inicio = st.sidebar.date_input(
    "Data inicial (captura do lead)",
    value=default_ini,
)
data_fim = st.sidebar.date_input(
    "Data final (captura do lead)",
    value=default_fim,
)

if data_inicio > data_fim:
    st.sidebar.error("A data inicial não pode ser maior que a data final.")
    st.stop()

# 🚨 POR ENQUANTO: NÃO VAMOS FILTRAR POR DATA PARA NÃO ZERAR OS DADOS
df_periodo = df.copy()

# Filtro por corretor
corretores = sorted(df_periodo["CORRETOR_EXIBICAO"].dropna().unique().tolist())
opcoes_corretor = ["Todos"] + corretores
corretor_sel = st.sidebar.selectbox("Corretor", opcoes_corretor)

if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR_EXIBICAO"] == corretor_sel]

if df_periodo.empty:
    st.warning("Nenhum lead encontrado com os filtros selecionados.")
    st.stop()

st.write(
    f"Período selecionado: **{data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}** "
    "(a filtragem por data ainda não está sendo aplicada – visão geral de todos os leads carregados)."
)

# =====================================================
# 4. KPIs GERAIS (TUDO COMO ATENDIMENTO)
# =====================================================

leads_no_periodo = len(df_periodo)
leads_atendidos = df_periodo["ATENDIDO"].sum()
leads_nao_atendidos = leads_no_periodo - leads_atendidos
leads_perdidos = df_periodo["PERDIDO"].sum()

# Tempo médio de atendimento (apenas atendidos)
tempo_medio_min = df_periodo.loc[df_periodo["ATENDIDO"], "TEMPO_ATEND_MIN"].mean()
tempo_medio_fmt = format_minutes(tempo_medio_min) if not pd.isna(tempo_medio_min) else "-"

# Leads novos = não perdidos e não atendidos
mask_novos = (~df_periodo["PERDIDO"]) & (~df_periodo["ATENDIDO"])
df_leads_novos = df_periodo[mask_novos].copy()
qtd_leads_novos = len(df_leads_novos)

# % atendidos em até 15 min
mask_ate15 = (df_periodo["ATENDIDO"]) & (df_periodo["TEMPO_ATEND_MIN"] <= 15)
qtd_ate15 = mask_ate15.sum()
perc_ate15 = (qtd_ate15 / leads_atendidos * 100) if leads_atendidos > 0 else 0

st.markdown("## 🧾 Visão geral do atendimento")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Leads no período", leads_no_periodo)
c2.metric("Leads atendidos", leads_atendidos)
c3.metric("Leads não atendidos", leads_nao_atendidos)
c4.metric("Leads perdidos no período", leads_perdidos)
c5.metric("Tempo médio de atendimento", tempo_medio_fmt)
c6.metric("% atendidos em até 15 min", f"{perc_ate15:.1f}%")

st.markdown("### 📥 Leads novos (não perdidos e ainda não atendidos)")
if qtd_leads_novos > 0:
    cols_exibir = ["NOME_LEAD", "TELEFONE_LEAD", "CORRETOR_EXIBICAO", "DATA_CAPTURA_DT"]
    cols_exibir = [c for c in cols_exibir if c in df_leads_novos.columns]
    df_tmp = df_leads_novos.copy()
    if "DATA_CAPTURA_DT" in df_tmp.columns:
        df_tmp["Data captura"] = df_tmp["DATA_CAPTURA_DT"].apply(fmt_dt)
        cols_exibir = [c for c in cols_exibir if c != "DATA_CAPTURA_DT"] + ["Data captura"]
    st.dataframe(df_tmp[cols_exibir], use_container_width=True)
else:
    st.button("↑ Nenhum lead novo", disabled=True)

# =====================================================
# 5. RESUMO GERAL POR CORRETOR (RANK + ANÁLISES)
# =====================================================

st.markdown("## 👥 Resumo geral por corretor")

df_cor = df_periodo.copy()

agr = df_cor.groupby("CORRETOR_EXIBICAO").agg(
    LEADS_PERIODO=("NOME_LEAD", "count"),
    LEADS_ATENDIDOS=("ATENDIDO", "sum"),
    TEMPO_MEDIO_ATEND_MIN=("TEMPO_ATEND_MIN", "mean"),
    TEMPO_MEDIO_INTERACOES_MIN=("TEMPO_INTERACOES_MIN", "mean"),
).reset_index()


def obter_analises_por_corretor() -> pd.Series:
    """
    Tenta puxar da base principal (ex.: st.session_state['df_base']) o número de
    análises por corretor (sem filtro de data por enquanto).
    Se não existir, devolve série vazia.
    """
    df_base = st.session_state.get("df_base")
    if df_base is None:
        return pd.Series(dtype="float64")

    df_b = df_base.copy()
    cols_lower = {c.lower(): c for c in df_b.columns}

    def col_base(*names):
        for n in names:
            for cl, real in cols_lower.items():
                if n.lower() in cl:
                    return real
        return None

    col_corretor_base = col_base("corretor", "consultor", "vendedor")
    col_status_base = col_base("status_base", "status", "etapa", "situação", "situacao")

    if not col_corretor_base or not col_status_base:
        return pd.Series(dtype="float64")

    txt_status = df_b[col_status_base].fillna("").astype(str).str.upper()
    mask_analise = (
        txt_status.str.contains("EM ANÁLISE")
        | txt_status.str.contains("REANÁLISE")
        | txt_status.str.contains("ANALISE")
        | txt_status.str.contains("ANÁLISE")
    )
    df_b = df_b[mask_analise]

    serie = df_b.groupby(col_corretor_base)[col_status_base].count()
    serie.name = "ANALISES_PERIODO"
    return serie


serie_analises = obter_analises_por_corretor()

if not serie_analises.empty:
    agr = agr.merge(
        serie_analises.reset_index().rename(columns={serie_analises.index.name: "CORRETOR_EXIBICAO"}),
        on="CORRETOR_EXIBICAO",
        how="left",
    )
else:
    agr["ANALISES_PERIODO"] = 0

agr = agr.sort_values(by="LEADS_PERIODO", ascending=False).reset_index(drop=True)
agr["RANK_LEADS"] = agr.index + 1

agr["Tempo médio atendimento"] = agr["TEMPO_MEDIO_ATEND_MIN"].apply(format_minutes)
agr["Tempo médio entre interações"] = agr["TEMPO_MEDIO_INTERACOES_MIN"].apply(format_minutes)

cols_resumo = [
    "RANK_LEADS",
    "CORRETOR_EXIBICAO",
    "LEADS_PERIODO",
    "LEADS_ATENDIDOS",
    "ANALISES_PERIODO",
    "Tempo médio atendimento",
    "Tempo médio entre interações",
]

st.dataframe(
    agr[cols_resumo],
    use_container_width=True,
    hide_index=True,
)

# =====================================================
# 6. TABELAS DETALHADAS
# =====================================================

st.markdown("## 📂 Detalhamento dos leads")

aba1, aba2, aba3 = st.tabs(["Atendidos", "Não atendidos", "Apenas 1 contato"])

with aba1:
    df_atendidos = df_periodo[df_periodo["ATENDIDO"] & (~df_periodo["PERDIDO"])].copy()
    if df_atendidos.empty:
        st.info("Nenhum lead atendido.")
    else:
        df_atendidos["Captura"] = df_atendidos["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_atendidos["1º contato"] = df_atendidos["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        df_atendidos["Última interação"] = df_atendidos["DATA_ULT_INTERACAO_DT"].apply(fmt_dt)
        df_atendidos["Tempo atendimento"] = df_atendidos["TEMPO_ATEND_MIN"].apply(format_minutes)

        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "Captura",
            "1º contato",
            "Última interação",
            "Tempo atendimento",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_atendidos.columns]
        st.dataframe(df_atendidos[cols], use_container_width=True)

with aba2:
    df_nao = df_periodo[(~df_periodo["ATENDIDO"]) & (~df_periodo["PERDIDO"])].copy()
    if df_nao.empty:
        st.info("Nenhum lead não atendido.")
    else:
        df_nao["Captura"] = df_nao["DATA_CAPTURA_DT"].apply(fmt_dt)
        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "Captura",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_nao.columns]
        st.dataframe(df_nao[cols], use_container_width=True)

with aba3:
    df_1contato = df_periodo[
        (df_periodo["ATENDIDO"])
        & (~df_periodo["PERDIDO"])
        & (df_periodo["DATA_ULT_INTERACAO_DT"].isna())
    ].copy()

    if df_1contato.empty:
        st.info("Nenhum lead com apenas 1 contato.")
    else:
        df_1contato["Captura"] = df_1contato["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_1contato["1º contato"] = df_1contato["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "Captura",
            "1º contato",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_1contato.columns]
        st.dataframe(df_1contato[cols], use_container_width=True)
