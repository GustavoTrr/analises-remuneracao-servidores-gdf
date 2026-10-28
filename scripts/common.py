import hashlib
import hmac
import os
import re
import sys
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path


DATA_ROOT = Path(os.getenv("DATA_ROOT", "/data"))
RAW_DIR = DATA_ROOT / "raw"
CURATED_DIR = DATA_ROOT / "curated"
QUARANTINE_DIR = DATA_ROOT / "quarantine"
REPORT_DIR = DATA_ROOT / "reports"

TEXT_COLUMNS = (
    "nome",
    "cpf",
    "orgao",
    "cargo",
    "funcao",
    "situacao",
    "codigo_orgao",
    "matricula",
)
INTEGER_COLUMNS = ("mes", "ano")
MONEY_COLUMNS = (
    "remuneracao_basica",
    "beneficios",
    "valor_funcao",
    "comissao_conselheiro",
    "hora_extra",
    "verbas_eventuais",
    "verbas_judiciais",
    "descontos_a_maior",
    "licenca_premio",
    "irrf",
    "seguridade_social",
    "teto_redutor",
    "outros_recebimentos",
    "outros_descontos_obrigatorios",
    "pagamento_a_maior",
    "bruto",
    "liquido",
)
SOURCE_COLUMNS = TEXT_COLUMNS[:6] + INTEGER_COLUMNS + TEXT_COLUMNS[6:] + MONEY_COLUMNS

ALIASES = {
    "seg_social": "seguridade_social",
    "pagamentos_a_maior": "pagamento_a_maior",
}


def normalize_column(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    token = re.sub(r"[^a-zA-Z0-9]+", "_", without_accents).strip("_").lower()
    token = re.sub(r"_(?:do|da|de|dos|das)_", "_", f"_{token}_").strip("_")
    return ALIASES.get(token, token)


def parse_money(value: str) -> str:
    value = value.strip().replace("R$", "").replace(" ", "")
    if not value:
        return ""
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    if value.startswith("."):
        value = "0" + value
    elif value.startswith("-."):
        value = value.replace("-.", "-0.", 1)
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"valor monetario inválido: {value!r}") from error
    if not amount.is_finite():
        raise ValueError(f"valor monetario inválido: {value!r}")
    return format(amount.quantize(Decimal("0.01")), ".2f")


def competence_from_name(filename: str) -> tuple[int, int]:
    match = re.search(r"(?<!\d)((?:19|20)\d{2})[-_](0[1-9]|1[0-2])(?!\d)", filename)
    if not match:
        raise ValueError(f"não foi possível identificar a competência em {filename!r}")
    return int(match.group(1)), int(match.group(2))


def csv_encoding(path: Path) -> str:
    with path.open("rb") as source:
        header = source.readline()
    try:
        header.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "cp1252"
    return "utf-8-sig"


def csv_delimiter(path: Path) -> str:
    with path.open(encoding=csv_encoding(path), newline="") as source:
        header = source.readline()
    comma_count = header.count(",")
    semicolon_count = header.count(";")
    if comma_count == semicolon_count:
        raise ValueError(f"não foi possível identificar o delimitador CSV em {path.name}")
    return ";" if semicolon_count > comma_count else ","


def identity_secret() -> bytes:
    secret = os.getenv("IDENTITY_HMAC_KEY", "").strip()
    if not secret:
        raise RuntimeError(
            "IDENTITY_HMAC_KEY não configurada no .env. Gere um segredo com "
            '`python -c "import secrets; print(secrets.token_hex(32))"` e mantenha-o fora do Git.'
        )
    return secret.encode("utf-8")


def servidor_key(nome: str, cpf: str, secret: bytes) -> str:
    decomposed = unicodedata.normalize("NFKD", nome.strip().upper())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    identity = f"{re.sub(r'\s+', ' ', without_accents)}|{cpf.strip()}"
    return hmac.new(secret, identity.encode("utf-8"), hashlib.sha256).hexdigest()


def competencia_inicial() -> tuple[int, int] | None:
    configurada = os.getenv("COMPETENCIA_INICIAL", "").strip()
    if not configurada:
        return None
    match = re.fullmatch(r"((?:19|20)\d{2})[-/_](0[1-9]|1[0-2])", configurada)
    if not match:
        print(
            f"[aviso] COMPETENCIA_INICIAL inválida ({configurada!r}); "
            "use AAAA-MM. Processando todas as competências.",
            file=sys.stderr,
        )
        return None
    return int(match.group(1)), int(match.group(2))


def competencia_permitida(year: int, month: int, inicio: tuple[int, int] | None) -> bool:
    return inicio is None or (year, month) >= inicio