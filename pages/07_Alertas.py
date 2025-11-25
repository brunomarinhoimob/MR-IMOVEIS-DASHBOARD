import streamlit as st
import pandas as pd
from datetime import timedelta, date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Alertas – MR Imóveis",
    page_icon="🔴",
    layout="wide",
)

# Cabeçalho com título + logo MR
col_titulo, col_logo = st.columns([3, 1])
with col_titulo:
    st.title("🔴 Alertas da Operação Comercial")
with col_logo:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except Exception:
        pass  # se não achar a logo, apenas ignora

st.markdown(
    "Monitoramento de **corretores**, **clientes em pendência** "
    "e **vendas informadas paradas**, para o gestor cobrar e destravar o funil."
)

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA (MESMO DO DASHBOARD PRINCIPAL)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # Converte DIA para datetime para facilitar cálculos depois
    df["DT_BASE"] = pd.to_datetime(df["DIA"], errors="coerce")

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
    col_situacao = None
    for c in possiveis_cols_situacao:
        if c in df.columns:
            col_situacao = c
            break

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        # CORREÇÃO: tornar mapeamento de pendência mais abrangente (funciona com acento / variações)
        df.loc[status.str.contains("PEND", na=False), "STATUS_BASE"] = "PENDÊNCIA"

    # NOME / CPF BASE (para chave do cliente)
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


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link/gid.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – FILTRO DE EQUIPE
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

# Aplica filtro de equipe na base inteira
if equipe_sel != "Todas":
    df = df[df["EQUIPE"] == equipe_sel]

if df.empty:
    st.warning("Não há registros para a equipe selecionada.")
    st.stop()

# Data de referência geral (última data na base filtrada)
data_ref_geral_ts = df["DT_BASE"].max()
if pd.isna(data_ref_geral_ts):
    st.info("Não foi possível identificar a data de referência na base.")
    st.stop()
data_ref_geral_date = data_ref_geral_ts.date()

# Também vamos usar a data de hoje para alguns cálculos (pendência)
hoje = date.today()

# ---------------------------------------------------------
# 1) CORRETORES SEM ANÁLISE HÁ 3+ DIAS (JANELA 30 DIAS)
# ---------------------------------------------------------
st.markdown("## 🧑‍💻 Corretores sem análises nos últimos 3 dias (janela de 30 dias)")

df_analise_base = df[df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])].copy()

if df_analise_base.empty or df_analise_base["DT_BASE"].isna().all():
    if equipe_sel == "Todas":
        st.info("Ainda não há análises registradas para calcular alertas.")
    else:
        st.info(f"A equipe **{equipe_sel}** não possui análises registradas.")
