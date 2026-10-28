import json
import os
import sys
from datetime import date

import psycopg

from .common import REPORT_DIR
from .load_dw import connect


# Verbas extraordinárias: eventuais + judiciais + licença-prêmio.
EXTRAORDINARIAS = (
    "COALESCE(verbas_eventuais, 0) + COALESCE(verbas_judiciais, 0) + COALESCE(licenca_premio, 0)"
)

AGG_ORGAO_SQL = f"""
    INSERT INTO agg_orgao_mes (
        competencia, codigo_orgao, orgao, quantidade_servidores, quantidade_vinculos,
        quantidade_registros, total_bruto, media_bruto, mediana_bruto, p10_bruto, p25_bruto,
        p75_bruto, p90_bruto, desvio_padrao_bruto, coeficiente_variacao, participacao_total,
        total_hora_extra, participacao_hora_extra,
        total_verbas_extraordinarias, participacao_verbas_extraordinarias
    )
    WITH base AS (
        SELECT
            codigo_orgao,
            orgao,
            servidor_id,
            matricula,
            bruto,
            COALESCE(hora_extra, 0) AS hora_extra,
            {EXTRAORDINARIAS} AS extraordinarias
        FROM fato_remuneracao
        WHERE competencia = %(competencia)s
    ),
    total AS (
        SELECT NULLIF(SUM(bruto), 0) AS total_bruto FROM base
    )
    SELECT
        %(competencia)s,
        base.codigo_orgao,
        base.orgao,
        COUNT(DISTINCT base.servidor_id),
        COUNT(DISTINCT base.matricula),
        COUNT(*),
        SUM(base.bruto),
        AVG(base.bruto),
        percentile_cont(0.50) WITHIN GROUP (ORDER BY base.bruto),
        percentile_cont(0.10) WITHIN GROUP (ORDER BY base.bruto),
        percentile_cont(0.25) WITHIN GROUP (ORDER BY base.bruto),
        percentile_cont(0.75) WITHIN GROUP (ORDER BY base.bruto),
        percentile_cont(0.90) WITHIN GROUP (ORDER BY base.bruto),
        STDDEV_SAMP(base.bruto),
        STDDEV_SAMP(base.bruto) / NULLIF(AVG(base.bruto), 0),
        SUM(base.bruto) / total.total_bruto,
        SUM(base.hora_extra),
        SUM(base.hora_extra) / NULLIF(SUM(base.bruto), 0),
        SUM(base.extraordinarias),
        SUM(base.extraordinarias) / NULLIF(SUM(base.bruto), 0)
    FROM base
    CROSS JOIN total
    GROUP BY base.codigo_orgao, base.orgao, total.total_bruto
"""

AGG_CARGO_SQL = """
    INSERT INTO agg_cargo_mes (
        competencia, codigo_orgao, orgao, cargo, quantidade_servidores, quantidade_registros,
        total_bruto, media_bruto, mediana_bruto, p25_bruto, p75_bruto, desvio_padrao_bruto
    )
    SELECT
        %(competencia)s,
        codigo_orgao,
        orgao,
        cargo,
        COUNT(DISTINCT servidor_id),
        COUNT(*),
        SUM(bruto),
        AVG(bruto),
        percentile_cont(0.50) WITHIN GROUP (ORDER BY bruto),
        percentile_cont(0.25) WITHIN GROUP (ORDER BY bruto),
        percentile_cont(0.75) WITHIN GROUP (ORDER BY bruto),
        STDDEV_SAMP(bruto)
    FROM fato_remuneracao
    WHERE competencia = %(competencia)s
    GROUP BY codigo_orgao, orgao, cargo
"""

