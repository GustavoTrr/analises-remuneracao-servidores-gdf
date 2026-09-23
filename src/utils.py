import hashlib
import re
from datetime import datetime
from pathlib import Path


MESES_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def extrair_competencia(nome: str) -> datetime | None:
    """
    Tenta identificar mês e ano no nome do recurso.

    Formatos reconhecidos:
        01/2025
        01-2025
        01_2025
        2025/01
        2025-01
        2025_01
        Janeiro/2025
        Janeiro de 2025
        Janeiro 2025

    Retorna:
        datetime correspondente ao primeiro dia da competência,
        ou None quando mês/ano não puderem ser determinados.

    Observação:
        Não inferimos janeiro quando apenas o ano é encontrado,
        pois isso criaria uma competência que não está explícita
        na fonte.
    """

    if not nome:
        return None

    nome_lower = nome.lower()

    # MM/YYYY, MM-YYYY ou MM_YYYY
    match = re.search(r"\b(0[1-9]|1[0-2])[-_/](20\d{2})\b", nome_lower)

    if match:
        mes = int(match.group(1))
        ano = int(match.group(2))
        return datetime(ano, mes, 1)

    # YYYY/MM, YYYY-MM ou YYYY_MM
    match = re.search(r"\b(20\d{2})[-_/](0[1-9]|1[0-2])\b", nome_lower)

    if match:
        ano = int(match.group(1))
        mes = int(match.group(2))
        return datetime(ano, mes, 1)

    # Janeiro/2024, Janeiro de 2024, Janeiro 2024 etc.
    for nome_mes, numero_mes in MESES_PT.items():

        if nome_mes not in nome_lower:
            continue

        match_ano = re.search(r"\b(20\d{2})\b", nome_lower)

        if match_ano:
            ano = int(match_ano.group(1))
            return datetime(ano, numero_mes, 1)

    return None


def limpar_nome_arquivo(nome: str) -> str:
    """
    Substitui caracteres inválidos ou problemáticos em nomes
    de arquivos por underscore.
    """

    nome = re.sub(r'[\\/*?:"<>|]', "_", nome)
    return nome.strip()


def calcular_sha256(caminho: Path) -> str:
    """
    Calcula o SHA-256 de um arquivo.

    O arquivo é processado em blocos para evitar seu
    carregamento completo em memória.
    """

    sha256 = hashlib.sha256()

    with caminho.open("rb") as arquivo:

        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            sha256.update(bloco)

    return sha256.hexdigest()