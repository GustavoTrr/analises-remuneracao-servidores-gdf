# Dicionário de Dados — Remuneração dos Servidores do Governo do Distrito Federal

**Versão consolidada oficial de trabalho — 2026**

## 1. Identificação da base

- **Fonte de dados:** SIGRH (SEEC) / SIAPE (PCDF/CBMDF/PMDF) / CEB / CAESB / TERRACAP / CEASA / BRB
- **Base de dados:** Remuneração dos Servidores
- **Descrição oficial:** conjunto de dados que apresenta a remuneração dos servidores do Governo do Distrito Federal, detalhada por órgão e nome do servidor.
- **Periodicidade/disponibilização:** as bases são encaminhadas até o final do mês subsequente ao mês de referência da consulta, para inclusão de todos os valores efetivamente pagos aos servidores.
- **Fonte documental principal:** Portal de Dados Abertos do Distrito Federal — Dicionário de Dados da base *Remuneração dos Servidores*.

> **Nota de uso:** as descrições abaixo preservam o nome e o tipo dos campos do dicionário oficial e acrescentam uma interpretação funcional e jurídica consolidada para uso no projeto analítico. As referências legais explicam a natureza das parcelas quando aplicáveis, mas não substituem a identificação da rubrica específica na folha de pagamento.

---

## 2. Campos de identificação e vínculo

### NOME
- **Tipo:** TEXTO
- **Descrição oficial:** Nome completo do servidor.
- **Descrição consolidada:** Nome do servidor conforme disponibilizado na base de remuneração.

### CPF
- **Tipo:** TEXTO
- **Descrição oficial:** Nº do Cadastro de Pessoa Física mascarado.
- **Descrição consolidada:** CPF apresentado de forma parcialmente mascarada. Para identificação analítica de uma pessoa ao longo do tempo, recomenda-se não utilizar este campo isoladamente quando houver possibilidade de homônimos ou alterações de vínculo.

### ÓRGÃO
- **Tipo:** TEXTO
- **Descrição oficial:** Órgão vinculado ao servidor.
- **Descrição consolidada:** Nome do órgão ou entidade ao qual o vínculo remuneratório do servidor está associado na competência.

### CARGO
- **Tipo:** TEXTO
- **Descrição oficial:** Posição que o servidor ocupa no órgão de forma permanente.
- **Descrição consolidada:** Cargo, emprego ou posição permanente registrada para o vínculo do servidor.

### FUNÇÃO
- **Tipo:** TEXTO
- **Descrição oficial:** Designação temporária para desempenho de determinadas atribuições (cargo comissionado).
- **Descrição consolidada:** Função, cargo em comissão ou designação temporária vinculada ao servidor na competência. Pode estar vazia quando não houver função registrada.

### SITUAÇÃO
- **Tipo:** TEXTO
- **Descrição oficial:** Condição do servidor em relação ao exercício de suas atividades.
- **Descrição consolidada:** Situação funcional informada para o vínculo na competência.

### MÊS
- **Tipo:** NÚMERO
- **Descrição oficial:** Mês de referência.
- **Descrição consolidada:** Mês da competência remuneratória.

### ANO
- **Tipo:** NÚMERO
- **Descrição oficial:** Ano de referência.
- **Descrição consolidada:** Ano da competência remuneratória.

### CÓDIGO DO ÓRGÃO
- **Tipo:** NÚMERO
- **Descrição oficial:** Órgão vinculado ao servidor.
- **Descrição consolidada:** Código numérico utilizado para identificar o órgão ou entidade do vínculo.

### MATRÍCULA
- **Tipo:** TEXTO
- **Descrição oficial:** Matrícula do servidor no órgão vinculado.
- **Descrição consolidada:** Identificador funcional do servidor dentro do órgão ou entidade. Como uma mesma pessoa pode possuir mais de um vínculo, a matrícula deve ser tratada como identificador do vínculo, e não necessariamente da pessoa.

---

## 3. Campos de créditos e recebimentos

### REMUNERAÇÃO BÁSICA
- **Tipo:** MOEDA
- **Descrição oficial:** Remuneração básica.
- **Descrição consolidada:** Representa a parcela principal e ordinária da remuneração vinculada ao cargo ou emprego, podendo agregar vencimento básico e outras parcelas classificadas pelo sistema como remuneração regular.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO**. Valores negativos podem ocorrer em competências com estornos, proporcionalizações ou acertos de rubricas anteriormente lançadas, sem significar juridicamente a existência de “salário negativo”.
- **Referência jurídica:** LC nº 840/2011, arts. 68 e 71 — a remuneração é composta por vencimentos e vantagens, e o vencimento básico corresponde ao valor fixado na tabela da carreira.