AGG_SERVIDOR_SQL = f"""
    INSERT INTO agg_servidor_periodo (
        servidor_id, meses_observados, orgaos_distintos, total_bruto, media_mensal,
        mediana_mensal, desvio_padrao_mensal, meses_com_hora_extra, frequencia_hora_extra,
        meses_com_verbas_extraordinarias, frequencia_verbas_extraordinarias
    )
    WITH mensal AS (
        SELECT
            servidor_id,
            competencia,
            SUM(bruto) AS bruto,
            SUM(COALESCE(hora_extra, 0)) AS hora_extra,
            SUM({EXTRAORDINARIAS}) AS extraordinarias
        FROM fato_remuneracao
        GROUP BY servidor_id, competencia
    ),
    orgaos AS (
        SELECT servidor_id, COUNT(DISTINCT codigo_orgao) AS quantidade
        FROM fato_remuneracao
        GROUP BY servidor_id
    )
    SELECT
        mensal.servidor_id,
        COUNT(*),
        orgaos.quantidade,
        SUM(mensal.bruto),
        AVG(mensal.bruto),
        percentile_cont(0.50) WITHIN GROUP (ORDER BY mensal.bruto),
        STDDEV_SAMP(mensal.bruto),
        COUNT(*) FILTER (WHERE mensal.hora_extra <> 0),
        COUNT(*) FILTER (WHERE mensal.hora_extra <> 0)::numeric / COUNT(*),
        COUNT(*) FILTER (WHERE mensal.extraordinarias <> 0),
        COUNT(*) FILTER (WHERE mensal.extraordinarias <> 0)::numeric / COUNT(*)
    FROM mensal
    JOIN orgaos ON orgaos.servidor_id = mensal.servidor_id
    GROUP BY mensal.servidor_id, orgaos.quantidade
"""

ANOMALY_ZSCORE_SQL = """
    INSERT INTO statistical_anomaly (
        competencia, servidor_id, metodo, escopo, valor_bruto, referencia, escore
    )
    WITH mensal AS (
        SELECT servidor_id, competencia, SUM(bruto) AS bruto
        FROM fato_remuneracao
        GROUP BY servidor_id, competencia
    ),
    historico AS (
        SELECT servidor_id, COUNT(*) AS meses, AVG(bruto) AS media, STDDEV_SAMP(bruto) AS desvio
        FROM mensal
        GROUP BY servidor_id
    )
    SELECT
        mensal.competencia,
        mensal.servidor_id,
        'zscore',
        'historico_servidor',
        mensal.bruto,
        historico.media,
        (mensal.bruto - historico.media) / historico.desvio
    FROM mensal
    JOIN historico ON historico.servidor_id = mensal.servidor_id
    WHERE mensal.competencia = %(competencia)s
      AND historico.meses >= %(min_observacoes)s
      AND historico.desvio > 0
      AND ABS((mensal.bruto - historico.media) / historico.desvio) >= %(zscore)s
"""

ANOMALY_IQR_SQL = """
    INSERT INTO statistical_anomaly (
        competencia, servidor_id, metodo, escopo, valor_bruto, referencia, escore
    )
    WITH base AS (
        SELECT servidor_id, codigo_orgao, cargo, SUM(bruto) AS bruto
        FROM fato_remuneracao
        WHERE competencia = %(competencia)s
        GROUP BY servidor_id, codigo_orgao, cargo
    ),
    limites AS (
        SELECT
            codigo_orgao,
            cargo,
            COUNT(*) AS observacoes,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY bruto) AS q1,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY bruto) AS q3
        FROM base
        GROUP BY codigo_orgao, cargo
    )
    SELECT
        %(competencia)s,
        base.servidor_id,
        'iqr',
        'cargo_orgao:' || base.codigo_orgao || ':' || base.cargo,
        base.bruto,
        (limites.q1 + limites.q3) / 2,
        (base.bruto - (limites.q1 + limites.q3) / 2) / NULLIF(limites.q3 - limites.q1, 0)
    FROM base
    JOIN limites ON limites.codigo_orgao = base.codigo_orgao AND limites.cargo = base.cargo
    WHERE limites.observacoes >= %(min_grupo)s
      AND (limites.q3 - limites.q1) > 0
      AND (
            base.bruto < limites.q1 - %(multiplicador)s * (limites.q3 - limites.q1)
         OR base.bruto > limites.q3 + %(multiplicador)s * (limites.q3 - limites.q1)
      )
"""

