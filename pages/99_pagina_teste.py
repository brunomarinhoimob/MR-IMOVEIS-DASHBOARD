import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, datetime, timedelta

from utils.bootstrap import iniciar_app
from app_dashboard import carregar_dados_planilha
from streamlit_autorefresh import st_autorefresh


# ---------------------------------------------------------
# CONFIG DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Meta & Planejamento – MR Imóveis",
    page_icon="🎯",
    layout="wide",
)

st_autorefresh(interval=30 * 1000, key="auto_refresh_meta")


# ---------------------------------------------------------
# BOOTSTRAP (LOGIN + NOTIFICAÇÕES)
# ---------------------------------------------------------
iniciar_app()
perfil = st.session_state.get("perfil")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def _norm_str(s):
    return str(s).upper().strip() if s is not None else ""


def format_int(v: int) -> str:
    try:
        return f"{int(v)}"
    except Exception:
        return "0"


def format_pct(x: float) -> str:
    return f"{x:.1%}"


def obter_vendas_unicas(df_scope: pd.DataFrame, status_final_map=None):
    """
    Vendas únicas: considera VENDA GERADA e mantém 1 por cliente (última ocorrência).
    Exclui clientes cujo status final seja DESISTIU (quando status_final_map é fornecido).
    """
    if df_scope is None or df_scope.empty:
        return df_scope.iloc[0:0].copy()

    df_scope = df_scope.copy()

    if "CHAVE_CLIENTE" not in df_scope.columns:
        # fallback: tenta criar chave com nome/cpf se existirem
        nome_col = "NOME_CLIENTE_BASE" if "NOME_CLIENTE_BASE" in df_scope.columns else None
        cpf_col = "CPF_CLIENTE_BASE" if "CPF_CLIENTE_BASE" in df_scope.columns else None
        if nome_col:
            nome = df_scope[nome_col].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        else:
            nome = pd.Series(["NÃO INFORMADO"] * len(df_scope))
        if cpf_col:
            cpf = df_scope[cpf_col].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        else:
            cpf = pd.Series([""] * len(df_scope))
        df_scope["CHAVE_CLIENTE"] = nome + " | " + cpf

    # filtra status venda
    if "STATUS_BASE" not in df_scope.columns:
        return df_scope.iloc[0:0].copy()

    df_v = df_scope[df_scope["STATUS_BASE"] == "VENDA GERADA"].copy()
    if df_v.empty:
        return df_v

    # excluir desistidos pelo status final do cliente
    if status_final_map is not None:
        try:
            if isinstance(status_final_map, dict):
                df_v["STATUS_FINAL"] = df_v["CHAVE_CLIENTE"].map(status_final_map)
            else:
                df_v["STATUS_FINAL"] = df_v["CHAVE_CLIENTE"].map(status_final_map.to_dict())
            df_v = df_v[df_v["STATUS_FINAL"] != "DESISTIU"]
        except Exception:
            pass

    # mantém 1 por cliente (última ocorrência por data)
    if "DIA" in df_v.columns:
        df_v = df_v.sort_values("DIA")
    df_v = df_v.groupby("CHAVE_CLIENTE").tail(1)

    return df_v