### BENEFÍCIOS
- **Tipo:** MOEDA
- **Descrição oficial:** Valor dos benefícios.
- **Descrição consolidada:** Representa os benefícios pagos ao servidor que o Portal consolida separadamente da remuneração básica, incluindo parcelas assistenciais ou indenizatórias previstas para o vínculo.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO**.
- **Observação:** o arquivo aberto não discrimina quais benefícios formaram o total informado.
- **Referência jurídica:** depende do benefício específico. A LC nº 840/2011 disciplina, entre outros, auxílio-natalidade, auxílio pré-escolar e outras vantagens; empregados públicos podem estar sujeitos a legislação e instrumentos próprios.

### VALOR DA FUNÇÃO
- **Tipo:** MOEDA
- **Descrição oficial:** Valor das funções.
- **Descrição consolidada:** Corresponde à retribuição decorrente do exercício temporário de função de confiança, cargo em comissão ou função equivalente, além da remuneração do cargo efetivo quando cabível.
- **Comportamento no cálculo:** é crédito e compõe positivamente o **BRUTO** enquanto houver direito à função.
- **Referência jurídica:** LC nº 840/2011, art. 77.

### COMISSÃO CONSELHEIRO
- **Tipo:** MOEDA
- **Descrição oficial:** Comissão conselheiro.
- **Descrição consolidada:** Gratificação, normalmente denominada *jeton*, paga pela participação remunerada em conselho, comitê ou outro órgão de deliberação coletiva.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO**.
- **Referência jurídica:** Lei nº 4.585/2011, especialmente arts. 2º a 4º, sem prejuízo de normas específicas de cada colegiado.

### HORA EXTRA
- **Tipo:** MOEDA
- **Descrição oficial:** Total de hora extra.
- **Descrição consolidada:** Registra a remuneração por serviço prestado além da jornada ordinária.
- **Comportamento no cálculo:** é crédito e compõe positivamente o **BRUTO**.
- **Referência jurídica:** para servidores regidos pela LC nº 840/2011, art. 60 (ampliação excepcional e temporária da jornada) e art. 84 (serviço extraordinário remunerado com acréscimo de 50% sobre o valor da hora normal). Outros vínculos podem seguir regras distintas.

### VERBAS EVENTUAIS
- **Tipo:** MOEDA
- **Descrição oficial:** Valor das verbas eventuais.
- **Descrição consolidada:** Categoria agregadora utilizada pelo Portal para pagamentos que não integram necessariamente a remuneração ordinária mensal e surgem em competências específicas.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO**.
- **Observação:** há evidência administrativa de que parcelas como 13º salário e adicional de férias podem aparecer entre as verbas eventuais, mas o arquivo não informa quais rubricas específicas compõem cada valor.
- **Referência jurídica:** LC nº 840/2011, art. 91 (adicional de férias) e arts. 92 a 95 (13º salário), além de fundamentos próprios para outras verbas eventuais.

### VERBAS JUDICIAIS
- **Tipo:** MOEDA
- **Descrição oficial:** Valor das verbas judiciais.
- **Descrição consolidada:** Valores incluídos na folha em cumprimento a decisão judicial com repercussão remuneratória, como diferenças ou vantagens reconhecidas judicialmente.
- **Comportamento no cálculo:** são créditos e compõem positivamente o **BRUTO**.
- **Observação:** não existe uma única lei que determine o valor, pois o fundamento imediato é a decisão judicial e a norma material discutida em cada processo.
- **Referência jurídica:** LC nº 840/2011, art. 90, entre outras normas aplicáveis ao caso concreto.

### DESCONTOS A MAIOR
- **Tipo:** MOEDA
- **Descrição oficial:** Valor da reposição de descontos a maior.
- **Descrição consolidada:** Apesar do nome, representa dinheiro devolvido ao servidor porque houve desconto superior ao que deveria ter sido efetuado anteriormente.
- **Comportamento no cálculo:** é **crédito** e compõe positivamente o **BRUTO**; não deve ser tratado como desconto.
- **Referência jurídica:** para servidores submetidos à LC nº 840/2011, art. 118, parágrafo único, sobre débito decorrente de erro desfavorável ao servidor no processamento da folha.

