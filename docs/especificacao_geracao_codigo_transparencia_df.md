# Especificação para geração do código — Transparência DF

## 1. Objetivo

Gere um projeto completo e executável para um pipeline de Business Analytics sobre dados públicos de remuneração do Distrito Federal.

O projeto deve priorizar:

- segurança;
- integridade e rastreabilidade dos dados;
- idempotência e capacidade de reprocessamento;
- resiliência a falhas;
- legibilidade do código;
- baixo acoplamento entre etapas;
- simplicidade operacional.

**Não criar microserviços complexos.** Cada etapa deve ser um pequeno job Python independente, executável isoladamente e em container Docker.

O fluxo principal será:

```text
Portal DF
   ↓
Collector
   ↓
RAW CSV imutável
   ↓
Curator / Data Quality
   ├── Quarantine
   ↓
Curated Parquet
   ↓
Analytics
   ↓
DW Loader
   ↓
PostgreSQL / Data Warehouse
   ↓
Publisher
   ↓
Dados agregados para relatórios/dashboard
```

Para uma mesma competência, as etapas são sequenciais. Competências diferentes podem ser processadas independentemente.

## 2. Stack

Use preferencialmente:

- Python 3.12;
- Polars para leitura, limpeza e transformação de CSV;
- PyArrow/Parquet;
- DuckDB para consultas e cálculos analíticos sobre Parquet;
- PostgreSQL 16 para o Data Warehouse e controle do pipeline;
- SQLAlchemy 2 + Psycopg 3;
- Alembic para migrations;
- Pydantic Settings para configuração;
- httpx para downloads HTTP;
- pytest para testes;
- Ruff para lint/format;
- Docker e Docker Compose.

Não adicionar Airflow, Kafka, Celery, Kubernetes, Spark ou outra infraestrutura distribuída.

## 3. Estrutura esperada do repositório

Crie todos os arquivos necessários para o projeto funcionar, incluindo Dockerfiles, Compose, migrations, scripts, testes e documentação.

Estrutura sugerida:

```text
transparencia-df/
├── services/
│   ├── collector/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── downloader.py
│   │   └── manifest.py
│   ├── curator/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── normalization.py
│   │   ├── validation.py
│   │   └── quarantine.py
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── quality_metrics.py
│   │   ├── organization_metrics.py
│   │   ├── employee_metrics.py
│   │   └── anomaly_metrics.py
│   ├── dw_loader/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── loader.py
│   └── publisher/
│       ├── __init__.py
│       ├── main.py
│       └── exporter.py
├── shared/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── logging.py
│   ├── models.py
│   ├── identity.py
│   └── filesystem.py
├── config/
│   ├── source_schema.example.yaml
│   └── analytics.yaml
├── migrations/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
│   ├── run_pipeline.sh
│   ├── migrate.sh
│   └── status.sh
├── data/
│   └── .gitkeep
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

Pode ajustar a estrutura se houver justificativa técnica simples.

## 4. Regra fundamental: contrato entre etapas

Cada job deve conhecer apenas sua entrada e sua saída.

- `collector` não conhece regras analíticas;
- `curator` não conhece PostgreSQL analítico;
- `analytics` não baixa arquivos;
- `dw_loader` não conhece detalhes do CSV original;
- `publisher` nunca acessa dados RAW.

Os dados devem ser compartilhados por volumes de arquivos e pelo PostgreSQL apenas quando necessário.

## 5. Organização dos dados em disco

Utilize um volume persistente montado em `/data`.

```text
/data/
├── raw/
│   └── remuneracao/
│       └── ano=YYYY/
│           └── mes=MM/
├── curated/
│   └── remuneracao/
│       └── ano=YYYY/
│           └── mes=MM/
├── quarantine/
│   └── remuneracao/
│       └── ano=YYYY/
│           └── mes=MM/
├── analytics/
│   └── ano=YYYY/
│       └── mes=MM/
├── public/
└── logs/
```

### RAW

- imutável;
- nunca modificar ou sobrescrever silenciosamente;
- registrar URL original, data/hora do download, tamanho e SHA-256;
- em caso de alteração do arquivo de origem para a mesma competência, preservar as duas versões.

### Curated

- somente dados que passaram pelas regras obrigatórias de curadoria;
- formato Parquet;
- particionamento por ano/mês;
- escrita atômica: gerar arquivo temporário e renomear apenas após sucesso.

### Quarantine

- registros rejeitados ou suspeitos;
- preservar os dados necessários para diagnóstico;
- incluir `reason_code` e descrição da validação que falhou.

## 6. Identificação e privacidade

Os arquivos de origem podem conter dados identificáveis.

Regras:

1. RAW é privado e nunca deve ser publicado.
2. Não propagar nome e fragmento de CPF para a camada pública.
3. A identidade lógica do servidor deve ser baseada na combinação normalizada disponível na fonte, por exemplo:
   - nome normalizado;
   - fragmento de CPF disponibilizado.
4. Gerar uma chave pseudonimizada estável usando HMAC-SHA256 com segredo configurado por variável de ambiente.
5. Nunca versionar o segredo.
6. No DW, utilizar chave surrogate numérica em `dim_servidor`, associada à chave pseudonimizada.
7. Exportações públicas devem ser agregadas e não permitir reidentificação direta.

## 7. Collector

Responsabilidade: localizar/receber a URL do arquivo mensal e baixá-lo com segurança.

CLI esperada:

```bash
python -m services.collector.main   --competencia 2026-08   --url "URL_DO_CSV"
```

Requisitos:

- download em streaming;
- timeout configurável;
- retry com exponential backoff apenas para falhas transitórias;
- gravação primeiro em `.tmp`;
- calcular SHA-256;
- verificar que o arquivo não está vazio;
- validar minimamente se pode ser interpretado como CSV;
- mover atomicamente para RAW somente após sucesso;
- registrar manifesto no PostgreSQL;
- se o mesmo hash já estiver registrado, retornar sucesso sem duplicar;
- não apagar versões antigas;
- logs estruturados.

O sistema deve permitir futuramente implementar descoberta automática da URL, mas `--url` deve funcionar desde o MVP.

## 8. Curator / Data Quality

Entrada: CSV RAW.

Saídas:

- Parquet curado;
- Parquet de quarentena;
- relatório resumido de qualidade;
- atualização do estado da execução.

CLI:

```bash
python -m services.curator.main --competencia 2026-08
```

### Mapeamento da fonte

**Não inventar nomes de colunas do Portal.**

O mapeamento entre colunas de origem e modelo normalizado deve ficar em:

```text
config/source_schema.yaml
```

Se um CSV ou dicionário de dados real for fornecido junto desta especificação, utilize os nomes reais.

Se não for fornecido, gere `source_schema.example.yaml`, valide sua existência e faça o programa falhar de forma clara até que o mapeamento seja configurado.

### Validações mínimas

Implementar arquitetura extensível de regras com `reason_code`.

Incluir:

- campos obrigatórios;
- conversão e formato de datas;
- conversão segura de valores monetários;
- registros integralmente duplicados;
- duplicidade pela chave lógica configurada;
- valores nulos inesperados;
- valores não numéricos em campos financeiros;
- meses/competência inconsistentes;
- valores negativos: sinalizar conforme configuração, não assumir erro;
- consistência aritmética entre créditos, bruto, descontos e líquido **somente quando as colunas reais permitirem essa validação**;
- contagem de registros da competência;
- comparação da quantidade de registros com competências anteriores;
- geração de métricas de qualidade.

Não afirmar que uma anomalia representa fraude ou irregularidade administrativa.

## 9. Contrato do Parquet curado

Defina um modelo normalizado, documentado e versionado.

Exemplo conceitual:

```text
competencia
servidor_key
orgao_codigo
orgao_nome
cargo_codigo
cargo_nome
funcao_codigo
funcao_nome
situacao_funcional
remuneracao_basica
horas_extras
verbas_eventuais
verbas_judiciais
outros_creditos
remuneracao_bruta
irrf
previdencia
outros_descontos
remuneracao_liquida
source_file_hash
pipeline_version
```

Essa lista é conceitual. Adapte aos campos realmente existentes na fonte.

Incluir `schema_version`.

## 10. Analytics

Entrada: Parquet curado.

Tecnologia principal: DuckDB sobre Parquet, usando SQL legível.

CLI:

```bash
python -m services.analytics.main --competencia 2026-08
```

Gerar métricas em grupos independentes.

### 10.1 Qualidade

- total RAW;
- total curado;
- total em quarentena;
- quantidade e percentual por `reason_code`;
- duplicidades;
- variação de registros entre competências;
- meses disponíveis/ausentes.

### 10.2 Órgãos

Quando os dados permitirem:

- quantidade de servidores/vínculos;
- total bruto;
- média;
- mediana;
- P25/P75;
- P10/P90;
- desvio padrão;
- coeficiente de variação;
- participação no total analisado;
- valores e participação de horas extras;
- valores e participação de verbas extraordinárias;
- evolução mensal.

### 10.3 Servidor

Gerar indicadores históricos sem publicação de identidade:

- quantidade de meses observados;
- quantidade de órgãos distintos;
- total bruto no período;
- média mensal;
- mediana;
- desvio padrão;
- frequência de horas extras;
- frequência de verbas extraordinárias;
- meses com comportamento atípico.

### 10.4 Anomalias estatísticas

Aplicar apenas quando houver quantidade mínima configurável de observações.

Implementar:

- Z-Score;
- IQR;
- percentis.

Comparações possíveis:

- servidor contra seu próprio histórico;
- servidor contra mesmo cargo + órgão + competência;
- cargo/função dentro do órgão.

Anomalia deve ser chamada de:

`estatisticamente_atipico`

Nunca utilizar termos como fraude, irregular, ilegal ou erro administrativo como conclusão automática.

## 11. Data Warehouse

PostgreSQL será a camada de consumo, não a fonte histórica primária.

Crie migrations Alembic.

### Tabelas de controle

No mínimo:

#### `source_file_manifest`

- id;
- dataset;
- competencia;
- source_url;
- original_filename;
- sha256;
- file_size;
- downloaded_at;
- pipeline_version.

#### `pipeline_execution`

- id;
- dataset;
- competencia;
- source_file_id;
- status;
- started_at;
- finished_at;
- error_message;
- pipeline_version.

Status sugeridos:

```text
DISCOVERED
DOWNLOADING
DOWNLOADED
CURATING
CURATED
ANALYZING
ANALYZED
LOADING_DW
DW_LOADED
PUBLISHING
PUBLISHED
FAILED
```

Pode modelar falhas por etapa de forma mais adequada se mantiver legibilidade.

### Modelo dimensional

Criar, conforme dados disponíveis:

- `dim_tempo`;
- `dim_orgao`;
- `dim_servidor`;
- `dim_cargo`;
- `dim_funcao`;
- `fato_remuneracao`.

Criar também tabelas analíticas/agregadas quando útil:

- `agg_orgao_mes`;
- `agg_servidor_periodo`;
- `agg_cargo_mes`;
- `data_quality_summary`;
- `statistical_anomaly`.

Adicionar chaves únicas e índices necessários para impedir duplicação silenciosa.

## 12. DW Loader

Entrada: resultados analíticos + Parquet curado.

CLI:

```bash
python -m services.dw_loader.main --competencia 2026-08
```

Requisitos:

- executar dentro de transação;
- fazer upsert das dimensões;
- carga idempotente da fato;
- nunca duplicar uma competência em reexecução;
- permitir `--force` para recarga explícita;
- rollback completo em caso de falha;
- atualizar `pipeline_execution` somente após commit;
- migrations separadas da execução normal.

Se uma competência for recarregada, utilizar estratégia clara e segura, por exemplo:

1. iniciar transação;
2. remover/substituir somente os dados daquela competência;
3. inserir nova versão;
4. commit.

## 13. Publisher

Responsabilidade: produzir somente dados adequados a consumo público.

CLI:

```bash
python -m services.publisher.main --competencia 2026-08
```

Implementar inicialmente:

- refresh de views/materialized views necessárias;
- exportação de datasets agregados para `/data/public`;
- formatos Parquet e CSV; JSON apenas se simples;
- nenhum nome, CPF ou chave que permita identificação direta;
- documentação do significado dos indicadores.

Não implementar frontend nesta fase.

## 14. Idempotência e resiliência

Princípios obrigatórios:

1. executar uma etapa duas vezes deve produzir o mesmo estado final;
2. nenhuma etapa pode sobrescrever dados anteriores silenciosamente;
3. escrita de arquivos deve ser atômica;
4. carga no PostgreSQL deve usar transações;
5. falhas devem ser registradas;
6. nunca usar `except Exception: pass`;
7. retry somente para falhas transitórias;
8. erro de validação de dados não deve ser tratado como erro transitório;
9. o DW deve poder ser reconstruído a partir dos Parquets;
10. os Parquets devem poder ser reconstruídos a partir dos RAW.

## 15. Logging

Utilizar logs estruturados e legíveis.

Todo log relevante deve incluir quando aplicável:

- serviço;
- dataset;
- competência;
- etapa;
- evento;
- duração;
- quantidade de registros;
- `source_file_hash`;
- erro.

Nunca registrar segredo, senha, CPF ou nome completo.

## 16. Docker

Criar `docker-compose.yml` completo.

Serviços esperados:

```text
postgres
collector
curator
analytics
dw-loader
publisher
```

Os jobs Python podem utilizar a mesma imagem base, mas devem possuir comandos independentes.

### PostgreSQL

O Compose deve:

- subir PostgreSQL 16;
- usar volume persistente;
- healthcheck;
- usuário/banco/senha via `.env`;
- não usar senha hardcoded;
- expor porta local apenas se necessário;
- usar rede interna entre containers.

### Volumes

Montar `/data` nos jobs que necessitam.

### Segurança

- containers Python executados como usuário não-root;
- imagem slim;
- versões de dependências travadas;
- não copiar `.env` para a imagem;
- adicionar `.dockerignore`.

## 17. Orquestração

Não utilizar orquestrador externo.

Criar:

```text
scripts/run_pipeline.sh
```

que execute sequencialmente:

```text
collector
curator
analytics
dw-loader
publisher
```

via Docker Compose.

Exemplo esperado:

```bash
./scripts/run_pipeline.sh   --competencia 2026-08   --url "URL_DO_CSV"
```

Cada etapa deve permanecer executável individualmente.

O script deve:

- `set -euo pipefail`;
- interromper em falha;
- imprimir claramente a etapa atual;
- retornar código diferente de zero em erro.

Criar também targets no `Makefile`.

Exemplos desejados:

```bash
make build
make up
make migrate
make collector COMPETENCIA=2026-08 URL=...
make curator COMPETENCIA=2026-08
make analytics COMPETENCIA=2026-08
make load COMPETENCIA=2026-08
make publish COMPETENCIA=2026-08
make pipeline COMPETENCIA=2026-08 URL=...
make status
make test
make lint
```

## 18. Configuração

Criar `.env.example`.

Variáveis mínimas:

```text
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
DATABASE_URL=

