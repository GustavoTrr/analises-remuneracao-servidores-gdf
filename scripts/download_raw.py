import csv
import errno
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from .common import (
    RAW_DIR,
    competencia_inicial,
    competencia_permitida,
    competence_from_name,
    csv_delimiter,
    csv_encoding,
    normalize_column,
)


def monthly_csv_resources(response: dict) -> list[dict]:
    resources = []
    for resource in response.get("resourceDetails", []):
        if resource.get("format", "").upper() != "CSV":
            continue
        if not resource.get("downloadUrl") or not re.search(r"(?:19|20)\d{2}[-_]\d{2}", resource.get("name", "")):
            continue
        resources.append(resource)
    return resources


def validate_csv(path: Path) -> None:
    if path.stat().st_size == 0:
        raise ValueError("download vazio")
    with path.open("rb") as source:
        signature = source.read(4)
    if signature in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        raise ValueError("o servidor retornou um arquivo ZIP, não um CSV")
    with path.open(encoding=csv_encoding(path), newline="") as source:
        header = next(csv.reader(source, delimiter=csv_delimiter(path)), [])
    normalized = {normalize_column(column) for column in header}
    if len(header) < 2 or not {"nome", "cpf", "mes", "ano"}.issubset(normalized):
        raise ValueError("arquivo baixado não parece ser o CSV mensal esperado")


def download(url: str, partial_path: Path, timeout: int, max_retries: int) -> None:
    retryable_statuses = {404, 408, 425, 429, 500, 502, 503, 504}
    for attempt in range(max_retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": "transparencia-df-pipeline/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                with partial_path.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            return
        except urllib.error.HTTPError as error:
            if error.code not in retryable_statuses or attempt == max_retries:
                raise
            error.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == max_retries:
                raise

        delay = 2**attempt
        print(f"[retry] tentativa {attempt + 2}/{max_retries + 1} em {delay}s")
        time.sleep(delay)


def fetch_dataset_metadata(api_url: str, timeout: int, max_retries: int) -> dict:
    retryable_statuses = {408, 425, 429, 500, 502, 503, 504}
    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            api_url,
            headers={"Accept": "application/json", "User-Agent": "transparencia-df-pipeline/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in retryable_statuses or attempt == max_retries:
                raise
            error.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == max_retries:
                raise

        delay = 2**attempt
        print(f"[retry] consulta do catálogo, tentativa {attempt + 2}/{max_retries + 1} em {delay}s")
        time.sleep(delay)
    raise RuntimeError("não foi possível consultar o catálogo do Portal")


def main() -> None:
    api_url = os.getenv(
        "DATASET_API_URL",
        "https://dados.df.gov.br/o/dados-abertos/v1.0/datasets/"
        "portal-da-transparencia-remuneracao-dos-servidores",
    )
    base_url = os.getenv("PORTAL_BASE_URL", "https://dados.df.gov.br").rstrip("/") + "/"
    timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))
    max_retries = int(os.getenv("HTTP_MAX_RETRIES", "3"))
    response = fetch_dataset_metadata(api_url, timeout, max_retries)
    resources = monthly_csv_resources(response)
    if not resources:
        raise RuntimeError(f"nenhum recurso mensal CSV encontrado em {api_url}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    inicio = competencia_inicial()
    downloaded = 0
    failures = []
    for resource in resources:
        year, month = competence_from_name(resource["name"])
        filename = f"remuneracao_{year:04d}-{month:02d}.csv"
        if not competencia_permitida(year, month, inicio):
            continue
        final_path = RAW_DIR / filename
        if final_path.is_file() and final_path.stat().st_size > 0:
            print(f"[skip] {filename} já existe")
            continue

        partial_path = final_path.with_name(final_path.name + ".part")
        url = urljoin(base_url, resource["downloadUrl"])
        print(f"[download] {filename}")
        try:
            download(url, partial_path, timeout, max_retries)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            error.close()
            partial_path.unlink(missing_ok=True)
            failures.append(f"{filename} (HTTP 404)")
            print(f"[unavailable] {filename}: HTTP 404; continuará na próxima execução")
            continue
        except OSError as error:
            if error.errno in (errno.ENOSPC, errno.EIO):
                free_gib = shutil.disk_usage(RAW_DIR).free / 1024**3
                raise RuntimeError(
                    f"falha de armazenamento ao gravar {filename} em {RAW_DIR} "
                    f"(espaço livre: {free_gib:.2f} GiB). Libere espaço no disco "
                    "ou no Docker Desktop e execute o coletor novamente."
                ) from error
            raise
        try:
            validate_csv(partial_path)
        except (ValueError, UnicodeDecodeError, csv.Error) as error:
            partial_path.unlink(missing_ok=True)
            failures.append(f"{filename} (arquivo inválido)")
            print(f"[error] {filename}: {error}; arquivo rejeitado, continuará com o próximo")
            continue
        partial_path.replace(final_path)
        downloaded += 1

    print(f"Concluído: {downloaded} arquivo(s) novo(s), {len(resources)} recurso(s) mensal(is).")
    if failures:
        raise RuntimeError("recursos não baixados ou rejeitados: " + ", ".join(failures))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"[falha] {error}", file=sys.stderr)
        raise SystemExit(1) from None