### LICENÇA PRÊMIO
- **Tipo:** MOEDA
- **Descrição oficial:** Valor da licença prêmio.
- **Descrição consolidada:** Registra valores relacionados à licença-prêmio por assiduidade convertida em pecúnia, especialmente direitos adquiridos sob regime anterior.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO** e pode coexistir com outras verbas na mesma competência, sem significar necessariamente que o servidor esteve afastado naquele mês.
- **Referência jurídica:** LC nº 952/2019, especialmente arts. 2º a 6º. O art. 6º permite, mediante autorização e disponibilidade orçamentária, a conversão de até um mês de licença-prêmio em pecúnia por ano nas hipóteses previstas.

### OUTROS RECEBIMENTOS
- **Tipo:** MOEDA
- **Descrição oficial:** Valor de outros recebimentos.
- **Descrição consolidada:** Categoria residual de créditos, reunindo pagamentos que entram na remuneração da competência, mas não foram classificados pelo Portal em remuneração básica, benefícios, função, conselho, horas extras, verbas eventuais, verbas judiciais, licença-prêmio ou reposição de descontos a maior.
- **Comportamento no cálculo:** compõe positivamente o **BRUTO**.
- **Observação:** não possui uma única lei ou artigo próprio; o fundamento jurídico depende da rubrica que originou o pagamento. A natureza exata não pode ser determinada apenas pelo CSV.

---

## 4. Campos de descontos obrigatórios

### IRRF
- **Tipo:** MOEDA
- **Descrição oficial:** Valor do desconto de Imposto de Renda Retido na Fonte.
- **Descrição consolidada:** Imposto de Renda Retido na Fonte incidente sobre rendimentos tributáveis pagos ao servidor.
- **Comportamento no cálculo:** não compõe positivamente o bruto; é desconto utilizado na apuração do **LÍQUIDO**, conforme base tributável, deduções e tabela vigente na competência.
- **Referência jurídica:** Lei federal nº 7.713/1988, especialmente arts. 1º, 2º e 7º.

### SEGURIDADE SOCIAL
- **Tipo:** MOEDA
- **Descrição oficial:** Valor do desconto de seguridade social.
- **Descrição consolidada:** Contribuição previdenciária descontada da remuneração ou dos proventos do servidor.
- **Comportamento no cálculo:** reduz o **LÍQUIDO**, não o **BRUTO**.
- **Referência jurídica:** para segurados do RPPS/DF, LC nº 769/2008, arts. 60 a 62. Outros vínculos, como empregados públicos, podem estar sujeitos ao RGPS.

### TETO REDUTOR
- **Tipo:** MOEDA
- **Descrição oficial:** Valor do desconto de teto redutor.
- **Descrição consolidada:** Valor retirado da remuneração quando as parcelas sujeitas ao limite constitucional ultrapassam o teto remuneratório aplicável ao agente público.
- **Comportamento no cálculo:** não reduz o valor apresentado como **BRUTO** no arquivo; aparece como desconto na obtenção do **LÍQUIDO**.
- **Referência jurídica:** para servidores distritais abrangidos pela LC nº 840/2011, art. 70, além dos atos específicos que atualizam o valor do teto aplicável.

### OUTROS DESCONTOS OBRIGATÓRIOS
- **Tipo:** MOEDA
- **Descrição oficial:** Valor de outros descontos obrigatórios.
- **Descrição consolidada:** Reúne descontos compulsórios que não foram individualizados nas colunas de IRRF, seguridade social, teto redutor ou pagamento a maior.
- **Comportamento no cálculo:** é subtraído do **BRUTO** para obtenção do **LÍQUIDO**.
- **Observação:** por ser uma categoria residual, não existe uma única lei que regulamente todo o campo; cada desconto possui fundamento próprio. O conjunto de dados não fornece a decomposição das rubricas.

### PAGAMENTO A MAIOR
- **Tipo:** MOEDA
- **Descrição oficial:** Valor dos descontos de pagamentos a maior.
- **Descrição consolidada:** Representa a recuperação de valores que a Administração identifica como pagos indevidamente ou além do devido ao servidor.
- **Comportamento no cálculo:** é desconto e, portanto, é subtraído do **BRUTO** para obtenção do **LÍQUIDO**.
- **Referência jurídica:** para servidores regidos pela LC nº 840/2011, arts. 119 e 120, que disciplinam reposições e indenizações ao erário.
- **Distinção importante:** é conceitualmente o inverso de **DESCONTOS A MAIOR**. Em **DESCONTOS A MAIOR**, a Administração devolve ao servidor valor descontado indevidamente; em **PAGAMENTO A MAIOR**, a Administração recupera valor anteriormente pago ao servidor além do devido.

---

## 5. Campos totalizadores

### BRUTO
- **Tipo:** MOEDA
- **Descrição oficial:** Valor bruto da remuneração.
- **Descrição consolidada:** Total dos créditos registrados para a linha e competência antes dos descontos obrigatórios.
- **Relação observada na base:**

