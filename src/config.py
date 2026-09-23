from datetime import datetime
from pathlib import Path

import yaml


# ============================================================
# LOCALIZAÇÃO DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_CONFIG = BASE_DIR / "config" / "config.yaml"


# ============================================================
# CARREGAMENTO
# ============================================================

def carregar_configuracoes() -> dict:
    """
    Carrega e valida as configurações definidas em config.yaml.
    """

    if not ARQUIVO_CONFIG.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: "
            f"{ARQUIVO_CONFIG}"
        )

    with ARQUIVO_CONFIG.open("r", encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)

    if not config:
        raise ValueError(
            "O arquivo config.yaml está vazio."
        )

    return config


CONFIG = carregar_configuracoes()


# ============================================================
# FONTE
# ============================================================

FONTE = CONFIG["fonte"]

BASE_URL = FONTE["base_url"].rstrip("/")

DATASET_SLUG = FONTE["dataset"]

API_URL = f"{BASE_URL}/datasets/{DATASET_SLUG}"

DATA_INICIAL = datetime.strptime(
    FONTE["data_inicial"],
    "%Y-%m",
)


# ============================================================
# COLETA
# ============================================================

COLETA = CONFIG["coleta"]

INTERVALO_ENTRE_DOWNLOADS = float(
    COLETA["intervalo_downloads_segundos"]
)

MAX_TENTATIVAS = int(
    COLETA["max_tentativas"]
)

TIMEOUT_CONEXAO = int(
    COLETA["timeout_conexao_segundos"]
)

TIMEOUT_LEITURA = int(
    COLETA["timeout_leitura_segundos"]
)


# ============================================================
# ARMAZENAMENTO
# ============================================================

ARMAZENAMENTO = CONFIG["armazenamento"]


def resolver_caminho(caminho: str) -> Path:
    """
    Converte caminhos relativos do YAML em caminhos absolutos
    relativos à raiz do projeto.
    """

    path = Path(caminho)

    if path.is_absolute():
        return path

    return BASE_DIR / path


PASTA_RAW = resolver_caminho(
    ARMAZENAMENTO["pasta_raw"]
)

PASTA_LOGS = resolver_caminho(
    ARMAZENAMENTO["pasta_logs"]
)

ARQUIVO_MANIFESTO = resolver_caminho(
    ARMAZENAMENTO["arquivo_manifesto"]
)


# ============================================================
# CONSTANTES INTERNAS
# ============================================================

STATUS_HTTP_RETRY = {
    429,
    500,
    502,
    503,
    504,
}