else:
    # Data de referência (última análise)
    data_ref_ts = df_analise_base["DT_BASE"].max()
    data_ref = data_ref_ts if not pd.isna(data_ref_ts) else data_ref_geral_ts

    data_inicio_janela = data_ref - timedelta(days=30)

    # Mantém análises dentro dos últimos 30 dias
    df_analise_30 = df_analise_base[
        (df_analise_30["DT_BASE"] >= data_inicio_janela)
        & (df_analise_30["DT_BASE"] <= data_ref)
    ].copy()

    if df_analise_30.empty:
        st.info(
            f"Não há análises nos últimos 30 dias (data de referência: {data_ref.date().strftime('%d/%m/%Y')})."
        )
    else:
        ultima_analise_corretor = (
            df_analise_30.dropna(subset=["DT_BASE"])
            .groupby("CORRETOR", as_index=False)["DT_BASE"]
            .max()
        )

        corretores_todos = sorted(df["CORRETOR"].dropna().unique().tolist())

        registros_alerta = []
        for corr in corretores_todos:
            linha = ultima_analise_corretor[ultima_analise_corretor["CORRETOR"] == corr]
            if linha.empty:
                # sem análise na janela de 30 dias => não entra no alerta
                continue

            ultima_dt_ts = linha["DT_BASE"].iloc[0]
            dias_sem = (data_ref - ultima_dt_ts).days

            if dias_sem >= 3:
                registros_alerta.append(
                    {
                        "CORRETOR": corr,
                        "ÚLTIMA ANÁLISE": ultima_dt_ts.date().strftime("%d/%m/%Y"),
                        "DIAS SEM ANÁLISE (janela 30d)": dias_sem,
                    }
                )

        st.caption(
            f"Data de referência considerada: **{data_ref.date().strftime('%d/%m/%Y')}**. "
            "Janela de **30 dias** para trás. Entram aqui somente corretores que "
            "estão há **3 dias ou mais** sem subir análises, mas que tiveram pelo menos "
            "1 análise dentro dessa janela."
        )

        if not registros_alerta:
            st.success(
                "✅ Nenhum corretor está há 3 dias ou mais sem análises dentro da janela dos últimos 30 dias."
            )
        else:
            df_alerta = pd.DataFrame(registros_alerta).sort_values(
                "DIAS SEM ANÁLISE (janela 30d)", ascending=False
            )

            def colorir_dias(val):
                return "color: #f97373; font-weight: bold;"

            st.dataframe(
                df_alerta.style.applymap(
                    colorir_dias, subset=["DIAS SEM ANÁLISE (janela 30d)"]
                ),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------
# 2) CLIENTES EM PENDÊNCIA COMO ÚLTIMA AÇÃO (2+ DIAS)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## ⏳ Clientes em pendência há mais de 2 dias (última ação pendência)")

df_pend_base = df.copy()

# Chave de cliente
df_pend_base["CHAVE_CLIENTE"] = (
    df_pend_base["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
    + " | "
    + df_pend_base["CPF_CLIENTE_BASE"].fillna("")
)

# Última ação por cliente
df_last_acao = (
    df_pend_base.dropna(subset=["DT_BASE"])
    .sort_values("DT_BASE")
    .groupby("CHAVE_CLIENTE", as_index=False)
    .tail(1)
)

if df_last_acao.empty:
    st.info("Não foi possível identificar últimas ações dos clientes.")
else:
    df_pendentes = df_last_acao[df_last_acao["STATUS_BASE"] == "PENDÊNCIA"].copy()

    if df_pendentes.empty:
        st.success("✅ Não há clientes com pendência como última ação.")
    else:
        # CORREÇÃO: diferença de dias usando a data de hoje (e não só última data da base)
        df_pendentes["DIAS_DESDE_PENDENCIA"] = (
            hoje - df_pendentes["DT_BASE"].dt.date
        ).dt.days

        # filtra quem está há 2 dias ou mais parado em pendência
        df_pendentes = df_pendentes[df_pendentes["DIAS_DESDE_PENDENCIA"] >= 2]

        if df_pendentes.empty:
            st.success("✅ Não há clientes com pendência há 2 dias ou mais.")
        else:
            df_pend_view = df_pendentes[
                [
                    "NOME_CLIENTE_BASE",
                    "CPF_CLIENTE_BASE",
                    "EQUIPE",
                    "CORRETOR",
                    "DT_BASE",
                    "DIAS_DESDE_PENDENCIA",
                ]
            ].copy()

            df_pend_view = df_pend_view.rename(
                columns={
                    "NOME_CLIENTE_BASE": "CLIENTE",
                    "CPF_CLIENTE_BASE": "CPF",
                    "EQUIPE": "EQUIPE",
                    "CORRETOR": "CORRETOR",
                    "DT_BASE": "DATA ÚLTIMA AÇÃO",
                    "DIAS_DESDE_PENDENCIA": "DIAS DESDE PENDÊNCIA",
                }
            )

            df_pend_view["DATA ÚLTIMA AÇÃO"] = pd.to_datetime(
                df_pend_view["DATA ÚLTIMA AÇÃO"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

            df_pend_view = df_pend_view.sort_values(
                "DIAS DESDE PENDÊNCIA", ascending=False
            )

            def colorir_pend(val):
                return "color: #fbbf24; font-weight: bold;"

            st.dataframe(
                df_pend_view.style.applymap(
                    colorir_pend, subset=["DIAS DESDE PENDÊNCIA"]
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Clientes cuja **última ação é pendência** e que estão há "
                "**2 dias ou mais** sem movimentação (contando a partir de hoje). "
                "Priorizem a cobrança nesses casos."
            )

# ---------------------------------------------------------
# 3) VENDAS INFORMADAS PARADAS (5+ DIAS SEM VIRAR VENDA GERADA)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📝 Vendas informadas há mais de 5 dias (sem virar venda gerada)")

if df_last_acao.empty:
    st.info("Não há histórico suficiente para identificar vendas informadas.")
else:
    df_venda_info = df_last_acao[df_last_acao["STATUS_BASE"] == "VENDA INFORMADA"].copy()

    if df_venda_info.empty:
        st.success("✅ Não há vendas informadas pendentes de confirmação.")
    else:
        df_venda_info["DIAS_DESDE_INFO"] = (
            data_ref_geral_ts - df_venda_info["DT_BASE"]
        ).dt.days

        df_venda_info = df_venda_info[df_venda_info["DIAS_DESDE_INFO"] >= 5]

        if df_venda_info.empty:
            st.success("✅ Não há vendas informadas há 5 dias ou mais sem evolução.")
        else:
            df_info_view = df_venda_info[
                [
                    "NOME_CLIENTE_BASE",
                    "CPF_CLIENTE_BASE",
                    "EQUIPE",
                    "CORRETOR",
                    "DT_BASE",
                    "DIAS_DESDE_INFO",
                ]
            ].copy()

            df_info_view = df_info_view.rename(
                columns={
                    "NOME_CLIENTE_BASE": "CLIENTE",
                    "CPF_CLIENTE_BASE": "CPF",
                    "EQUIPE": "EQUIPE",
                    "CORRETOR": "CORRETOR",
                    "DT_BASE": "DATA ÚLTIMA AÇÃO",
                    "DIAS_DESDE_INFO": "DIAS DESDE VENDA INFORMADA",
                }
            )

            df_info_view["DATA ÚLTIMA AÇÃO"] = pd.to_datetime(
                df_info_view["DATA ÚLTIMA AÇÃO"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

            df_info_view = df_info_view.sort_values(
                "DIAS DESDE VENDA INFORMADA", ascending=False
            )

            def colorir_info(val):
                return "color: #f97373; font-weight: bold;"

            st.dataframe(
                df_info_view.style.applymap(
                    colorir_info, subset=["DIAS DESDE VENDA INFORMADA"]
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Vendas com **status final VENDA INFORMADA** há **5 dias ou mais**, "
                "sem registro posterior de VENDA GERADA. Cobrar construtora/cliente "
                "para confirmar ou atualizar o status."
            )