DATA_ROOT=/data
LOG_LEVEL=INFO
TZ=America/Sao_Paulo

IDENTITY_HMAC_KEY=
PIPELINE_VERSION=

HTTP_TIMEOUT_SECONDS=
HTTP_MAX_RETRIES=
```

Não versionar `.env`.

Configurações de regras analíticas e limites devem ficar em YAML/TOML quando fizer sentido, evitando números mágicos no código.

## 19. Testes

Crie dados sintéticos pequenos e sem dados pessoais reais.

### Unitários

Testar:

- normalização;
- parsing monetário;
- HMAC de identidade;
- regras de validação;
- cálculo de Z-Score;
- cálculo de IQR;
- geração de paths;
- idempotência de funções críticas.

### Integração

Testar:

- CSV sintético → Parquet;
- quarentena;
- DuckDB → métricas;
- carga PostgreSQL;
- reexecução da mesma competência sem duplicação.

### E2E

Criar fixture pequena que permita executar:

```text
collector/mock → curator → analytics → DW → publisher
```

e verificar o estado final.

O `collector` real deve ter HTTP mockado nos testes.

## 20. Qualidade do código

O código deve ser fácil de entender por outro desenvolvedor.

Regras:

- funções pequenas;
- nomes explícitos;
- tipagem;
- docstrings apenas onde agregam valor;
- evitar abstrações prematuras;
- evitar classes quando funções simples bastarem;
- evitar metaprogramação;
- SQL formatado e legível;
- comentários explicam o motivo, não repetem o código;
- separar regra de negócio de I/O;
- nenhuma dependência sem justificativa.

Configurar Ruff no `pyproject.toml`.

## 21. README obrigatório

O README deve explicar de forma objetiva:

1. arquitetura;
2. pré-requisitos;
3. como configurar `.env`;
4. como configurar `source_schema.yaml`;
5. como subir PostgreSQL;
6. como executar migrations;
7. como processar uma competência;
8. como reprocessar;
9. onde ficam RAW, Parquet, quarentena e publicações;
10. como executar testes;
11. como consultar o status do pipeline;
12. como configurar execução mensal via cron;
13. política de privacidade e dados públicos;
14. limitações das análises estatísticas.

Adicionar um diagrama Mermaid simples da arquitetura.

## 22. Cron

Não configurar automaticamente o cron do host.

Fornecer no README um exemplo seguro.

Criar `run_monthly.sh` apenas se for possível descobrir de forma confiável a competência/URL. Caso contrário, documentar como fornecer a URL.

## 23. O que não fazer

- não criar frontend;
- não criar Kubernetes;
- não criar Kafka;
- não criar Airflow;
- não criar Celery;
- não armazenar secrets no Git;
- não publicar dados pessoais;
- não inventar colunas da fonte;
- não classificar automaticamente anomalias como fraude/ilegalidade;
- não excluir RAW após processamento;
- não acoplar analytics ao layout do CSV original;
- não usar PostgreSQL como única cópia dos dados históricos.

## 24. Critérios de aceite

O projeto estará pronto quando for possível executar, em uma máquina apenas com Docker + Docker Compose:

```bash
cp .env.example .env
# preencher segredos/configuração

