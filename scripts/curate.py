import csv
import errno
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

from .common import (
    CURATED_DIR,
    MONEY_COLUMNS,
    QUARANTINE_DIR,
    REPORT_DIR,
    SOURCE_COLUMNS,
    competencia_inicial,
    competencia_permitida,
    competence_from_name,
    csv_delimiter,
    csv_encoding,
    normalize_column,
    parse_money,
)


def curate_file(raw_path: Path) -> dict:
    year, month = competence_from_name(raw_path.name)
    output_path = CURATED_DIR / raw_path.name
    quarantine_path = QUARANTINE_DIR / f"{raw_path.stem}_quarantine.csv"
    report_path = REPORT_DIR / f"{raw_path.stem}_quality.json"
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    temporary_output = output_path.with_name(output_path.name + ".tmp")
    temporary_quarantine = quarantine_path.with_name(quarantine_path.name + ".tmp")
    temporary_report = report_path.with_name(report_path.name + ".tmp")
    reasons: Counter[str] = Counter()
    read_count = curated_count = quarantine_count = 0

    try:
        with raw_path.open(encoding=csv_encoding(raw_path), newline="") as source:
            reader = csv.DictReader(source, delimiter=csv_delimiter(raw_path))
            if not reader.fieldnames:
                raise ValueError(f"CSV sem cabeçalho: {raw_path}")
            normalized_headers = [normalize_column(header) for header in reader.fieldnames]
            if len(set(normalized_headers)) != len(normalized_headers):
                raise ValueError(f"cabeçalhos duplicados após normalização: {raw_path}")
            if set(normalized_headers) != set(SOURCE_COLUMNS):
                missing = sorted(set(SOURCE_COLUMNS) - set(normalized_headers))
                unknown = sorted(set(normalized_headers) - set(SOURCE_COLUMNS))
                raise ValueError(f"schema inesperado em {raw_path.name}; ausentes={missing}, desconhecidos={unknown}")
            original_by_normalized = dict(zip(normalized_headers, reader.fieldnames, strict=True))

            with temporary_output.open("w", encoding="utf-8", newline="") as curated_file:
                writer = csv.DictWriter(curated_file, fieldnames=SOURCE_COLUMNS)
                writer.writeheader()
                with temporary_quarantine.open("w", encoding="utf-8", newline="") as quarantine_file:
                    quarantine_writer = csv.DictWriter(
                        quarantine_file,
                        fieldnames=("line_number", "reason", "raw_row"),
                    )
                    quarantine_writer.writeheader()

                    for row in reader:
                        read_count += 1
                        line_number = reader.line_num
                        if None in row or any(row.get(original_by_normalized[column]) is None for column in SOURCE_COLUMNS):
                            reason = "column_count_mismatch"
                            quarantine_writer.writerow(
                                {"line_number": line_number, "reason": reason, "raw_row": json.dumps(row, ensure_ascii=True)}
                            )
                            reasons[reason] += 1
                            quarantine_count += 1
                            continue

                        cleaned = {}
                        try:
                            for column in SOURCE_COLUMNS:
                                value = row[original_by_normalized[column]].strip()
                                if column in MONEY_COLUMNS:
                                    value = parse_money(value)
                                elif column in ("mes", "ano") and value:
                                    value = str(int(value))
                                cleaned[column] = value
                        except ValueError:
                            reason = "invalid_value"
                            quarantine_writer.writerow(
                                {"line_number": line_number, "reason": reason, "raw_row": json.dumps(row, ensure_ascii=True)}
                            )
                            reasons[reason] += 1
                            quarantine_count += 1
                            continue

                        writer.writerow(cleaned)
                        curated_count += 1

        temporary_report.write_text(
            json.dumps(
                {
                    "source_file": raw_path.name,
                    "competencia": f"{year:04d}-{month:02d}",
                    "linhas_lidas": read_count,
                    "linhas_curadas": curated_count,
                    "linhas_quarentena": quarantine_count,
                    "motivos_quarentena": dict(reasons),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_output.replace(output_path)
        if quarantine_count:
            temporary_quarantine.replace(quarantine_path)
        else:
            quarantine_path.unlink(missing_ok=True)
        temporary_report.replace(report_path)
    finally:
        for temporary_path in (temporary_output, temporary_quarantine, temporary_report):
            temporary_path.unlink(missing_ok=True)

    return {
        "source_file": raw_path.name,
        "linhas_lidas": read_count,
        "linhas_curadas": curated_count,
        "linhas_quarentena": quarantine_count,
    }


def main() -> None:
    raw_files = sorted(path for path in CURATED_DIR.parent.joinpath("raw").glob("remuneracao_*.csv") if path.is_file())
    if not raw_files:
        raise RuntimeError(f"nenhum CSV RAW encontrado em {CURATED_DIR.parent / 'raw'}")
    inicio = competencia_inicial()
    for raw_path in raw_files:
        year, month = competence_from_name(raw_path.name)
        if not competencia_permitida(year, month, inicio):
            continue
        output_path = CURATED_DIR / raw_path.name
        if output_path.is_file() and output_path.stat().st_size > 0:
            print(f"[skip] {raw_path.name} já foi curado")
            continue
        try:
            result = curate_file(raw_path)
        except OSError as error:
            if error.errno in (errno.ENOSPC, errno.EIO):
                free_gib = shutil.disk_usage(CURATED_DIR.parent).free / 1024**3
                raise RuntimeError(
                    f"falha de armazenamento ao curar {raw_path.name} "
                    f"(espaço livre: {free_gib:.2f} GiB). Libere espaço no disco "
                    "ou no Docker Desktop e execute o curador novamente."
                ) from error
            raise
        print(
            f"[curated] {result['source_file']}: {result['linhas_curadas']} válida(s), "
            f"{result['linhas_quarentena']} em quarentena"
        )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"[falha] {error}", file=sys.stderr)
        raise SystemExit(1) from None