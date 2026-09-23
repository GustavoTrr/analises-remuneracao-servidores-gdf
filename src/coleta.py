import json
import random
import time
from datetime import datetime
from pathlib import Path

import requests

from utils import (
    calcular_sha256,
    extrair_competencia,
    limpar_nome_arquivo,
)

from config import (
    DATASET_SLUG,
    BASE_URL,
    DATA_INICIAL,
    PASTA_RAW,
    PASTA_LOG,
    ARQUIVO_MANIFESTO,
    INTERVALO_ENTRE_DOWNLOADS,
    MAX_TENTATIVAS,
    TIMEOUT_CONEXAO,
    TIMEOUT_LEITURA,
    STATUS_RETRY,
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DATASET_SLUG = "portal-da-transparencia-remuneracao-dos-servidores"

BASE_URL = "https://www.dados.df.gov.br/o/dados-abertos/v1.0"

API_URL = f"{BASE_URL}/datasets/{DATASET_SLUG}"

DATA_LIMITE = datetime(2022, 1, 1)

PASTA_RAW = Path("./data/raw")
PASTA_LOG = Path("./logs")

ARQUIVO_LOG = PASTA_LOG / "downloads.jsonl"


# ------------------------------------------------------------
# Política de acesso
# ------------------------------------------------------------

INTERVALO_ENTRE_DOWNLOADS = 2
MAX_TENTATIVAS = 3

TIMEOUT_CONEXAO = 10
TIMEOUT_LEITURA = 120

STATUS_RETRY = {429, 500, 502, 503, 504}


# ============================================================
# HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "TransparenciaDF-AcademicResearch/1.0 "
        "(coleta de dados publicos para pesquisa academica)"
    ),
    "Accept": "application/json,*/*",
})


# ============================================================
# LOG / MANIFEST
# ============================================================

def registrar_log(**dados):
    """
    Registra cada evento em JSON Lines.

    Um JSON por linha facilita processamento posterior
    sem necessidade de banco de dados.
    """

    PASTA_LOG.mkdir(parents=True, exist_ok=True)

    registro = {
        "timestamp": datetime.now().astimezone().isoformat(),
        **dados,
    }

    with ARQUIVO_LOG.open("a", encoding="utf-8") as arquivo:
        arquivo.write(
            json.dumps(registro, ensure_ascii=False) + "\n"
        )


# ============================================================
# RETRY
# ============================================================

def calcular_espera(tentativa: int) -> float:
    """
    Exponential backoff com pequeno jitter.

    tentativa 1 -> aproximadamente 2s
    tentativa 2 -> aproximadamente 4s
    tentativa 3 -> aproximadamente 8s
    """

    base = 2 ** tentativa
    jitter = random.uniform(0, 1)

    return base + jitter


def obter_retry_after(response):
    """
    Tenta interpretar Retry-After quando fornecido pelo servidor.

    Nesta versão simples tratamos o formato em segundos.
    """

    valor = response.headers.get("Retry-After")

    if valor and valor.isdigit():
        return int(valor)

    return None


# ============================================================
# DOWNLOAD
# ============================================================

def baixar_arquivo(url: str, destino: Path):
    """
    Faz download em streaming com retry.

    O download é realizado inicialmente em arquivo .part.
    Somente após conclusão ele é renomeado para o nome final.
    """

    arquivo_temporario = destino.with_suffix(
        destino.suffix + ".part"
    )

    for tentativa in range(1, MAX_TENTATIVAS + 1):

        try:

            with session.get(
                url,
                stream=True,
                timeout=(TIMEOUT_CONEXAO, TIMEOUT_LEITURA),
            ) as response:

                # --------------------------------------------
                # Erros temporários
                # --------------------------------------------

                if response.status_code in STATUS_RETRY:

                    retry_after = obter_retry_after(response)

                    espera = (
                        retry_after
                        if retry_after is not None
                        else calcular_espera(tentativa)
                    )

                    print(
                        f"   ↳ HTTP {response.status_code}. "
                        f"Nova tentativa em {espera:.1f}s."
                    )

                    if tentativa == MAX_TENTATIVAS:
                        response.raise_for_status()

                    time.sleep(espera)
                    continue

                # Outros códigos HTTP de erro
                response.raise_for_status()

                # --------------------------------------------
                # Escrita
                # --------------------------------------------

                with arquivo_temporario.open("wb") as arquivo:

                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):
                        if chunk:
                            arquivo.write(chunk)

            # Download completo:
            arquivo_temporario.replace(destino)

            return

        except requests.RequestException:

            if arquivo_temporario.exists():
                arquivo_temporario.unlink()

            if tentativa == MAX_TENTATIVAS:
                raise

            espera = calcular_espera(tentativa)

            print(
                f"   ↳ Falha de comunicação. "
                f"Nova tentativa em {espera:.1f}s."
            )

            time.sleep(espera)


