-- Dados identificáveis ficam isolados nesta tabela; a fato referencia apenas o id.
CREATE TABLE IF NOT EXISTS dim_servidor (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    servidor_key text NOT NULL UNIQUE,
    nome text NOT NULL,
    cpf text NOT NULL
);

CREATE TABLE IF NOT EXISTS fato_remuneracao (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    competencia date NOT NULL,
    servidor_id bigint NOT NULL REFERENCES dim_servidor (id),
    source_file text NOT NULL,
    orgao text NOT NULL DEFAULT '',
    cargo text NOT NULL DEFAULT '',
    funcao text NOT NULL DEFAULT '',
    situacao text NOT NULL DEFAULT '',
    mes smallint,
    ano smallint,
    codigo_orgao text NOT NULL DEFAULT '',
    matricula text NOT NULL DEFAULT '',
    remuneracao_basica numeric(18, 2),
    beneficios numeric(18, 2),
    valor_funcao numeric(18, 2),
    comissao_conselheiro numeric(18, 2),
    hora_extra numeric(18, 2),
    verbas_eventuais numeric(18, 2),
    verbas_judiciais numeric(18, 2),
    descontos_a_maior numeric(18, 2),
    licenca_premio numeric(18, 2),
    irrf numeric(18, 2),
    seguridade_social numeric(18, 2),
    teto_redutor numeric(18, 2),
    outros_recebimentos numeric(18, 2),
    outros_descontos_obrigatorios numeric(18, 2),
    pagamento_a_maior numeric(18, 2),
    bruto numeric(18, 2),
    liquido numeric(18, 2)
);

CREATE INDEX IF NOT EXISTS ix_fato_competencia_orgao
    ON fato_remuneracao (competencia, codigo_orgao);

CREATE INDEX IF NOT EXISTS ix_fato_servidor
    ON fato_remuneracao (servidor_id, competencia);

CREATE INDEX IF NOT EXISTS ix_fato_cargo
    ON fato_remuneracao (competencia, codigo_orgao, cargo);

CREATE TABLE IF NOT EXISTS agg_orgao_mes (
    competencia date NOT NULL,
    codigo_orgao text NOT NULL,
    orgao text NOT NULL,
    quantidade_servidores bigint NOT NULL,
    quantidade_vinculos bigint NOT NULL,
    quantidade_registros bigint NOT NULL,
    total_bruto numeric(20, 2),
    media_bruto numeric(20, 2),
    mediana_bruto numeric(20, 2),
    p10_bruto numeric(20, 2),
    p25_bruto numeric(20, 2),
    p75_bruto numeric(20, 2),
    p90_bruto numeric(20, 2),
    desvio_padrao_bruto numeric(20, 2),
    coeficiente_variacao numeric(12, 4),
    participacao_total numeric(12, 6),
    total_hora_extra numeric(20, 2),
    participacao_hora_extra numeric(12, 6),
    total_verbas_extraordinarias numeric(20, 2),
    participacao_verbas_extraordinarias numeric(12, 6),
    PRIMARY KEY (competencia, codigo_orgao, orgao)
);

CREATE TABLE IF NOT EXISTS agg_cargo_mes (
    competencia date NOT NULL,
    codigo_orgao text NOT NULL,
    orgao text NOT NULL,
    cargo text NOT NULL,
    quantidade_servidores bigint NOT NULL,
    quantidade_registros bigint NOT NULL,
    total_bruto numeric(20, 2),
    media_bruto numeric(20, 2),
    mediana_bruto numeric(20, 2),
    p25_bruto numeric(20, 2),
    p75_bruto numeric(20, 2),
    desvio_padrao_bruto numeric(20, 2),
    PRIMARY KEY (competencia, codigo_orgao, orgao, cargo)
);

CREATE TABLE IF NOT EXISTS agg_servidor_periodo (
    servidor_id bigint PRIMARY KEY REFERENCES dim_servidor (id),
    meses_observados bigint NOT NULL,
    orgaos_distintos bigint NOT NULL,
    total_bruto numeric(20, 2),
    media_mensal numeric(20, 2),
    mediana_mensal numeric(20, 2),
    desvio_padrao_mensal numeric(20, 2),
    meses_com_hora_extra bigint NOT NULL,
    frequencia_hora_extra numeric(12, 6),
    meses_com_verbas_extraordinarias bigint NOT NULL,
    frequencia_verbas_extraordinarias numeric(12, 6)
);

-- classificacao indica desvio estatístico, nunca irregularidade administrativa.
CREATE TABLE IF NOT EXISTS statistical_anomaly (
    competencia date NOT NULL,
    servidor_id bigint NOT NULL REFERENCES dim_servidor (id),
    metodo text NOT NULL,
    escopo text NOT NULL,
    valor_bruto numeric(20, 2),
    referencia numeric(20, 2),
    escore numeric(14, 4),
    classificacao text NOT NULL DEFAULT 'estatisticamente_atipico',
    PRIMARY KEY (competencia, servidor_id, metodo, escopo)
);

CREATE TABLE IF NOT EXISTS data_quality_summary (
    source_file text PRIMARY KEY,
    competencia date NOT NULL,
    linhas_lidas bigint NOT NULL,
    linhas_curadas bigint NOT NULL,
    linhas_quarentena bigint NOT NULL,
    motivos_quarentena jsonb NOT NULL
);
