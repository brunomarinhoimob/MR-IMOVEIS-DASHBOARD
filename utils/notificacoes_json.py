import json
import uuid
from pathlib import Path
from datetime import datetime
import pandas as pd

# =================================================
# CAMINHOS DOS DADOS
# =================================================
BASE_DIR = Path("data")
ARQ_NOTIFICACOES = BASE_DIR / "notificacoes.json"
ARQ_SNAPSHOT = BASE_DIR / "snapshot_clientes.json"

# =================================================
# UTILIDADES JSON
# =================================================
def _ler_json(caminho: Path) -> dict:
    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}
    return {}

def _salvar_json(caminho: Path, data: dict):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =================================================
# STATUS REAL DO CLIENTE (MESMA LÓGICA DA 08_CLIENTES_MR)
# =================================================
def obter_status_atual_cliente(grupo: pd.DataFrame) -> pd.Series | None:
    grupo = grupo.copy()

    if "DIA" not in grupo.columns:
        return None

    grupo = grupo[grupo["DIA"].notna()]
    if grupo.empty:
        return None

    grupo = grupo.sort_values("DIA")

    # se houve desistência, ignora histórico anterior
    desist_mask = grupo["SITUACAO_EXATA"].str.contains("DESIST", na=False)
    if desist_mask.any():
        idx = grupo[desist_mask].index[-1]
        grupo = grupo.loc[idx:]

    # prioridade absoluta para venda
    vendas = grupo[grupo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]

    # caso normal: último estado válido
    return grupo.iloc[-1]

# =================================================
# PROCESSADOR DE EVENTOS (NOTIFICAÇÕES)
# =================================================
def processar_eventos(df: pd.DataFrame):
    """
    Gera notificações persistentes quando:
    - um cliente aparece pela primeira vez
    - o STATUS REAL do cliente muda

    Usa SITUACAO_EXATA como fonte da verdade.
    """

    if df is None or df.empty:
        return

    colunas_necessarias = {
        "CHAVE_CLIENTE",
        "CORRETOR",
        "SITUACAO_EXATA",
        "STATUS_BASE",
        "DIA",
    }

    if not colunas_necessarias.issubset(df.columns):
        return

    # normalizações básicas
    df = df.copy()
    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    df["STATUS_BASE"] = df["STATUS_BASE"].astype(str).str.upper().str.strip()
    df["SITUACAO_EXATA"] = df["SITUACAO_EXATA"].astype(str).str.strip()

    # -------------------------
    # Estado salvo
    # -------------------------
    notificacoes = _ler_json(ARQ_NOTIFICACOES)
    snapshot = _ler_json(ARQ_SNAPSHOT)

    agora = datetime.now().isoformat(timespec="seconds")
    novo_snapshot = {}

    # -------------------------
    # Processa cliente por cliente
    # -------------------------
    for chave, grupo in df.groupby("CHAVE_CLIENTE"):
        status_row = obter_status_atual_cliente(grupo)
        if status_row is None:
            continue

        status_atual = status_row["SITUACAO_EXATA"]
        corretor = status_row["CORRETOR"]
        cliente = chave.split("|")[0].strip()

        if not status_atual:
            continue

        # garante estrutura por corretor
        if corretor not in notificacoes:
            notificacoes[corretor] = []

        estado_antigo = snapshot.get(chave)

        # -------------------------
        # CLIENTE NOVO
        # -------------------------
        if not estado_antigo:
            notificacoes[corretor].append({
                "id": str(uuid.uuid4()),
                "cliente": cliente,
                "status": status_atual,
                "tipo": "NOVO_CLIENTE",
                "timestamp": agora,
                "lido": False
            })

        # -------------------------
        # MUDANÇA DE STATUS REAL
        # -------------------------
        elif estado_antigo.get("status") != status_atual:
            notificacoes[corretor].append({
                "id": str(uuid.uuid4()),
                "cliente": cliente,
                "de": estado_antigo.get("status"),
                "para": status_atual,
                "tipo": "MUDANCA_STATUS",
                "timestamp": agora,
                "lido": False
            })

        # -------------------------
        # Atualiza snapshot
        # -------------------------
        novo_snapshot[chave] = {
            "status": status_atual,
            "corretor": corretor
        }

    # -------------------------
    # Persistência
    # -------------------------
    _salvar_json(ARQ_NOTIFICACOES, notificacoes)
    _salvar_json(ARQ_SNAPSHOT, novo_snapshot)