def contar_analises_volume(df: pd.DataFrame) -> int:
    """Volume de análises = EM ANÁLISE + REANÁLISE."""
    if df.empty:
        return 0
    s = df["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
    return int((s == "EM ANÁLISE").sum() + (s == "REANÁLISE").sum())


def contar_aprovacoes(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    s = df["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
    return int((s == "APROVADO").sum())


def ultimo_dia_com_registro(df: pd.DataFrame) -> date | None:
    if df.empty or "DIA" not in df.columns:
        return None
    d = pd.to_datetime(df["DIA"], errors="coerce").dropna()
    if d.empty:
        return None
    return d.max().date()


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df_global = carregar_dados_planilha(_refresh_key=st.session_state.get("refresh_planilha"))

if df_global is None or df_global.empty:
    st.error("Erro ao carregar a planilha.")
    st.stop()

# Garantias mínimas de colunas
df_global.columns = [c.strip().upper() for c in df_global.columns]

if "DIA" not in df_global.columns:
    # tenta achar DATA
    if "DATA" in df_global.columns:
        df_global["DIA"] = pd.to_datetime(df_global["DATA"], errors="coerce")
    else:
        st.error("A planilha não possui coluna DIA/DATA.")
        st.stop()

df_global["DIA"] = pd.to_datetime(df_global["DIA"], errors="coerce")

if "STATUS_BASE" not in df_global.columns:
    # se vier só STATUS, tenta padronizar de forma simples
    possiveis = ["STATUS", "SITUACAO", "SITUAÇÃO", "STATUS ATUAL", "SITUACAO ATUAL", "SITUAÇÃO ATUAL"]
    col_status = next((c for c in possiveis if c in df_global.columns), None)
    if col_status is None:
        st.error("Nenhuma coluna de status encontrada (STATUS/STATUS_BASE/SITUAÇÃO).")
        st.stop()
    df_global["STATUS_BASE"] = df_global[col_status].fillna("").astype(str).str.upper().str.strip()

# Normalizações padrão
for col in ["EQUIPE", "CORRETOR"]:
    if col not in df_global.columns:
        df_global[col] = "NÃO INFORMADO"
    df_global[col] = df_global[col].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()

# CHAVE_CLIENTE (se não existir, tenta criar)
if "CHAVE_CLIENTE" not in df_global.columns:
    nome_col = "NOME_CLIENTE_BASE" if "NOME_CLIENTE_BASE" in df_global.columns else None
    cpf_col = "CPF_CLIENTE_BASE" if "CPF_CLIENTE_BASE" in df_global.columns else None
    if nome_col:
        nome = df_global[nome_col].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
    else:
        nome = pd.Series(["NÃO INFORMADO"] * len(df_global))
    if cpf_col:
        cpf = df_global[cpf_col].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    else:
        cpf = pd.Series([""] * len(df_global))
    df_global["CHAVE_CLIENTE"] = nome + " | " + cpf

# Status final por cliente (histórico completo)
df_aux_final = df_global.sort_values("DIA").groupby("CHAVE_CLIENTE").tail(1)
status_final_por_cliente = df_aux_final.set_index("CHAVE_CLIENTE")["STATUS_BASE"].to_dict()


# ---------------------------------------------------------
# SIDEBAR – VISÃO E FILTROS DE ESCOPO
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

visao = st.sidebar.radio(
    "Visão",
    ["MR IMÓVEIS", "Equipe", "Corretor"],
    index=0,
)

# 🔒 Trava de corretor: força visão e escopo
df_scope = df_global.copy()

if perfil == "corretor":
    visao = "Corretor"
    if "CORRETOR" in df_scope.columns:
        df_scope = df_scope[df_scope["CORRETOR"] == nome_usuario]

# Seleção de equipe/corretor (para gestor)
equipe_sel = None
corretor_sel = None

if visao == "Equipe":
    equipes = sorted(df_scope["EQUIPE"].dropna().astype(str).unique())
    equipe_sel = st.sidebar.selectbox("Equipe", equipes) if equipes else None
    if equipe_sel:
        df_scope = df_scope[df_scope["EQUIPE"] == str(equipe_sel)]
elif visao == "Corretor":
    equipes = sorted(df_scope["EQUIPE"].dropna().astype(str).unique())
    if equipes and perfil != "corretor":
        equipe_sel = st.sidebar.selectbox("Equipe", equipes)
        df_scope = df_scope[df_scope["EQUIPE"] == str(equipe_sel)]

    corretores = sorted(df_scope["CORRETOR"].dropna().astype(str).unique()) if "CORRETOR" in df_scope.columns else []
    if corretores and perfil != "corretor":
        corretor_sel = st.sidebar.selectbox("Corretor", corretores)
        df_scope = df_scope[df_scope["CORRETOR"] == str(corretor_sel)]

# Segurança: se ficou vazio
if df_scope.empty:
    st.warning("Sem dados para o escopo selecionado.")
    st.stop()


# ---------------------------------------------------------
# TOPO – PLANEJAMENTO (MÊS COMERCIAL)
# ---------------------------------------------------------
st.title("🎯 Meta & Planejamento – MR Imóveis")

st.caption(
    f"Visão: **{visao}**"
    + (f" | Equipe: **{equipe_sel}**" if equipe_sel else "")
    + (f" | Corretor: **{corretor_sel}**" if corretor_sel else "")
)

st.markdown("---")

colA, colB, colC = st.columns([1.1, 1.1, 1.2])

with colA:
    tipo_meta = st.selectbox(
        "Selecione o tipo de meta",
        ["Número de Análises", "Número de Aprovações", "Número de Vendas"],
        index=2,
    )

with colB:
    hoje = date.today()
    # sugestão: mês corrente
    dt_ini_default = date(hoje.year, hoje.month, 1)
    # fim padrão = último dia do mês (cálculo)
    prox_mes = (dt_ini_default.replace(day=28) + timedelta(days=4)).replace(day=1)
    dt_fim_default = prox_mes - timedelta(days=1)

    dt_ini_mes = st.date_input(
        "Início do mês comercial",
        value=dt_ini_default,
        format="DD/MM/YYYY",
    )
    dt_fim_mes = st.date_input(
        "Fim do mês comercial",
        value=dt_fim_default,
        format="DD/MM/YYYY",
    )

with colC:
    meta_valor = st.number_input(
        "Valor da meta (número absoluto)",
        min_value=0,
        step=1,
        value=0,
    )

if dt_ini_mes > dt_fim_mes:
    st.error("A data inicial do mês comercial não pode ser maior que a data final.")
    st.stop()


# ---------------------------------------------------------
# BASE DO MÊS COMERCIAL (PARA O GRÁFICO E REAL)
# ---------------------------------------------------------
df_mes = df_scope.copy()
df_mes["DIA_DATA"] = pd.to_datetime(df_mes["DIA"], errors="coerce").dt.date
df_mes = df_mes[(df_mes["DIA_DATA"] >= dt_ini_mes) & (df_mes["DIA_DATA"] <= dt_fim_mes)].copy()

# Último dia REAL (para cortar a linha real)
ultimo_dia_planilha_no_mes = ultimo_dia_com_registro(df_mes)
if ultimo_dia_planilha_no_mes is None:
    ultimo_dia_planilha_no_mes = dt_ini_mes  # evita quebrar

# Base até o último dia disponível na planilha (REAL)
df_real = df_mes[df_mes["DIA_DATA"] <= ultimo_dia_planilha_no_mes].copy()

# Lista completa de dias do mês comercial (para a linha da META)
dias_mes = pd.date_range(start=dt_ini_mes, end=dt_fim_mes, freq="D")
dias_mes_lista = [d.date() for d in dias_mes]

# Lista de dias até o último dia na planilha (para a linha REAL)
dias_real = pd.date_range(start=dt_ini_mes, end=ultimo_dia_planilha_no_mes, freq="D")
dias_real_lista = [d.date() for d in dias_real]


# ---------------------------------------------------------
# CÁLCULOS DO INDICADOR SELECIONADO
# ---------------------------------------------------------
def calcular_total_real(df_real_base: pd.DataFrame) -> int:
    if tipo_meta == "Número de Análises":
        return contar_analises_volume(df_real_base)
    if tipo_meta == "Número de Aprovações":
        return contar_aprovacoes(df_real_base)
    # Vendas
    df_v = obter_vendas_unicas(df_real_base, status_final_map=status_final_por_cliente)
    return int(len(df_v))


def serie_diaria_real(df_real_base: pd.DataFrame) -> pd.Series:
    """
    Retorna contagem diária do indicador, reindexado nos dias_real_lista.
    """
    if df_real_base.empty:
        return pd.Series([0] * len(dias_real_lista), index=dias_real_lista)

    if tipo_meta == "Número de Análises":
        s = df_real_base["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
        df_ind = df_real_base[(s == "EM ANÁLISE") | (s == "REANÁLISE")].copy()
        cont = df_ind.groupby("DIA_DATA").size().reindex(dias_real_lista, fill_value=0)
        return cont

    if tipo_meta == "Número de Aprovações":
        s = df_real_base["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
        df_ind = df_real_base[s == "APROVADO"].copy()
        cont = df_ind.groupby("DIA_DATA").size().reindex(dias_real_lista, fill_value=0)
        return cont

    # Vendas únicas por dia (data do registro do “último” status de venda por cliente dentro do range real)
    df_v = obter_vendas_unicas(df_real_base, status_final_map=status_final_por_cliente).copy()
    if df_v.empty:
        return pd.Series([0] * len(dias_real_lista), index=dias_real_lista)
    df_v["DIA_DATA"] = pd.to_datetime(df_v["DIA"], errors="coerce").dt.date
    cont = df_v.groupby("DIA_DATA").size().reindex(dias_real_lista, fill_value=0)
    return cont


real_total = calcular_total_real(df_real)
faltam = max(int(meta_valor) - int(real_total), 0)
pct = (real_total / meta_valor) if meta_valor > 0 else 0.0

# Dias restantes (para ritmo) — usa HOJE, mas nunca fora do mês
hoje = date.today()
if hoje < dt_ini_mes:
    base_ritmo = dt_ini_mes
elif hoje > dt_fim_mes:
    base_ritmo = dt_fim_mes
else:
    base_ritmo = hoje

dias_restantes = max((dt_fim_mes - base_ritmo).days + 1, 0)  # inclui o dia de hoje
ritmo_necessario = (faltam / dias_restantes) if dias_restantes > 0 else 0.0


# ---------------------------------------------------------
# CARDS – META X REAL
# ---------------------------------------------------------
st.subheader("📌 Meta x Real (mês comercial)")

c1, c2, c3, c4 = st.columns(4)

c1.metric("🎯 Meta", format_int(meta_valor))
c2.metric("✅ Real (até a última data da planilha)", format_int(real_total))
c3.metric("⏳ Falta", format_int(faltam))
c4.metric("📊 % Atingido", format_pct(pct))

st.caption(
    f"REAL considerado até **{ultimo_dia_planilha_no_mes.strftime('%d/%m/%Y')}** (última data presente na planilha dentro do mês comercial)."
)

st.markdown("---")


# ---------------------------------------------------------
# INTELIGÊNCIA – CONVERSÕES (últimos 90 dias)
# ---------------------------------------------------------
st.subheader("🧠 Planejamento de Produção (base: últimos 90 dias)")

data_max_global = pd.to_datetime(df_scope["DIA"], errors="coerce").dropna()
if data_max_global.empty:
    st.info("Sem datas válidas para calcular histórico.")
    df_90 = df_scope.iloc[0:0].copy()
else:
    max_d = data_max_global.max()
    min_90 = max_d - pd.Timedelta(days=90)
    df_90 = df_scope[(df_scope["DIA"] >= min_90) & (df_scope["DIA"] <= max_d)].copy()
    df_90["DIA_DATA"] = pd.to_datetime(df_90["DIA"], errors="coerce").dt.date

# Métricas base histórico
analises_90 = contar_analises_volume(df_90)
aprov_90 = contar_aprovacoes(df_90)
vendas_90 = len(obter_vendas_unicas(df_90, status_final_map=status_final_por_cliente)) if not df_90.empty else 0

# Conversões (evita divisão por zero)
analises_por_aprov = (analises_90 / aprov_90) if aprov_90 > 0 else 0.0
aprov_por_venda = (aprov_90 / vendas_90) if vendas_90 > 0 else 0.0
analises_por_venda = (analises_90 / vendas_90) if vendas_90 > 0 else 0.0

# Necessidades conforme tipo de meta
need_analises = 0
need_aprov = 0
need_meta_dia = 0.0
need_analises_dia = 0.0
need_aprov_dia = 0.0

if meta_valor > 0:
    if tipo_meta == "Número de Análises":
        need_meta_dia = (meta_valor / ((dt_fim_mes - dt_ini_mes).days + 1)) if (dt_fim_mes >= dt_ini_mes) else 0.0
        # para análises, “produção” é a própria meta
        need_analises = meta_valor
        need_analises_dia = (faltam / dias_restantes) if dias_restantes > 0 else 0.0

    elif tipo_meta == "Número de Aprovações":
        need_aprov = meta_valor
        need_analises = int(np.ceil(meta_valor * analises_por_aprov)) if analises_por_aprov > 0 else 0
        need_aprov_dia = (faltam / dias_restantes) if dias_restantes > 0 else 0.0
        need_analises_dia = (max(need_analises - analises_90, 0) / dias_restantes) if dias_restantes > 0 else 0.0

    else:  # Vendas
        need_meta_dia = (faltam / dias_restantes) if dias_restantes > 0 else 0.0
        need_aprov = int(np.ceil(meta_valor * aprov_por_venda)) if aprov_por_venda > 0 else 0
        need_analises = int(np.ceil(meta_valor * analises_por_venda)) if analises_por_venda > 0 else 0
        need_aprov_dia = (max(need_aprov - aprov_90, 0) / dias_restantes) if dias_restantes > 0 else 0.0
        need_analises_dia = (max(need_analises - analises_90, 0) / dias_restantes) if dias_restantes > 0 else 0.0

colP1, colP2, colP3, colP4 = st.columns(4)
with colP1:
    st.metric("📦 Base 90 dias – Análises (vol.)", format_int(analises_90))
with colP2:
    st.metric("📦 Base 90 dias – Aprovações", format_int(aprov_90))
with colP3:
    st.metric("📦 Base 90 dias – Vendas (únicas)", format_int(vendas_90))
with colP4:
    st.metric("📆 Dias restantes (mês comercial)", format_int(dias_restantes))

colP5, colP6, colP7 = st.columns(3)
with colP5:
    st.metric("🧩 Análises por Aprovação", f"{analises_por_aprov:.2f}")
with colP6:
    st.metric("🧩 Aprovações por Venda", f"{aprov_por_venda:.2f}")
with colP7:
    st.metric("🧩 Análises por Venda", f"{analises_por_venda:.2f}")

st.markdown("### 🎯 Necessidade (para bater a meta)")

n1, n2, n3 = st.columns(3)
with n1:
    st.metric("🔍 Análises necessárias", format_int(need_analises))
with n2:
    st.metric("✔️ Aprovações necessárias", format_int(need_aprov))
with n3:
    st.metric("🔥 Ritmo necessário/dia (meta selecionada)", f"{ritmo_necessario:.2f}")

st.markdown("### 📌 Ritmo diário sugerido (prático)")
r1, r2, r3 = st.columns(3)
with r1:
    if tipo_meta == "Número de Análises":
        st.metric("🔍 Análises/dia necessárias", f"{need_analises_dia:.2f}")
    else:
        st.metric("🔍 Análises/dia sugeridas", f"{need_analises_dia:.2f}")
with r2:
    if tipo_meta in ["Número de Aprovações", "Número de Vendas"]:
        st.metric("✔️ Aprovações/dia sugeridas", f"{need_aprov_dia:.2f}")
    else:
        st.metric("✔️ Aprovações/dia sugeridas", "-")
with r3:
    st.metric("⏳ Falta (meta selecionada)", format_int(faltam))

st.caption(
    "Obs: Base de conversão calculada nos **últimos 90 dias** do mesmo escopo (MR/Equipe/Corretor)."
)

st.markdown("---")


# ---------------------------------------------------------
# GRÁFICO – META x REAL (ACUMULADO)
# ---------------------------------------------------------
st.subheader("📈 Acompanhamento — Meta x Real (acumulado)")

if meta_valor <= 0:
    st.info("Defina um valor de meta acima de 0 para exibir o gráfico.")
else:
    # Série REAL acumulada (até o último dia da planilha)
    cont_real = serie_diaria_real(df_real)
    real_acum = cont_real.cumsum()

    # Série META linear (do início ao fim do mês comercial)
    meta_linear = np.linspace(0, meta_valor, num=len(dias_mes_lista), endpoint=True)

    # Monta DF de plot
    df_plot_parts = []

    # REAL (só até último dia da planilha)
    df_real_line = pd.DataFrame({
        "DIA": pd.to_datetime(dias_real_lista),
        "Série": "Real",
        "Valor": real_acum.values
    })
    df_plot_parts.append(df_real_line)

    # META (até fim do mês)
    df_meta_line = pd.DataFrame({
        "DIA": pd.to_datetime(dias_mes_lista),
        "Série": "Meta",
        "Valor": meta_linear
    })
    df_plot_parts.append(df_meta_line)

    df_plot = pd.concat(df_plot_parts, ignore_index=True)

    chart = (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X("DIA:T", title="Dia"),
            y=alt.Y("Valor:Q", title="Total acumulado"),
            color=alt.Color("Série:N", title=""),
        )
        .properties(height=360)
    )

    st.altair_chart(chart, use_container_width=True)

    # Leitura inteligente
    if dias_restantes > 0:
        proj_final = real_total + ritmo_necessario * dias_restantes
    else:
        proj_final = real_total

    # Comparação de onde deveria estar hoje pela meta linear
    # posição do "hoje" dentro do mês (clamp)
    hoje_clamped = min(max(hoje, dt_ini_mes), dt_fim_mes)
    idx_hoje = (hoje_clamped - dt_ini_mes).days
    idx_hoje = max(min(idx_hoje, len(meta_linear) - 1), 0)
    meta_ate_hoje = meta_linear[idx_hoje]

    status_txt = ""
    if real_total >= meta_ate_hoje * 1.03:
        status_txt = "🟢 **Ritmo acima do necessário.** Mantendo assim, a meta tende a ser batida com folga."
    elif real_total >= meta_ate_hoje * 0.97:
        status_txt = "🟡 **No ritmo (na risca).** Pequenas oscilações podem colocar em risco — mantenha consistência."
    else:
        status_txt = "🔴 **Abaixo do ritmo.** Precisa aumentar o volume diário para recuperar o atraso."

    st.markdown(status_txt)
    st.caption(
        f"Hoje (considerando {hoje_clamped.strftime('%d/%m/%Y')}), pela linha da meta você deveria estar em ~{meta_ate_hoje:.1f}. "
        f"Você está em {real_total}."
    )

st.markdown("---")
st.caption(
    "Regra da página: **Real** para na última data registrada na planilha. **Meta** segue até o fim do mês comercial."
)