# ============================================================
# DATASET
# ============================================================

def obter_recursos():

    print(f"Consultando dataset:\n{API_URL}\n")

    response = session.get(
        API_URL,
        timeout=(TIMEOUT_CONEXAO, 30),
    )

    response.raise_for_status()

    dados = response.json()

    return dados.get("resources", [])


# ============================================================
# EXECUÇÃO
# ============================================================

def executar():

    PASTA_RAW.mkdir(parents=True, exist_ok=True)

    try:
        recursos = obter_recursos()

    except requests.RequestException as erro:

        print(f"[ERRO] Não foi possível consultar o dataset: {erro}")
        return

    print(f"Recursos encontrados: {len(recursos)}\n")

    baixados = 0
    existentes = 0
    antigos = 0
    desconhecidos = 0
    erros = 0

    primeiro_download = True

    for item in recursos:

        resource_id = item.get("id")

        nome = (
            item.get("name")
            or item.get("title")
            or resource_id
            or "recurso_sem_nome"
        )

        formato = (item.get("format") or "csv").lower()

        competencia = extrair_competencia(nome)

        # ----------------------------------------------------
        # Data desconhecida
        # ----------------------------------------------------

        if competencia is None:

            desconhecidos += 1

            print(
                f"[ATENÇÃO] Competência não identificada: {nome}"
            )

            registrar_log(
                status="competencia_desconhecida",
                resource_id=resource_id,
                nome=nome,
            )

            # Estratégia conservadora:
            # NÃO descartamos o recurso.
            # Continuamos para download.

        # ----------------------------------------------------
        # Recursos anteriores ao período estudado
        # ----------------------------------------------------

        elif competencia < DATA_INICIAL:

            antigos += 1
            continue

        # ----------------------------------------------------
        # Organização por ano
        # ----------------------------------------------------

        ano = (
            str(competencia.year)
            if competencia
            else "desconhecido"
        )

        pasta_ano = PASTA_RAW / ano
        pasta_ano.mkdir(parents=True, exist_ok=True)

        # ----------------------------------------------------
        # Nome do arquivo
        # ----------------------------------------------------

        nome_limpo = limpar_nome_arquivo(nome)

        extensao = f".{formato}"

        if not nome_limpo.lower().endswith(extensao):
            nome_limpo += extensao

        destino = pasta_ano / nome_limpo

        # ----------------------------------------------------
        # Idempotência
        # ----------------------------------------------------

        if destino.exists():

            existentes += 1

            print(f"[PULADO] {destino}")

            continue

        # ----------------------------------------------------
        # Rate limiting
        # ----------------------------------------------------

        if not primeiro_download:
            time.sleep(INTERVALO_ENTRE_DOWNLOADS)

        primeiro_download = False

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        url = (
            f"{API_URL}/resources/"
            f"{resource_id}/download"
        )

        print(f"[BAIXANDO] {nome}")

        try:

            baixar_arquivo(url, destino)

            sha256 = calcular_sha256(destino)

            tamanho = destino.stat().st_size

            registrar_log(
                status="baixado",
                resource_id=resource_id,
                nome=nome,
                competencia=(
                    competencia.strftime("%Y-%m")
                    if competencia
                    else None
                ),
                formato=formato,
                url=url,
                arquivo=str(destino),
                tamanho_bytes=tamanho,
                sha256=sha256,
            )

            baixados += 1

            print(
                f"   ↳ Concluído "
                f"({tamanho / 1024 / 1024:.2f} MB)"
            )

        except Exception as erro:

            erros += 1

            registrar_log(
                status="erro",
                resource_id=resource_id,
                nome=nome,
                url=url,
                erro=str(erro),
            )

            print(f"   ↳ [ERRO] {erro}")

    # ========================================================
    # RESUMO
    # ========================================================

    print("\n" + "=" * 60)

    print("COLETA FINALIZADA")

    print("=" * 60)

    print(f"Baixados...............: {baixados}")
    print(f"Já existentes..........: {existentes}")
    print(f"Anteriores a 2022......: {antigos}")
    print(f"Competência desconhecida: {desconhecidos}")
    print(f"Erros..................: {erros}")

    print(f"\nDados RAW: {PASTA_RAW.resolve()}")
    print(f"Manifest:  {ARQUIVO_LOG.resolve()}")


if __name__ == "__main__":
    executar()