```text
BRUTO =
    REMUNERAÇÃO BÁSICA
  + BENEFÍCIOS
  + VALOR DA FUNÇÃO
  + COMISSÃO CONSELHEIRO
  + HORA EXTRA
  + VERBAS EVENTUAIS
  + VERBAS JUDICIAIS
  + DESCONTOS A MAIOR
  + LICENÇA PRÊMIO
  + OUTROS RECEBIMENTOS
```

- **Observação:** a soma deve respeitar os sinais efetivamente presentes nas parcelas, inclusive eventuais valores negativos decorrentes de estornos, acertos ou proporcionalizações.
- **Natureza:** campo totalizador; não corresponde a uma verba autônoma criada por uma lei específica.

### LÍQUIDO
- **Tipo:** MOEDA
- **Descrição oficial:** Valor líquido após descontos obrigatórios.
- **Descrição consolidada:** Valor restante após a dedução, do **BRUTO**, dos descontos obrigatórios informados nas colunas da base.
- **Relação observada na base:**

```text
LÍQUIDO =
    BRUTO
  - IRRF
  - SEGURIDADE SOCIAL
  - TETO REDUTOR
  - OUTROS DESCONTOS OBRIGATÓRIOS
  - PAGAMENTO A MAIOR
```

- **Natureza:** campo totalizador; não corresponde a uma verba autônoma criada por lei específica.

---

## 6. Resumo da natureza financeira dos campos monetários

| Campo | Natureza na base | Efeito principal |
|---|---|---|
| REMUNERAÇÃO BÁSICA | Crédito | Soma ao BRUTO |
| BENEFÍCIOS | Crédito | Soma ao BRUTO |
| VALOR DA FUNÇÃO | Crédito | Soma ao BRUTO |
| COMISSÃO CONSELHEIRO | Crédito | Soma ao BRUTO |
| HORA EXTRA | Crédito | Soma ao BRUTO |
| VERBAS EVENTUAIS | Crédito | Soma ao BRUTO |
| VERBAS JUDICIAIS | Crédito | Soma ao BRUTO |
| DESCONTOS A MAIOR | Crédito | Soma ao BRUTO |
| LICENÇA PRÊMIO | Crédito | Soma ao BRUTO |
| OUTROS RECEBIMENTOS | Crédito | Soma ao BRUTO |
| IRRF | Desconto | Reduz o LÍQUIDO |
| SEGURIDADE SOCIAL | Desconto | Reduz o LÍQUIDO |
| TETO REDUTOR | Desconto | Reduz o LÍQUIDO |
| OUTROS DESCONTOS OBRIGATÓRIOS | Desconto | Reduz o LÍQUIDO |
| PAGAMENTO A MAIOR | Desconto | Reduz o LÍQUIDO |
| BRUTO | Totalizador | Soma dos créditos |
| LÍQUIDO | Totalizador | BRUTO menos descontos obrigatórios |

---

## 7. Observações para modelagem e análise

1. **Usar os nomes oficiais dos campos como referência canônica.** O dicionário oficial utiliza **PAGAMENTO A MAIOR** no singular.
2. **Não interpretar “DESCONTOS A MAIOR” como débito.** Apesar do nome, o próprio dicionário oficial o define como reposição de descontos a maior, portanto seu comportamento é de crédito.
3. **Não inferir a natureza jurídica exata de categorias agregadas** como BENEFÍCIOS, VERBAS EVENTUAIS, OUTROS RECEBIMENTOS ou OUTROS DESCONTOS OBRIGATÓRIOS sem acesso às rubricas de folha que deram origem ao total.
4. **Valores negativos devem ser preservados na camada analítica**, pois podem representar estornos, ajustes, proporcionalizações ou correções.
5. **A granularidade analítica deve considerar pessoa, vínculo, órgão e competência.** Matrícula identifica o vínculo funcional e CPF mascarado não deve ser tratado, isoladamente, como chave absoluta de pessoa.
6. **BRUTO e LÍQUIDO devem ser validados por recomposição matemática** a partir das parcelas componentes, permitindo registrar divergências para auditoria e qualidade de dados.
7. **A legislação citada é contextual.** Como a base consolida vínculos provenientes de diferentes sistemas e entidades, determinadas pessoas podem estar submetidas a regimes jurídicos distintos.

---

## 8. Fonte oficial

Portal de Dados Abertos do Distrito Federal — **Dicionário de Dados / Remuneração dos Servidores**.

Base disponível no Portal de Dados Abertos do Distrito Federal, conjunto **Portal da Transparência — Remuneração dos Servidores**.
