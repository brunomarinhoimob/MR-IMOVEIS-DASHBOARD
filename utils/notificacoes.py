import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================================================
# CAMINHOS
# =========================================================
PASTA_DATA = Path("data")
ARQ_ESTADO = PASTA_DATA / "estado_anterior_clientes.csv"
ARQ_NOTIF = PASTA_DATA / "notificacoes.csv"

# =========================================================
# GARANTIR ESTRUTURA
# =========================================================
def _garantir_arquivos():
    PASTA_DATA.mkdir(exist_ok=True)

    if not ARQ_ESTADO.exists():
        pd.DataFrame(columns=[
            "CHAVE",
            "CLIENTE",
            "CPF",
            "SITUACAO"
        ]).to_csv(ARQ_ESTADO, index=False)

    if not ARQ_NOTIF.exists():
        pd.DataFrame(columns=[
            "DATA_HORA",
            "CLIENTE",
            "CPF",
            "TIPO",
            "SITUACAO"
        ]).to_csv(ARQ_NOTIF, index=False)

# =========================================================
# FUNÇÃO PRINCIPAL
# =========================================================
def gerar_notificacoes(df_atual: pd.DataFrame):
    _garantir_arquivos()

    if df_atual is None or df_atual.empty:
        return

    # ================= NORMALIZAÇÃO DE COLUNAS =================
    df = df_atual.copy()

    # Mapa de colunas ignorando acento / caixa
    col_map = {c.upper().strip(): c for c in df.columns}

    def pegar_coluna(nome):
        return col_map.get(nome)

    COL_CLIENTE = pegar_coluna("CLIENTE")
    COL_CPF = pegar_coluna("CPF")
    COL_SITUACAO = pegar_coluna("SITUACAO") or pegar_coluna("SITUAÇÃO")

    # Segurança absoluta
    if not COL_CLIENTE or not COL_SITUACAO:
        return

    # ================= NORMALIZA DADOS =================
    df["CLIENTE_N"] = df[COL_CLIENTE].astype(str).str.strip()
    df["CPF_N"] = (
        df[COL_CPF].astype(str).str.strip()
        if COL_CPF else ""
    )
    df["SITUACAO_N"] = df[COL_SITUACAO].astype(str).str.strip()

    # Remove linhas inválidas
    df = df[
        (df["CLIENTE_N"] != "") &
        (df["CLIENTE_N"].str.upper() != "CLIENTE TESTE") &
        (df["SITUACAO_N"] != "")
    ]

    if df.empty:
        return

    # ================= CHAVE ÚNICA =================
    df["CHAVE"] = df.apply(
        lambda x: x["CPF_N"]
        if x["CPF_N"] not in ["", "nan", "None"]
        else x["CLIENTE_N"],
        axis=1
    )

    # ================= LE ESTADO ANTERIOR =================
    df_estado_ant = pd.read_csv(ARQ_ESTADO)
    df_notif = pd.read_csv(ARQ_NOTIF)

    estado_map = (
        df_estado_ant.set_index("CHAVE")["SITUACAO"].to_dict()
        if not df_estado_ant.empty else {}
    )

    novas_notificacoes = []

    # ================= DETECTA EVENTOS =================
    for _, row in df.iterrows():
        chave = row["CHAVE"]
        cliente = row["CLIENTE_N"]
        cpf = row["CPF_N"]
        situacao = row["SITUACAO_N"]

        situacao_ant = estado_map.get(chave)

        # 🟢 CLIENTE NOVO
        if situacao_ant is None:
            novas_notificacoes.append({
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "CLIENTE": cliente,
                "CPF": cpf,
                "TIPO": "CLIENTE NOVO",
                "SITUACAO": situacao
            })

        # 🔵 MUDANÇA DE SITUAÇÃO
        elif situacao_ant != situacao:
            novas_notificacoes.append({
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "CLIENTE": cliente,
                "CPF": cpf,
                "TIPO": "MUDANÇA DE SITUAÇÃO",
                "SITUACAO": situacao
            })

    # ================= SALVA NOTIFICAÇÕES =================
    if novas_notificacoes:
        df_notif = pd.concat(
            [pd.DataFrame(novas_notificacoes), df_notif],
            ignore_index=True
        )
        df_notif.to_csv(ARQ_NOTIF, index=False)

    # ================= ATUALIZA ESTADO =================
    df_estado_novo = (
        df[["CHAVE", "CLIENTE_N", "CPF_N", "SITUACAO_N"]]
        .rename(columns={
            "CLIENTE_N": "CLIENTE",
            "CPF_N": "CPF",
            "SITUACAO_N": "SITUACAO"
        })
        .drop_duplicates()
    )

    df_estado_novo.to_csv(ARQ_ESTADO, index=False)

# =========================================================
# LEITURA DAS NOTIFICAÇÕES
# =========================================================
def obter_notificacoes(qtd=20):
    if not ARQ_NOTIF.exists():
        return pd.DataFrame()

    df = pd.read_csv(ARQ_NOTIF)

    if df.empty:
        return df

    return df.head(qtd)
