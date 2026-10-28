import csv
import errno
import json
import os
import tempfile
import unittest
from io import BytesIO, StringIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import patch

from scripts.common import (
    MONEY_COLUMNS,
    SOURCE_COLUMNS,
    competence_from_name,
    competencia_inicial,
    competencia_permitida,
    csv_delimiter,
    csv_encoding,
    identity_secret,
    normalize_column,
    parse_money,
    servidor_key,
)
from scripts.curate import curate_file
from scripts import download_raw


class PipelineUnitTests(unittest.TestCase):
    def test_normalizes_source_header_aliases(self):
        self.assertEqual(normalize_column("SEG. SOCIAL"), "seguridade_social")
        self.assertEqual(normalize_column("PAGAMENTOS A MAIOR"), "pagamento_a_maior")
        self.assertEqual(normalize_column("CÓDIGO DO ÓRGÃO"), "codigo_orgao")

    def test_parses_brazilian_currency_and_preserves_negative_amounts(self):
        self.assertEqual(parse_money(",00"), "0.00")
        self.assertEqual(parse_money("1.234,56"), "1234.56")
        self.assertEqual(parse_money("-1047,66"), "-1047.66")
        with self.assertRaises(ValueError):
            parse_money("não numérico")

    def test_detects_windows_1252_csv_from_header(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "portal.csv"
            path.write_bytes("NOME,CPF,ÓRGÃO\n".encode("cp1252"))
            self.assertEqual(csv_encoding(path), "cp1252")

    def test_detects_comma_and_semicolon_delimiters(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            comma_path = Path(temporary_directory) / "comma.csv"
            semicolon_path = Path(temporary_directory) / "semicolon.csv"
            comma_path.write_text("NOME,CPF,ÓRGÃO\n", encoding="utf-8")
            semicolon_path.write_bytes("NOME;CPF;ÓRGÃO\n".encode("cp1252"))
            self.assertEqual(csv_delimiter(comma_path), ",")
            self.assertEqual(csv_delimiter(semicolon_path), ";")

    def test_extracts_month_and_year_from_filename(self):
        self.assertEqual(competence_from_name("remuneracao_2023-02.csv"), (2023, 2))
        with self.assertRaises(ValueError):
            competence_from_name("arquivo.csv")

    def test_servidor_key_is_stable_and_depends_on_secret(self):
        normalized = servidor_key("JOAO DA SILVA", "***123456**", b"segredo")
        self.assertEqual(servidor_key("  jo\u00e3o   da silva ", "***123456** ", b"segredo"), normalized)
        self.assertNotEqual(servidor_key("JOAO DA SILVA", "***123456**", b"outro"), normalized)
        self.assertNotEqual(servidor_key("JOAO DA SILVA", "***999999**", b"segredo"), normalized)
        self.assertEqual(len(normalized), 64)

    def test_identity_secret_requires_configuration(self):
        with patch.dict(os.environ, {"IDENTITY_HMAC_KEY": "  "}):
            with self.assertRaisesRegex(RuntimeError, "IDENTITY_HMAC_KEY"):
                identity_secret()
        with patch.dict(os.environ, {"IDENTITY_HMAC_KEY": "abc"}):
            self.assertEqual(identity_secret(), b"abc")

    def test_competencia_inicial_accepts_valid_value_and_ignores_the_rest(self):
        with patch.dict(os.environ, {"COMPETENCIA_INICIAL": "2024-03"}):
            self.assertEqual(competencia_inicial(), (2024, 3))
        with patch.dict(os.environ, {"COMPETENCIA_INICIAL": ""}):
            self.assertIsNone(competencia_inicial())
        for invalido in ("2024-13", "03/2024", "abril", "2024"):
            with patch.dict(os.environ, {"COMPETENCIA_INICIAL": invalido}):
                with patch("sys.stderr", new=StringIO()) as aviso:
                    self.assertIsNone(competencia_inicial())
                self.assertIn("COMPETENCIA_INICIAL", aviso.getvalue())

    def test_competencia_permitida_filters_earlier_months(self):
        inicio = (2024, 3)
        self.assertFalse(competencia_permitida(2024, 2, inicio))
        self.assertTrue(competencia_permitida(2024, 3, inicio))
        self.assertTrue(competencia_permitida(2025, 1, inicio))
        self.assertFalse(competencia_permitida(2023, 12, inicio))
        self.assertTrue(competencia_permitida(2020, 1, None))

    def test_collector_skips_competences_before_configured_start(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            metadata = {
                "resourceDetails": [
                    {
                        "name": f"2023-{month:02d} - Remuneração",
                        "format": "CSV",
                        "downloadUrl": f"/resource/{month}",
                    }
                    for month in (1, 2, 3)
                ]
            }
            raw_directory = Path(temporary_directory) / "raw"
            payload = (",".join(SOURCE_COLUMNS) + "\n").encode("utf-8")

            def write_download(_url, partial_path, _timeout, _max_retries):
                partial_path.write_bytes(payload)

            with (
                patch.object(download_raw, "RAW_DIR", raw_directory),
                patch.dict(os.environ, {"DATASET_API_URL": "https://portal.test/dataset", "COMPETENCIA_INICIAL": "2023-02"}),
                patch.object(download_raw, "fetch_dataset_metadata", return_value=metadata),
                patch.object(download_raw, "download", side_effect=write_download) as mocked_download,
            ):
                download_raw.main()

            self.assertEqual(
                sorted(path.name for path in raw_directory.glob("*.csv")),
                ["remuneracao_2023-02.csv", "remuneracao_2023-03.csv"],
            )
            self.assertEqual(mocked_download.call_count, 2)

    def test_collector_selects_monthly_csv_and_skips_completed_downloads(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            metadata = {
                "resourceDetails": [
                    {
                        "name": f"2023-{month:02d} - Remuneração",
                        "format": "CSV",
                        "downloadUrl": f"/resource/{month}",
                    }
                    for month in (2, 3)
                ]
                + [{"name": "Dicionário", "format": "HTML", "downloadUrl": "/dictionary"}]
            }
            raw_directory = root / "raw"
            payload = (",".join(SOURCE_COLUMNS) + "\n").encode("utf-8")

            def write_download(_url, partial_path, _timeout, _max_retries):
                partial_path.write_bytes(payload)

            with (
                patch.object(download_raw, "RAW_DIR", raw_directory),
                patch.dict(os.environ, {"DATASET_API_URL": "https://portal.test/dataset"}),
                patch.object(download_raw, "fetch_dataset_metadata", return_value=metadata) as metadata_request,
                patch.object(download_raw, "download", side_effect=write_download) as mocked_download,
            ):
                download_raw.main()
                download_raw.main()

            self.assertEqual(metadata_request.call_count, 2)
            metadata_request.assert_called_with("https://portal.test/dataset", 60, 3)
            completed_files = sorted(path.name for path in raw_directory.glob("*.csv"))
            partial_files = list(raw_directory.glob("*.part"))
            self.assertEqual(completed_files, ["remuneracao_2023-02.csv", "remuneracao_2023-03.csv"])
            self.assertEqual(partial_files, [])
            self.assertEqual(mocked_download.call_count, 2)

    def test_collector_continues_after_persistent_404_and_reports_missing_resource(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            metadata = {
                "resourceDetails": [
                    {
                        "name": f"2023-{month:02d} - Remuneração",
                        "format": "CSV",
                        "downloadUrl": f"/resource/{month}",
                    }
                    for month in (2, 3)
                ]
            }
            raw_directory = root / "raw"
            payload = (",".join(SOURCE_COLUMNS) + "\n").encode("utf-8")

            def download_with_missing_month(url, partial_path, _timeout, _max_retries):
                if url.endswith("/2"):
                    raise HTTPError(url, 404, "Not Found", None, None)
                partial_path.write_bytes(payload)

            with (
                patch.object(download_raw, "RAW_DIR", raw_directory),
                patch.dict(os.environ, {"DATASET_API_URL": "https://portal.test/dataset"}),
                patch.object(download_raw, "fetch_dataset_metadata", return_value=metadata),
                patch.object(download_raw, "download", side_effect=download_with_missing_month),
            ):
                with self.assertRaisesRegex(RuntimeError, "remuneracao_2023-02.csv"):
                    download_raw.main()

            self.assertTrue((raw_directory / "remuneracao_2023-03.csv").is_file())
            self.assertFalse((raw_directory / "remuneracao_2023-02.csv").exists())

    def test_collector_rejects_zip_payload_and_continues(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            metadata = {
                "resourceDetails": [
                    {
                        "name": f"2023-{month:02d} - Remuneração",
                        "format": "CSV",
                        "downloadUrl": f"/resource/{month}",
                    }
                    for month in (2, 3)
                ]
            }
            raw_directory = root / "raw"
            payload = (",".join(SOURCE_COLUMNS) + "\n").encode("utf-8")

            def download_with_zip(url, partial_path, _timeout, _max_retries):
                partial_path.write_bytes(b"PK\x03\x04unexpected archive")
                if url.endswith("/3"):
                    partial_path.write_bytes(payload)

            with (
                patch.object(download_raw, "RAW_DIR", raw_directory),
                patch.dict(os.environ, {"DATASET_API_URL": "https://portal.test/dataset"}),
                patch.object(download_raw, "fetch_dataset_metadata", return_value=metadata),
                patch.object(download_raw, "download", side_effect=download_with_zip),
            ):
                with self.assertRaisesRegex(RuntimeError, r"remuneracao_2023-02.csv \(arquivo inválido\)"):
                    download_raw.main()

            self.assertFalse((raw_directory / "remuneracao_2023-02.csv.part").exists())
            self.assertFalse((raw_directory / "remuneracao_2023-02.csv").exists())
            self.assertTrue((raw_directory / "remuneracao_2023-03.csv").is_file())

    def test_fetches_dataset_metadata_as_json(self):
        payload = json.dumps({"resourceDetails": []}).encode("utf-8")
        response = BytesIO(payload)
        url = "https://portal.test/dataset"
        with patch.object(download_raw.urllib.request, "urlopen", return_value=response) as open_url:
            metadata = download_raw.fetch_dataset_metadata(url, timeout=5, max_retries=0)

        request = open_url.call_args.args[0]
        self.assertEqual(metadata, {"resourceDetails": []})
        self.assertEqual(request.get_header("Accept"), "application/json")

    def test_collector_reports_storage_error_with_free_space(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            metadata = {
                "resourceDetails": [
                    {
                        "name": "2023-02 - Remuneração",
                        "format": "CSV",
                        "downloadUrl": "/resource/2",
                    }
                ]
            }
            with (
                patch.object(download_raw, "RAW_DIR", Path(temporary_directory) / "raw"),
                patch.dict(os.environ, {"DATASET_API_URL": "https://portal.test/dataset"}),
                patch.object(download_raw, "fetch_dataset_metadata", return_value=metadata),
                patch.object(download_raw, "download", side_effect=OSError(errno.EIO, "Input/output error")),
            ):
                with self.assertRaisesRegex(RuntimeError, "falha de armazenamento.*espaço livre"):
                    download_raw.main()

    def test_download_retries_transient_404(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            url = "https://example.test/resource.csv"
            partial_path = Path(temporary_directory) / "resource.csv.part"
            payload = b"downloaded"
            response = tempfile.TemporaryFile()
            response.write(payload)
            response.seek(0)
            with (
                patch.object(
                    download_raw.urllib.request,
                    "urlopen",
                    side_effect=[HTTPError(url, 404, "Not Found", None, None), response],
                ) as open_url,
                patch.object(download_raw.time, "sleep") as sleep,
            ):
                download_raw.download(url, partial_path, timeout=1, max_retries=2)

            self.assertEqual(partial_path.read_bytes(), payload)
            self.assertEqual(open_url.call_count, 2)
            sleep.assert_called_once_with(1)

    def test_curates_valid_rows_and_quarantines_invalid_money(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw_directory = root / "raw"
            raw_directory.mkdir()
            raw_path = raw_directory / "remuneracao_2023-02.csv"
            valid_row = {column: "" for column in SOURCE_COLUMNS}
            valid_row.update({"nome": "SERVIDOR TESTE", "mes": "2", "ano": "2023", "bruto": "1.234,56"})
            invalid_row = dict(valid_row, bruto="inválido")
            with raw_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=SOURCE_COLUMNS)
                writer.writeheader()
                writer.writerow(valid_row)
                writer.writerow(invalid_row)

            import scripts.curate as curator

            curator.CURATED_DIR = root / "curated"
            curator.QUARANTINE_DIR = root / "quarantine"
            curator.REPORT_DIR = root / "reports"
            result = curate_file(raw_path)

            with (root / "curated" / raw_path.name).open(encoding="utf-8", newline="") as source:
                curated_rows = list(csv.DictReader(source))
            with (root / "quarantine" / "remuneracao_2023-02_quarantine.csv").open(
                encoding="utf-8", newline=""
            ) as source:
                quarantined_rows = list(csv.DictReader(source))

            self.assertEqual(result["linhas_curadas"], 1)
            self.assertEqual(result["linhas_quarentena"], 1)
            self.assertEqual(curated_rows[0]["bruto"], "1234.56")
            self.assertEqual(quarantined_rows[0]["reason"], "invalid_value")
            self.assertEqual(len(MONEY_COLUMNS), 17)

    def test_curator_does_not_create_quarantine_file_without_rejections(self):
        import scripts.curate as curator

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw_directory = root / "raw"
            raw_directory.mkdir()
            raw_path = raw_directory / "remuneracao_2023-02.csv"
            row = {column: "" for column in SOURCE_COLUMNS}
            row.update({"mes": "2", "ano": "2023", "bruto": "10,00"})
            with raw_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=SOURCE_COLUMNS)
                writer.writeheader()
                writer.writerow(row)

            with (
                patch.object(curator, "CURATED_DIR", root / "curated"),
                patch.object(curator, "QUARANTINE_DIR", root / "quarantine"),
                patch.object(curator, "REPORT_DIR", root / "reports"),
            ):
                result = curate_file(raw_path)

            self.assertEqual(result["linhas_quarentena"], 0)
            self.assertEqual(list((root / "quarantine").iterdir()), [])
            self.assertTrue((root / "curated" / raw_path.name).is_file())

    def test_curator_reports_storage_error_with_free_space(self):
        import scripts.curate as curator

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw_directory = root / "raw"
            raw_directory.mkdir()
            (raw_directory / "remuneracao_2023-02.csv").touch()
            with (
                patch.object(curator, "CURATED_DIR", root / "curated"),
                patch.object(curator, "curate_file", side_effect=OSError(errno.EIO, "Input/output error")),
                patch.object(curator.shutil, "disk_usage", return_value=SimpleNamespace(free=2 * 1024**3)),
            ):
                with self.assertRaisesRegex(RuntimeError, "falha de armazenamento.*espaço livre: 2.00 GiB"):
                    curator.main()

    def test_curator_skips_completed_files_when_resuming(self):
        import scripts.curate as curator

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw_directory = root / "raw"
            curated_directory = root / "curated"
            raw_directory.mkdir()
            curated_directory.mkdir()
            (raw_directory / "remuneracao_2023-02.csv").touch()
            (curated_directory / "remuneracao_2023-02.csv").write_text("already curated", encoding="utf-8")
            with (
                patch.object(curator, "CURATED_DIR", curated_directory),
                patch.object(curator, "curate_file") as curate_mock,
            ):
                curator.main()

            curate_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()