docker compose build
docker compose up -d postgres
make migrate

make pipeline   COMPETENCIA=2026-08   URL="URL_REAL_DO_ARQUIVO"
```

e obter:

1. CSV RAW preservado;
2. manifesto com SHA-256;
3. Parquet curado;
4. quarentena quando houver inconsistências;
5. resumo de qualidade;
6. métricas analíticas;
7. dimensões/fatos/agregados no PostgreSQL;
8. arquivos públicos agregados;
9. estado `PUBLISHED` no controle do pipeline.

Ao executar novamente a mesma competência com o mesmo arquivo:

- não duplicar RAW;
- não duplicar fatos;
- não gerar agregados duplicados;
- concluir com sucesso.

Também deve ser possível apagar o DW, recriar o banco e reconstruí-lo a partir dos Parquets existentes.

## 25. Instrução final para a IA geradora de código

Entregue **todos os arquivos completos**, não apenas exemplos ou pseudocódigo.

Antes de gerar o código:

1. verifique se foi fornecido um CSV real e/ou dicionário de dados;
2. se existir, baseie o schema nos campos reais;
3. se não existir, não invente colunas: gere o mecanismo configurável e documente exatamente o que precisa ser preenchido em `source_schema.yaml`.

Ao finalizar:

- mostre a árvore final do projeto;
- liste os comandos exatos para primeira execução;
- indique qualquer ponto que permaneça dependente do schema real da fonte;
- garanta que `docker compose config` seja válido;
- garanta que os imports Python e comandos do Makefile/Compose sejam coerentes entre si;
- não deixe TODOs que impeçam a execução do pipeline básico.