QUALITY_SQL = """
    INSERT INTO data_quality_summary (
        source_file, competencia, linhas_lidas, linhas_curadas, linhas_quarentena, motivos_quarentena
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (source_file) DO UPDATE SET
        competencia = EXCLUDED.competencia,
        linhas_lidas = EXCLUDED.linhas_lidas,
        linhas_curadas = EXCLUDED.linhas_curadas,
        linhas_quarentena = EXCLUDED.linhas_quarentena,
        motivos_quarentena = EXCLUDED.motivos_quarentena
"""


def anomaly_settings() -> dict:
    return {
        "min_observacoes": int(os.getenv("ANOMALY_MIN_OBSERVACOES", "6")),
        "zscore": float(os.getenv("ANOMALY_ZSCORE", "3.0")),
        "min_grupo": int(os.getenv("ANOMALY_MIN_GRUPO", "20")),
        "multiplicador": float(os.getenv("ANOMALY_IQR_MULTIPLICADOR", "1.5")),
    }


def competencias(connection: psycopg.Connection) -> list[date]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT competencia FROM fato_remuneracao ORDER BY competencia")
        return [row[0] for row in cursor.fetchall()]


def analyze_competence(connection: psycopg.Connection, competencia: date, settings: dict) -> dict:
    parameters = {"competencia": competencia, **settings}
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM agg_orgao_mes WHERE competencia = %s", (competencia,))
            cursor.execute(AGG_ORGAO_SQL, parameters)
            orgaos = cursor.rowcount
            cursor.execute("DELETE FROM agg_cargo_mes WHERE competencia = %s", (competencia,))
            cursor.execute(AGG_CARGO_SQL, parameters)
            cargos = cursor.rowcount
            cursor.execute("DELETE FROM statistical_anomaly WHERE competencia = %s", (competencia,))
            cursor.execute(ANOMALY_ZSCORE_SQL, parameters)
            anomalias = cursor.rowcount
            cursor.execute(ANOMALY_IQR_SQL, parameters)
            anomalias += cursor.rowcount
    return {"orgaos": orgaos, "cargos": cargos, "anomalias": anomalias}


def rebuild_servidor_periodo(connection: psycopg.Connection) -> int:
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM agg_servidor_periodo")
            cursor.execute(AGG_SERVIDOR_SQL)
            return cursor.rowcount


def load_quality_reports(connection: psycopg.Connection) -> int:
    reports = sorted(REPORT_DIR.glob("*_quality.json")) if REPORT_DIR.is_dir() else []
    with connection.transaction():
        with connection.cursor() as cursor:
            for path in reports:
                report = json.loads(path.read_text(encoding="utf-8"))
                year, month = report["competencia"].split("-")
                cursor.execute(
                    QUALITY_SQL,
                    (
                        report["source_file"],
                        date(int(year), int(month), 1),
                        report["linhas_lidas"],
                        report["linhas_curadas"],
                        report["linhas_quarentena"],
                        json.dumps(report.get("motivos_quarentena", {})),
                    ),
                )
    return len(reports)


def main() -> None:
    settings = anomaly_settings()
    with connect() as connection:
        meses = competencias(connection)
        if not meses:
            raise RuntimeError("nenhuma competência carregada em fato_remuneracao; execute o loader antes")

        for competencia in meses:
            resultado = analyze_competence(connection, competencia, settings)
            print(
                f"[analyzed] {competencia:%Y-%m}: {resultado['orgaos']} órgão(s), "
                f"{resultado['cargos']} cargo(s), {resultado['anomalias']} atipicidade(s)"
            )

        servidores = rebuild_servidor_periodo(connection)
        print(f"[analyzed] período por servidor: {servidores} servidor(es)")
        relatorios = load_quality_reports(connection)
        print(f"[analyzed] qualidade: {relatorios} relatório(s)")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"[falha] {error}", file=sys.stderr)
        raise SystemExit(1) from None