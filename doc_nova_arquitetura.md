# Progresso da migração — Fase 2 (Camada Prata)

> Documento de acompanhamento da Fase 2 (camada Prata): decisões de negócio, convenção de nomes e status por tabela. Não cobre infraestrutura/Bronze (isso fica no `contexto.md` original). Última atualização: 21/07/2026.

---

## O que é a Fase 2, em 3 frases

Com as 7 áreas de negócio já migradas pra Bronze, a Fase 2 recria a camada **Prata** de cada área, **replicando fielmente** as regras de negócio do projeto legado — só muda a arquitetura (lê da Bronze, nunca do Sapiens direto) e a nomenclatura das tabelas. O resultado final (os dados, os números) **precisa ser idêntico** ao que já está em produção hoje — clientes já têm Power BI consumindo o projeto legado, então essa migração é troca de fundação, não de resultado. Começamos pelo **Comercial** (7 tabelas), tabela por tabela, sempre com validação antes de seguir.

---

## Onde fica cada coisa

- **Prata**: `dw_aquario/<area>/prata/` — 1 arquivo por tabela, nome do arquivo = nome da tabela nova em minúsculo (ex.: `dim_cliente.py` gera `DIM_CLIENTE`).
- **Catálogo**: `comercial/prata/tabelas.py` — nome antigo x novo, classificação, estratégia de carga, status de cada tabela do Comercial.
- **Conferência**: `dw_aquario/conferencias/conferencia_<tabela_nova>.py` — valida se a Prata bate com o legado (dado a dado, não só contagem) antes de considerar a tabela pronta.

---

## Status atual (21/07/2026)

**Bronze**: concluída nas 7 áreas — pré-requisito já atendido, todas as tabelas fonte disponíveis. Auditoria do bug de `tem_codfil` (Regra 6) estendida a todas as áreas em 17/07/2026 — 9 tabelas corrigidas fora do Comercial (Estoque, Produção, Laudos RMA), 2 confirmadas corretas (Expedição, Rastreabilidade); ver seção "Correção do `tem_codfil` nas demais áreas da Bronze". OPEX não teve nenhuma tabela com `tem_codfil` (área sem conceito de filial).

**Prata**:

| Área                                          | Status                                                                                                                             |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Comercial                                     | **7/7 tabelas construídas, testadas na VM e consideradas finalizadas** (20/07/2026) — ver ressalva na seção "Comercial finalizado" |
| Laudos RMA                                    | **5/5 tabelas construídas, testadas na VM e consideradas finalizadas** (21/07/2026) — ver seção "Laudos RMA finalizado"            |
| OPEX                                          | **1/1 tabela construída, testada na VM e validada** (21/07/2026) — ver seção "OPEX"                                                |
| Rastreabilidade                               | **1/1 tabela construída, testada na VM e validada** (21/07/2026) — ver seção "Rastreabilidade"                                     |
| Produção                                      | **Prata criada (21/07/2026)** — 7/7 tabelas prontas, aguardando extração/conferência na VM (ver seção "Produção")                  |
| Estoque, Expedição                            | Não iniciada                                                                                                                       |


### Tabelas da Prata do Comercial

| Tabela nova              | Tabela legado           | Classificação | Status                                                                                                                                                   |
| ------------------------ | ----------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DIM_CONDICAO_PAGAMENTO` | `USU_VBIACONDPGTO`      | Dimensão      | ✅ **Validada** — dados batem 100% com o legado                                                                                                           |
| `DIM_PRODUTO`            | `USU_BVIPRODUTOS`       | Dimensão      | ✅ **Validada** — testada na VM, conferência batendo                                                                                                      |
| `DIM_REPRESENTANTE`      | `USU_VBIREPRESENTANTES` | Dimensão      | ✅ **Validada** — testada na VM, conferência batendo                                                                                                      |
| `DIM_REGIONAL`           | `USU_VBIREGIONAIS`      | Dimensão      | ✅ **Validada** — testada na VM, conferência batendo (melhoria aplicada — ver abaixo)                                                                     |
| `FAT_METAS`              | `USU_VBIMETAS`          | Fato          | ✅ **Validada (20/07/2026)** — testada com troca real de representante em produção (506 → 544), conferência bateu 100% (ver "Comercial finalizado")       |
| `DIM_CLIENTE`            | `USU_BVIACLIENTES`      | Dimensão      | ✅ **Validada (17/07/2026)** — 3 bugs de Bronze encontrados e corrigidos na conferência (ver observação abaixo); MINUS final bateu 0 dos dois lados       |
| `FAT_FATURAMENTO`        | `USU_VBIAFATURAMENTO`   | Fato          | ✅ **Validada (20/07/2026)** — testada na VM, índices da Bronze corrigidos, validação extra por agregado mensal batendo 100% (ver "Comercial finalizado") |

**As 7 tabelas do Comercial estão construídas e testadas na VM.** Ver seção "Comercial finalizado" logo abaixo.

---

## Comercial finalizado (20/07/2026)

Todas as 7 tabelas testadas na VM (extração + conferência). Achados relevantes desta última rodada:

- **Performance / índices da Bronze**: `fat_faturamento.py` estava demorando bastante. Causa raiz: `full_reload_streaming()` (`core/loader.py`) nunca cria índice automático — só `upsert()` faz isso (via `_ensure_table`), e só na criação da tabela. As 7 tabelas grandes/transacionais da Bronze (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`) tinham perdido o índice quando foram dropadas e recarregadas para o fix do `tem_codfil` (17/07/2026) — a recarga (`full_reload_streaming`) não recriou o índice que existia antes do DROP. Índices recriados manualmente na VM; tempo total de extração+carga do `FAT_FATURAMENTO` caiu de bem lento para ~65s. **Pendência conhecida, não corrigida no código**: `full_reload_streaming()` continua sem criar índice — qualquer futuro "dropar e deixar recarregar" (padrão de correção usado várias vezes neste projeto) vai repetir esse mesmo problema até isso ser corrigido na função.
- **FAT_FATURAMENTO — validação extra por agregado mensal**: além da conferência linha a linha, validamos meses fechados (abril, maio, junho/2026) comparando soma de `VLR_LIQ`/`VLRBRUTO_TOTAL` e contagem por `TIPOREG`, direto no Sapiens x Prata — bateu 100% nos 3 meses. O pequeno resíduo visto em notas de janeiro/2026 (campos `CODCLIBASE`/`CODREGREP`/`CODREGCLI` de `E140NFV`) foi rastreado a uma oscilação ativa do próprio Sapiens (o valor mudava de um minuto pro outro em consultas diretas) — não é bug de pipeline, é instabilidade do dado de origem.
- **FAT_METAS — validado com mudança real de produção**: testado durante uma troca real de representante (saída do 506, entrada do 544) na meta de julho/2026. Confirmou que o fluxo Bronze → Prata → conferência reflete corretamente tanto atualização quanto substituição de linha (o Sapiens criou um `SEQREG` novo para o 544 em vez de editar o do 506 — ou seja, testou também o caminho de "linha órfã" que a limpeza de órfãos da Bronze precisa cobrir).

**Ressalva importante**: o Comercial não está sendo considerado 100% fechado em definitivo. Várias tabelas da Bronze são compartilhadas com outras áreas ainda não migradas (Laudos RMA, Rastreabilidade, Produção, Estoque) — pode surgir alguma divergência nova quando essas dependências forem exercitadas por elas. Mas a área em si (as 7 tabelas, suas regras de negócio e a validação contra o legado) está migrada e testada.

---

## Laudos RMA (21/07/2026, finalizado)

Segunda área a migrar, seguindo o mesmo processo do Comercial: analisar os 5 scripts legados (`aquario/laudos_rma/extract/`), decidir `DIM_`/`FAT_`, confirmar que a Bronze já tem tudo, só depois criar a Prata.

### Tabelas da Prata do Laudos RMA

| Tabela nova              | Tabela legado                    | Classificação | Origem                                                          | Status                                                                                                                                                                                                                    |
| ------------------------ | -------------------------------- | ------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DIM_RECLASSIF_DEFEITOS` | `USU_VBIARMA_RECLASSIF_DEFEITOS` | Dimensão      | Excel (`Z:\Dados\DefeitosProdutosRMA.xlsx`, aba `DescDefeitos`) | ✅ **Validada (21/07/2026)** — testada na VM, conferência batendo                                                                                                                                                        |
| `DIM_RECLASSIF_PRODUTOS` | `USU_VBIARMA_RECLASSIF_PRODUTOS` | Dimensão      | Excel (mesmo arquivo, aba `ClassifProdutos`)                    | ✅ **Validada (21/07/2026)** — testada na VM, conferência batendo                                                                                                                                                        |
| `DIM_INDICE_RMA`         | `USU_VBIARMA_INDICE_RMA`         | Dimensão      | Excel (`Z:\Dados\IndiceRMA.xlsx`, aba `Planilha1`)              | ✅ **Validada (21/07/2026)** — testada na VM, conferência batendo                                                                                                                                                        |
| `FAT_VENDAS_RMA`         | `USU_VBIARMA_VENDAS`             | Fato          | DW_BRONZE (E140NFV, E140IPV, E140IDE, E001TNS)                  | ✅ **Validada (20/07/2026)** — reescrita (agregação + window function) testada na VM: 3,6s total (contra 190s do legado e >1h30 da 1ª versão); conferência bateu com 1 linha de diferença (nota do dia corrente, esperado) |
| `FAT_LAUDOS`             | `USU_VBIARMA_LAUDOS`             | Fato          | DW_BRONZE (USU_TLAUITE + 13 JOINs)                              | ✅ **Validada (20/07/2026)** — testada na VM depois de 2 correções na Bronze (ver seção própria); conferência caiu de 35 mil divergências pra 1 linha (laudo aberto no dia, esperado)                                      |

**Ordem de construção**: das mais simples pras mais delicadas — `DIM_RECLASSIF_DEFEITOS` → `DIM_RECLASSIF_PRODUTOS` → `DIM_INDICE_RMA` → `FAT_VENDAS_RMA` → `FAT_LAUDOS` (por último, de propósito — é a mais complexa das 5).

**Cobertura da Bronze**: todas as tabelas Oracle usadas por `vbilaudos.py` (16, incluindo a subquery de reincidência) e `vbivendas.py` (4) já existem na Bronze — 9 exclusivas do catálogo do Laudos RMA + 10 compartilhadas com o Comercial. Nada precisava ser criado na Bronze para esta área.

### Decisão: as 3 tabelas de Excel continuam lendo direto do Excel (sem Bronze)

`DIM_RECLASSIF_DEFEITOS`, `DIM_RECLASSIF_PRODUTOS` e `DIM_INDICE_RMA` nunca tiveram origem Oracle — vêm de planilhas manuais (`Z:\Dados\DefeitosProdutosRMA.xlsx`, `Z:\Dados\IndiceRMA.xlsx`), alimentadas manualmente pelo time de negócio. **Confirmado com o usuário (20/07/2026): continuam lendo exatamente do mesmo caminho, sem criar uma camada Bronze de Excel.** É uma exceção deliberada à regra "Prata lê da Bronze, nunca da fonte direto" — não existe fonte Oracle equivalente pra essas 3 tabelas, então não há nada pra Bronze copiar.

### Corte de data do Laudos RMA — diferente do Comercial

O legado do Laudos RMA (`vbilaudos.py` e `vbivendas.py`) já filtrava `DATENT`/`DATEMI` `>= 01/01/2023` — diferente do corte de `01/01/2021` usado no Comercial. Regra 2 da Fase 2: só aplicamos corte novo quando o legado não tinha nenhum; aqui o legado já cortava em 2023, então o corte foi **mantido em `01/01/2023`** (`DATA_CORTE_LAUDOS` em `laudos_rma/config/settings.py`), não trocado pelo padrão de 2021.

### `FAT_LAUDOS` — melhorias de eficiência propostas e aplicadas (20/07/2026)

Diferente de tudo migrado no Comercial (sempre 1 query SQL + upsert/full_reload, sem lógica em pandas), `vbilaudos.py` calcula em Python: prazo (usa `date.today()`), reincidência (merge com uma segunda query), macro-região, classificação de entrega, chaves compostas. Usuário pediu para propor melhorias de eficiência, não só replicar — aplicadas 2, mantida 1 decisão de não mexer:

1. **Reincidência: window function em vez de self-join.** O legado calculava "a entrada anterior mais recente do mesmo número de série" com um self-join (`USU_TLAUITE`/`E440NFC` contra si mesma, `T1.DATENT > Tz.DATENT` + `GROUP BY MAX(Tz.DATENT)`) — custo que cresce mal (O(n²)-like) por número de série. Trocado por `LAG(DATENT) OVER (PARTITION BY USU_SERMAC ORDER BY DATENT)` — matematicamente equivalente (o maior valor anterior numa sequência ordenada É o valor imediatamente anterior), porque a query original usa o MESMO filtro tanto pro "atual" quanto pro "anterior" do cálculo (confirmado lendo os dois `WHERE`). Validado pela `conferencia_fat_laudos.py` (MINUS dado a dado) antes de ser considerada pronta — mesma régua de sempre.
2. **`_int_str()` vetorizado.** A versão original convertia `NUMBER` do Oracle pra string linha a linha via `.apply()` em Python puro. Trocado por `pd.to_numeric` + `Int64` (vetorizado), mesmo resultado nos 3 casos (numérico, nulo, já-texto).
3. **Não alterado**: `DS_PRAZO`/`REINCIDENTE`/`MACRO_REGIAO`/etc. já usam `np.select`/`np.where` (vetorizado) — mantidos exatamente iguais ao legado, sem reescrever pra SQL. Mesmo critério usado pra rejeitar a deduplicação do `FUNDPOB` no `FAT_FATURAMENTO`: risco de reescrever lógica de negócio sem poder testar contra Oracle real não compensa o ganho.

### Bug encontrado na conferência do `FAT_LAUDOS` (20/07/2026): 4 tabelas de referência zeradas na Bronze

Primeira rodada da conferência bateu **35.534 divergências** (>1/3 da tabela). Comparando as amostras campo a campo, a única diferença real era um valor vindo de `USU_TLAUCOR` (via `T0.USU_CODCOR = T14.USU_CODCOR`) — `None` na Prata, valor real no legado (ex.: `'CONSERTADO'`). O resumo do próprio ciclo da Bronze confirmou a causa na hora: `USU_TLAUCOR`, `USU_TLAUPRB`, `USU_TLAUSIT` e `USU_TLAUTIP` estavam com **0 linhas salvas** na Bronze.

Causa raiz (1): mesmo bug do `E085CLI` (Comercial) — essas 4 tabelas de referência (cor, problema, situação, tipo do laudo) tinham `coluna_data: "USU_DATALT"` no catálogo, aplicando o filtro incremental de 60 dias em todo ciclo depois da 1ª carga. Só que são tabelas praticamente estáticas: confirmado no Sapiens que têm entre 3 e 16 linhas, com a última alteração real variando de **2014 a 2020** — ou seja, sempre fora da janela de 60 dias, em qualquer ciclo. **Corrigido**: `coluna_data` virou `None` nas 4 (`laudos_rma/bronze/tabelas.py`) — Bronze relê essas tabelas inteiras a cada ciclo, custo irrelevante (no máximo 16 linhas).

Causa raiz (2): depois do fix acima, `USU_TLAUCOR` ainda só trouxe 8 das 16 linhas (as outras 3 vieram completas). `USU_TLAUCOR` tinha `tem_codemp: True` (filtrando `USU_CODEMP = 1`) — confirmado no Sapiens (`SELECT USU_CODEMP, COUNT(*) ... GROUP BY`) que 8 linhas têm `USU_CODEMP = 1` e 8 têm `USU_CODEMP = 0` (marcador de "global", não lixo). É referência global igual as 3 irmãs (`USU_TLAUPRB`/`SIT`/`TIP`, todas `tem_codemp: False`). **Corrigido**: `tem_codemp` virou `False` também.

Causa raiz (3): depois dos 2 fixes acima, sobraram 30 divergências (6 + 24), todas ligadas a atividade do dia (20/07/2026). Comparando campo a campo, a diferença real estava em `APETRA`/`CODTRA`/`DATEMI` (e os 2 campos calculados em cima deles) — vindos de `E140NFV`/`E073TRA`, que são **tabelas compartilhadas com o Comercial** (mantidas pelo extrator do Comercial, não pelo do Laudos RMA). Rodar `laudos_rma.bronze.extrator` não atualiza essas duas. **Resolvido rodando `comercial.bronze.extrator`** também — não foi bug de catálogo, foi só lembrar que o Laudos RMA depende de tabelas de outra área.

**Resultado final**: conferência caiu de 35.534 para 1 linha (um laudo aberto no dia corrente, ainda "AGUARDANDO MOV DE ESTOQUE" — a Prata capturou um registro mais recente que o próprio legado, cujo ciclo de 15 min ainda não tinha rodado de novo; mesma tolerância de não-atomicidade já documentada no `DIM_CLIENTE`). `FAT_LAUDOS` considerado validado.

### `FAT_VENDAS_RMA` — causa da lentidão encontrada e corrigida (20/07/2026)

Legado (`vbivendas.py`, direto no Sapiens): 190s. Nossa 1ª versão (mesma lógica, lendo da Bronze): passou de 1h30 sem terminar, mesmo depois de confirmar índice (`IDX_E140IDE_PK`, `IDX_E085HCL_PK`, `IDX_E140PVD_PK`) e estatística atualizada (`DBMS_STATS.GATHER_TABLE_STATS`) em `E140NFV`, `E140IPV`, `E140IDE`, `E001TNS`. Não era nem índice nem estatística.

Causa raiz: `QTDMED` era calculado com uma **subquery correlacionada no SELECT**, reexecutada uma vez **por linha** do JOIN principal, antes do `GROUP BY` agrupar por mês/produto. O JOIN principal contra a Bronze produz **~210 mil linhas** (confirmado via `COUNT(*)` isolado) — ou seja, a subquery rodava ~210 mil vezes, mesmo o resultado final tendo só 1 linha por combinação de mês x produto (o grão real da tabela). Mesmo uma subquery individualmente rápida, multiplicada 210 mil vezes, facilmente passa de 1h30.

**Corrigido**: reescrita em 2 passos (`laudos_rma/prata/fat_vendas_rma.py`) — agrega vendas por mês x produto **uma vez** (CTE `VENDAS_MES_PRODUTO`), depois calcula a soma móvel de 6 meses com `SUM(...) OVER (PARTITION BY CODPRO ORDER BY MES RANGE BETWEEN INTERVAL '6' MONTH PRECEDING AND INTERVAL '1' MONTH PRECEDING)` em cima do agregado (bem menor que 210 mil linhas). O corte de `DATA_CORTE_LAUDOS` é aplicado só no final (filtrando quais mês/produto entram no resultado), igual o legado só cortava a linha externa — o cálculo de `QTDMED` de um mês de referência de janeiro/2023 precisa olhar meses anteriores a 2023, então a agregação em si não pode ter esse corte.

Mesmo princípio da correção da reincidência no `FAT_LAUDOS`: trocar "recalcular por linha" por "agregar uma vez + calcular por cima do agregado". **Validado**: testado na VM em 3,6s total (extração + carga), `conferencia_fat_vendas_rma.py` bateu com só 1 linha de diferença (venda do dia corrente ainda não refletida no legado — esperado).

### Conferências com colunas dinâmicas (não hardcoded)

`DIM_INDICE_RMA` (colunas do Excel não documentadas linha a linha no código legado) e `FAT_LAUDOS` (~75 colunas — risco real de erro de transcrição manual) usam uma técnica diferente das outras conferências do projeto: em vez de uma lista `COLUNAS` fixa, a conferência consulta `ALL_TAB_COLUMNS` dos dois lados em tempo de execução e compara a **interseção** das colunas (excluindo metadado técnico). As outras 3 tabelas desta área continuam com lista fixa, igual o padrão já usado no Comercial.

**Laudos RMA finalizado (21/07/2026).** As 3 dimensões de Excel (`DIM_RECLASSIF_DEFEITOS`, `DIM_RECLASSIF_PRODUTOS`, `DIM_INDICE_RMA`) testadas na VM depois de `FAT_VENDAS_RMA`/`FAT_LAUDOS` — conferência batendo nas 5. Área considerada fechada, mesmo critério do Comercial (ressalva: `USU_TLAUITE`/`USU_TLAUGER`/`USU_VZRASLAU` são tabelas Bronze compartilhadas com a Rastreabilidade — ver Regra 8 sobre dependência entre extratores de áreas diferentes).

---

## OPEX (21/07/2026, levantamento concluído)

Terceira área a migrar, mesmo processo do Comercial/Laudos RMA: analisar o legado (`aquario/opex/extract/`), decidir `DIM_`/`FAT_`, confirmar que a Bronze já tem tudo, só depois criar a Prata. Diferença desta área: o legado **nunca teve tabelas de dimensão separadas** — é 1 script/1 tabela só, já denormalizada.

### Tabela da Prata do OPEX

| Tabela nova          | Tabela legado            | Classificação | Origem (Bronze)                                               | Status                                                                                                                         |
| --------------------- | ------------------------- | ------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `FAT_ORCAMENTO_OPEX` | `USU_VBIAOPEX_ORCAMENTO` | Fato          | `USU_T650ORC`, `USU_T650CUS`, `E044CCU`, `E043PCM`, `R910USU` | ✅ **Validada (21/07/2026)** — testada na VM, conferência bateu 100% depois de isolar o resíduo de não-atomicidade (ver abaixo) |

**Decisão: 1 única tabela, sem separar em dimensões.** `vbiopex.py` (legado) faz `FULL OUTER JOIN` entre orçamento (`USU_T650ORC`) e realizado (`USU_T650CUS`), enriquecendo com descrição de centro de custo (`E044CCU`), plano de contas (`E043PCM`) e nome de dono/coordenador (`R910USU`, join duplo) — tudo já embutido no resultado, sem tabelas de apoio separadas no legado. Diferente do Comercial (7 scripts→7 tabelas, cada um já era uma entidade própria no legado), aqui não existe precedente de dimensão separada — criar `DIM_CENTRO_CUSTO`/`DIM_PLANO_CONTAS`/`DIM_USUARIO` agora seria redesenho de modelo estrela, fora do escopo desta fase (Regra da Fase 2 é replicar fielmente a arquitetura Bronze/Prata, não redesenhar o data model). Classificação **FATO**: tem `ORCADO`/`REALIZADO` mensurável por período (`COMP`) × centro de custo (`CC`) × despesa (`CDESP`).

**Nome escolhido**: `FAT_ORCAMENTO_OPEX` (sufixo `_OPEX`, mesmo padrão do `_RMA` no Laudos RMA) — schema `DW_PRATA` é compartilhado entre áreas, sufixo evita colisão futura com um eventual `FAT_ORCAMENTO` de outra área. Confirmado com o usuário em 21/07/2026.

**Cobertura da Bronze**: 100% — as 5 tabelas Oracle usadas por `vbiopex.py` já existem no catálogo `dw_aquario/opex/bronze/tabelas.py` e já rodam em produção (upsert/full incremental via `carregar_bronze()`/`upsert_cross_servidor()`). Nada precisa ser criado na Bronze para esta área. Auditoria do `tem_codfil` (Regra 6) já cobriu o OPEX em 17/07/2026 — nenhuma das 5 tabelas tem conceito de filial, então não há esse bug aqui.

**Mudança de arquitetura real para esta área**: o legado lê **direto do Sapiens Controladoria** (servidor separado, 172.16.0.123/dbprod) a cada execução. A Prata nova vai ler **só da `DW_BRONZE`** (Regra 2 da Fase 2 — "lê da Bronze, nunca da fonte direto") — a Bronze já faz essa ponte via `get_engine_controladoria()`/`get_engine_bronze()` (2 engines cross-servidor, sem DB LINK entre eles). Isso é a mudança estrutural desta migração: o script Prata do OPEX não vai mais precisar da engine de Controladoria, só da engine da Prata (mesmo padrão do `fat_metas.py` do Comercial).

**Ponto investigado (não é bug) — PK de `USU_T650CUS` diverge do JOIN legado**: o catálogo da Bronze (`opex/bronze/tabelas.py`) já sinalizava isso como pendência de investigação. PK real de `USU_T650CUS` tem 6 colunas (inclui `USU_CTAEMP`), mas o `JOIN` do `vbiopex.py` usa só 5 (sem `USU_CTAEMP`) para casar com `USU_T650ORC`. Analisado em 21/07/2026: **não é bug** — `ORCADO` (`T1.USU_ORCMES`) não é somado, só carregado como atributo agrupado (mesmo valor repetido a cada linha duplicada do `FULL OUTER JOIN`); `REALIZADO` é `SUM(T0.USU_SALMES)`, que agrega corretamente todas as linhas de `USU_T650CUS` com `CTAEMP` diferente para a mesma chave de 5 colunas, via `GROUP BY`. Replicando o mesmo `JOIN` de 5 colunas na Prata (Bronze guarda a granularidade real via PK de 6 colunas, mas a query da Prata decide o agrupamento, igual sempre foi no legado), o resultado fica idêntico ao legado — confirmar isso na conferência quando a tabela for construída.

**Particularidade mantida**: `CODEMP IN (1, 50)` (2 razões sociais do grupo Aquário, exceção já documentada em `opex/config/settings.py` — diferente do resto do projeto, que é sempre `CODEMP = 1`) e `USU_CODMPC = '801'` — filtros do legado, mantidos sem alteração.

**Tipo de carga proposto**: `full_reload` — mesmo motivo do legado e do `FAT_FATURAMENTO` do Comercial: `FULL OUTER JOIN` sem chave natural estável para upsert (a combinação de colunas do `GROUP BY` não é uma PK física de nenhum lado).

**Prata criada (21/07/2026)**: `dw_aquario/opex/prata/fat_orcamento_opex.py` (query idêntica à do legado, trocando as 5 fontes de `SAPIENS.*` na Controladoria pelas mesmas tabelas em `DW_BRONZE`, lendo via `get_engine_prata()` — não precisa mais de `get_engine_controladoria()` aqui) + `dw_aquario/opex/prata/tabelas.py` (catálogo, mesmo padrão do `comercial/prata/tabelas.py`) + `dw_aquario/conferencias/dw_prata/conferencia_fat_orcamento_opex.py` (MINUS dado a dado contra `BIAQUARIO.USU_VBIAOPEX_ORCAMENTO`, mesmo padrão do `conferencia_fat_faturamento.py`). Nenhuma coluna nova foi adicionada — as 15 colunas do legado (`EMP`, `COMP`, `CC`, `CDESP`, `ORCADO`, `REALIZADO`, `CCUSTO`, `TPCC`, `DESPESA`, `PROD`, `CODDONO`, `DONO`, `QUARTER`, `CODCOORD`, `COORD`) são as mesmas na Prata.

**Validada (21/07/2026)**: 1ª rodada da conferência (feita com o legado já um tempo sem rodar) bateu **26 divergências**, todas com a mesma assinatura: mesma chave dos dois lados, `REALIZADO` com valor na Prata e `NULL` no legado, só em `COMP` = mês corrente (julho/2026, ainda em aberto). Diferente das outras áreas, o legado do OPEX **não roda em ciclo automático de 2 em 2 min** (apesar de `opex/orquestrador.py` estar preparado para isso) — na prática o disparo é **manual** (`opex/gatilho_manual.py`), então o intervalo entre uma atualização do legado e outra pode ser bem maior que nas demais áreas, alargando a janela de não-atomicidade. Confirmado rodando o disparo manual do legado, seguido imediatamente de `opex.bronze.extrator` + `opex.prata.fat_orcamento_opex` + a conferência de novo: a divergência caiu de 26 para **1 linha** (mesma assinatura -- despesa lançada no Sapiens no intervalo de ~25s entre o fim do disparo manual do legado e o início da nossa extração). Mesmo mecanismo de não-atomicidade já documentado no `DIM_CLIENTE` e no `FAT_LAUDOS` -- não é bug de lógica, é o legado e a Prata lendo o Sapiens em instantes diferentes enquanto o mês está em aberto e despesas continuam sendo lançadas. `FAT_ORCAMENTO_OPEX` considerada validada.

**Gatilho manual/disparo/orquestrador ficam para a fase 3**, junto com as demais áreas.

**OPEX encerrado (21/07/2026).** Única tabela da área validada e considerada fechada, mesmo critério do Comercial.

---

## Rastreabilidade (21/07/2026, finalizada)

Quarta área a migrar, mesmo processo das anteriores. Igual o OPEX, o legado (`aquario/rastreabilidade/extract/vbirastreabilidade.py`) é **1 único script/tabela**, sem dimensão separada.

### Tabela da Prata da Rastreabilidade

| Tabela nova            | Tabela legado                     | Classificação | Origem (Bronze)                                                                                                                                                                          | Status                                                                                                                            |
| ------------------------ | -------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `FAT_RASTREABILIDADE` | `USU_VBIARAST_RASTREABILIDADE` | Fato          | `E140IPV`, `E140NFV`, `E085CLI`, `E090REP`, `E026RAM`, `E075PRO`, `E120IPD` (compartilhadas com o Comercial), `USU_T140QRC` (exclusiva), `USU_VZRASLAU` (compartilhada com o Laudos RMA) + `MetaMix.xlsx` (Excel, fora da Bronze) | ✅ **Validada (21/07/2026)** — testada na VM, conferência bateu 100% depois de atualizar os 3 extratores de Bronze dos quais esta tabela depende (ver abaixo) |

**Cobertura da Bronze: 100%, já estava pronta antes desta migração começar.** O catálogo `rastreabilidade/bronze/tabelas.py` já documentava (desde 14/07/2026) que só 1 tabela é exclusiva desta área (`USU_T140QRC` — log de geração de código de barras/QR, 2,7 milhões de linhas, a MAIOR tabela do projeto, maior que o `E120IPD` do Comercial); as outras 7 tabelas Oracle usadas pelo legado já são mantidas pelo `comercial/bronze/extrator.py`, e `USU_VZRASLAU` (view sem PK) já é mantida pelo `laudos_rma/bronze/extrator.py`. `tem_codfil` de `USU_T140QRC` já auditado e confirmado correto (`True`) na rodada de 17/07/2026. Nada precisou ser criado na Bronze.

**`MetaMix.xlsx` fora da Bronze**: mesma exceção já decidida pro Laudos RMA (07/07/2026) — arquivo Excel mantido manualmente pelo time de negócio, sem fonte Oracle equivalente. A Prata nova continua lendo o Excel direto e fazendo o merge em Python (`how="left"`), igual o legado.

**Corte de data**: legado já filtrava `DATEMI`/`USU_DATGER` `>= 01/01/2023` — mantido (Regra 2, mesmo caso do Laudos RMA). Constante nova: `DATA_CORTE_RASTREABILIDADE` em `rastreabilidade/config/settings.py`.

### Melhoria aplicada: JOIN modernizado para sintaxe ANSI

O legado escreve o JOIN no estilo antigo do Oracle (tabelas separadas por vírgula no `FROM` + condições de igualdade no `WHERE`, com o operador `(+)` emulando o `LEFT JOIN` de `USU_VZRASLAU`). Reescrito em `fat_rastreabilidade.py` como `INNER JOIN`/`LEFT JOIN` explícitos — tradução mecânica, mesmo plano de execução (o otimizador do Oracle trata as duas formas de forma idêntica), mesmo resultado. Ganho é só legibilidade/manutenção, não performance — mesmo tipo de limpeza segura já aplicada no `FAT_FATURAMENTO` (remoção do hint manual).

### Melhoria avaliada e **não** aplicada: carga incremental (upsert)

`USU_T140QRC` (a tabela-âncora do grão real desta fato) é insert-only ("log de geração", nunca é alterada — confirmado no catálogo da Bronze) e tem PK física real estável — a princípio, boa candidata a `upsert` incremental, mesmo padrão já usado em `FAT_VENDAS_RMA`/`FAT_LAUDOS` (Laudos RMA).

Avaliado e descartado por enquanto: a `FAT_RASTREABILIDADE` embute, junto de cada linha de bipagem, atributos **descritivos** de outras tabelas (nome/cidade/UF do cliente, nome do representante, descrição da região, descrição do produto, `MIX`/`ORIGEM` do Excel). O legado (`full_reload`) sempre relê essas tabelas por completo a cada ciclo, então toda linha histórica sempre mostra o valor **atual** desses cadastros. Um `upsert` que só toca a parte transacional (via PK do `USU_T140QRC`) deixaria essas colunas "congeladas" no valor de quando a linha foi inserida — se um cadastro mudar depois (ex.: correção de cidade de um cliente, reclassificação de `MIX` no Excel), o histórico não acompanharia, divergindo do legado.

Resolver isso direito exigiria resincronizar separadamente produto, cliente, representante+região e `MIX`/`ORIGEM` a cada ciclo (múltiplas passadas de `MERGE`/`UPDATE` em massa) — bem mais código e mais superfície pra esconder um bug sutil, sem ainda saber se o problema de performance é real. **Decisão consciente (21/07/2026): manter `full_reload`, medir o tempo real na VM primeiro.** Mesmo caso do `FAT_FATURAMENTO`: lá a causa de lentidão era só um índice faltando na Bronze, não a estratégia de carga — pode ser que aconteça o mesmo aqui. Fica registrado como candidato a otimização futura, só se o `full_reload` simples se mostrar realmente lento na prática.

### Validado (21/07/2026) — 3 rodadas de conferência, cada uma revelando uma dependência de Bronze diferente

Testado na VM: extração + carga de `USU_T140QRC` (Bronze), `FAT_RASTREABILIDADE` (Prata) e conferência contra o legado. Tempo real da 1ª carga: 42,9s de extração + 106,8s de carga = **159,2s no total**, para **1.258.194 linhas** (bem menor que o universo de 2,7 milhões da fonte, depois dos filtros de `CODDEP`/tipo de operação/corte de data). Decisão de manter `full_reload` (ver seção "Melhoria avaliada e não aplicada" acima) confirmada como correta — não foi preciso redesenhar nada.

A conferência revelou 3 causas de divergência em sequência, todas resolvidas sem tocar em nenhuma lógica de negócio:

1. **226 linhas — `E085CLI` desatualizada na Bronze.** Nome de um cliente (`WTB COMÉRCIO DE PECAS E ACESSORIOS LTDA` na Prata x `WTB COMÉRCIO DE PEÇAS E ACESSÓRIOS LTDA` no legado) divergia só na acentuação -- cadastro tinha sido corrigido no Sapiens depois da última vez que `comercial.bronze.extrator` releu `E085CLI` por completo. Resolvido rodando `comercial.bronze.extrator` de novo.
2. **20 linhas — resíduo de não-atomicidade.** Depois do fix acima, sobrou um gap de contagem (1.258.214 legado x 1.258.194 Prata) -- bipagens muito recentes que o legado (rodando ao vivo) capturou e a Bronze ainda não tinha. Resolvido rodando os extratores e a Prata próximos no tempo -- o gap de contagem fechou (1.258.214 = 1.258.214).
3. **130 linhas — `USU_VZRASLAU` desatualizada na Bronze.** Todas as colunas vindas de `PVD` (fornecedor, pedido, documento, processo, datas de embarque/previsão/chegada/desembaraço) nulas na Prata, preenchidas no legado, só em bipagens muito recentes (dia anterior). Causa: `USU_VZRASLAU` é mantida pelo `laudos_rma.bronze.extrator`, não pelo da Rastreabilidade -- não tinha sido rodado nesta rodada de testes. Resolvido rodando `laudos_rma.bronze.extrator`.

**Resultado final**: depois dos 3 extratores de Bronze atualizados (`comercial`, `rastreabilidade`, `laudos_rma`) e a Prata reconstruída, a conferência bateu **0 divergências** dos dois lados. `FAT_RASTREABILIDADE` considerada validada.

### Ponto importante para a fase 3 (orquestrador) — ver também Regra 8

`FAT_RASTREABILIDADE` depende de **3 extratores de Bronze diferentes**, mantidos por 3 áreas distintas: `comercial.bronze.extrator` (`E140IPV`, `E140NFV`, `E085CLI`, `E090REP`, `E026RAM`, `E075PRO`, `E120IPD`), `rastreabilidade.bronze.extrator` (`USU_T140QRC`, a única exclusiva) e `laudos_rma.bronze.extrator` (`USU_VZRASLAU`). Rodar só o extrator da própria área **não é suficiente** para a Prata da Rastreabilidade ficar correta -- as 3 causas de divergência desta validação vieram exatamente disso. Quando o orquestrador definitivo da Rastreabilidade for desenhado (fase 3), ele precisa garantir que os 3 extratores estejam em dia antes de rodar `fat_rastreabilidade.py` -- não necessariamente rodando os 3 dentro do próprio ciclo da Rastreabilidade (isso duplicaria trabalho já feito pelos orquestradores das outras áreas), mas pelo menos confirmando que os ciclos do Comercial e do Laudos RMA já rodaram recentemente o suficiente.

**Rastreabilidade encerrada (21/07/2026).** Única tabela da área validada e considerada fechada, mesmo critério do Comercial e do OPEX.

---

## Produção (21/07/2026, Prata criada)

Quinta área a migrar, mesmo processo das anteriores: analisar os 7 scripts legados (`aquario/producao/extract/`), decidir `DIM_`/`FAT_`, confirmar que a Bronze já tem tudo, só depois criar a Prata. Diferente do OPEX/Rastreabilidade (1 tabela só), a Produção tem 7 tabelas — mais parecida em escala com o Comercial.

### Tabelas da Prata da Produção

| Tabela nova | Tabela legado | Classificação | Carga | Status |
|---|---|---|---|---|
| `DIM_PRODUTO_PRODUCAO` | `USU_VBIAPROD_PRODUTO` | Dimensão | upsert | 🔶 Pronta — aguardando teste na VM |
| `DIM_CENTRO_CUSTO_PRODUCAO` | `USU_VBIAPROD_CENTROCUSTO` | Dimensão | upsert | 🔶 2 correções aplicadas (21-22/07/2026 — chave de merge + `NULL` duplicando linha, ver seção própria) — precisa dropar a tabela na VM e retestar do zero |
| `DIM_CUSTO_PADRAO_PRODUCAO` | `USU_VBIAPROD_CUSTO_PADRAO` | Dimensão | full_reload (Excel) | 🔶 Pronta — aguardando teste na VM |
| `FAT_PARADAS_PRODUCAO` | `USU_VBIAPROD_PARADAS` | Fato | full_reload | 🔶 Pronta — aguardando teste na VM |
| `FAT_CUSTO_CC_PRODUCAO` | `USU_VBIAPROD_CUSTOCC` | Fato | full_reload | 🔶 Pronta — aguardando teste na VM |
| `FAT_UTILIZACAO_META_PRODUCAO` | `USU_VBIAPROD_UTILIZACAO_META` | Fato | full_reload (Excel) | 🔶 Pronta — aguardando teste na VM |
| `FAT_DESEMPENHO_PRODUCAO` | `USU_VBIAPROD_DESEMPENHO` | Fato (central) | full_reload | 🔶 Pronta — aguardando teste na VM |

**Sufixo `_PRODUCAO` em todas** — já existe `DIM_PRODUTO` no Comercial, com campos completamente diferentes (a versão da Produção tem `CODORI`, `CODAGE`, `CURABC`, `DEPPAD`, específicos de manufatura); sem o sufixo colidiria no schema `DW_PRATA` compartilhado.

**Cobertura da Bronze: 100%, já estava pronta.** O catálogo `producao/bronze/tabelas.py` já tinha as 16 tabelas exclusivas documentadas (desde 08/07/2026), incluindo a auditoria de `tem_codfil` de 17/07/2026 (4 correções: `E210MVP`, `E621MTC`, `E900COP`, `E930MPR`). Nada precisou ser criado na Bronze.

**Dependência de outro extrator (Regra 8)**: `DIM_PRODUTO_PRODUCAO` e o bloco CONSUMO de `FAT_DESEMPENHO_PRODUCAO` usam `E012FAM`/`E013AGP`/`E075DER`/`E075PRO` — tabelas mantidas pelo `comercial.bronze.extrator`, não pelo da Produção. Precisa dele rodado em dia antes de validar essas duas tabelas.

### Corte de data: `01/01/2021` em TODAS as tabelas FATO — decisão explícita, diferente da Regra 2 padrão

O legado da Produção usava `01/01/2018` (`DATA_INICIO_HISTORICO`) em `FAT_PARADAS_PRODUCAO` e nos blocos DESEMPENHO/CONSUMO de `FAT_DESEMPENHO_PRODUCAO`, e **nenhum corte** em `FAT_CUSTO_CC_PRODUCAO` e no bloco CUSTO_CC de `FAT_DESEMPENHO_PRODUCAO`. **Confirmado com o usuário em 21/07/2026: `01/01/2021` em TODAS** — inclusive nas duas que nunca tiveram corte nenhum no legado. Isso é uma exceção deliberada à Regra 2 padrão da Fase 2 (que só aplicaria corte novo onde o legado não tinha nenhum, e manteria 2018 onde já existia um corte) — aqui foi pedido explicitamente o padrão único de 2021 pra toda a área, mesmo custando janela de histórico a mais (2018-2020) e volume nas duas tabelas que nunca foram cortadas antes. Constante nova: `DATA_CORTE_PRODUCAO = "01/01/2021"` em `producao/config/settings.py`.

**Consequência nas conferências**: como o corte muda o volume visível (Prata sempre vai ter MENOS linhas que o legado nas 4 tabelas FATO), as conferências dessas 4 tabelas (`fat_paradas_producao`, `fat_custo_cc_producao`, `fat_utilizacao_meta_producao`, `fat_desempenho_producao`) aplicam o MESMO filtro de `01/01/2021` no lado do legado antes de comparar — senão a divergência de contagem apareceria sempre, mascarando uma divergência de conteúdo de verdade. O que valida é se os dados de 2021 em diante batem 100% dos dois lados; o legado ter mais linhas (histórico anterior a 2021) é esperado, não é bug.

### Bug encontrado e corrigido: `DIM_CENTRO_CUSTO_PRODUCAO` descartava operações duplicadas (21/07/2026)

Primeira rodada da conferência bateu **9 divergências** (mesma contagem: 133=133, mas conteúdo diferente em 9 grupos). Todas as 9 tinham o mesmo padrão: mesma `CODCCU`+`CODETG`+`CODCRE`, mas `CODOPR`/`DESOPR`/`ABROPR` diferentes (ex.: Prata `251302 CORTE 249MM` x legado `251301 CORTE`).

Causa raiz: a chave de merge do legado (`chaves_merge = [CODCCU, CODETG, CODCRE]`, sem `CODOPR`) — copiada fielmente pra Prata — não reflete a granularidade real da query, que é por `E720OPR` (a tabela-âncora do `FROM`, PK real `CODEMP+CODOPR`). Quando mais de uma operação existe pro mesmo centro de custo/estágio/centro de recurso, o `MERGE` só guarda 1 por grupo — tanto no legado quanto na Prata, cada lado "sorteando" uma arbitrariamente (não existe critério de desempate real: `coluna_ordem="CODCCU ASC"` não desempata nada dentro de um grupo, porque `CODCCU` já é constante ali).

**Confirmado com consulta direta em `E720OPR`** (Sapiens e Bronze, idênticas — não é problema de Bronze desatualizada): não são só os 9 casos visíveis — existem **21 grupos reais** com mais de 1 operação (a maioria "escondida" porque os dois lados coincidentemente sortearam a mesma operação vencedora). O pior caso, `CCU=4200/ETG=71/CRE=7101` ("Montagem Conversores"), tem **23 operações diferentes** reduzidas a 1 registro só.

**Corrigido**: `CODOPR` incluído na `chaves_merge` (`dim_centro_custo_producao.py` e catálogo `tabelas.py`) — a tabela passa de ~133 para **~194 linhas** (133 − 21 grupos truncados + 82 operações reais desses mesmos grupos). Não é inflação de dado, é a granularidade correta que sempre existiu em `E720OPR` e nunca apareceu no Power BI (nem no legado).

**Consequência pra conferência**: como o legado tem a MESMA limitação (não é fonte de verdade nesse ponto específico), o padrão de conferência do projeto (MINUS simétrico, esperando 0 dos dois lados) não se aplica aqui — vai sempre acusar "só na Prata" com as ~61 linhas a mais, por design. `conferencia_dim_centro_custo_producao.py` foi reescrita com 2 testes diferentes:

1. **Regressão contra o legado** (`só no legado` deve ser 0): garante que a Prata não perdeu nada que o legado já tinha — é sempre um superconjunto, nunca um subconjunto.
2. **Completude contra a fonte de verdade** (query de referência reexecutada direto na Bronze, mesma lógica do script de carga): garante que a carga (upsert, conversão de tipo) preservou exatamente o que a query deveria trazer — pega bug de carga, não de lógica de negócio (essa parte já foi validada à parte, direto no Sapiens).

Essa é a **primeira exceção real à Regra 3** da Fase 2 ("resultado idêntico ao legado, 0 divergências") — registrado aqui porque pode se repetir: qualquer tabela migrada cuja chave de merge do legado não capture a granularidade real da query-âncora tem o mesmo risco. Vale conferir isso cedo (antes de rodar a conferência padrão) em áreas futuras que também usem `upsert` com chave composta.

### 2º bug encontrado na mesma tabela: `NULL` na chave de merge duplica linha a cada execução (22/07/2026)

Depois da correção acima, o reteste na VM mostrou um problema novo: `Linhas na Prata: 204` contra `Linhas na query de referência (Bronze): 195` — 9 linhas a mais na Prata, mesmo com o **Teste 2** (completude) acusando só 1 divergência (`só na referência`). A aritmética não fechava: se a Prata tem 204 linhas físicas mas só diverge em 1 da referência (195 linhas), sobra a conclusão de que a Prata tinha **linhas fisicamente duplicadas** (mesma chave completa, 2 cópias).

Diagnóstico direto na VM confirmou: **10 grupos** (`SELECT CODCCU, CODETG, CODCRE, CODOPR, COUNT(*) ... HAVING COUNT(*) > 1`) apareceram com `CODOPR` **vazio/`NULL`** e `COUNT(*) = 2`. São exatamente 10 dos 11 códigos da lista hardcoded do 2º bloco do `UNION ALL` (centros de recurso sem estágio) — o 11º (`CODCRE='2540'`) tem uma operação real vinculada (`254001`), por isso não duplicou.

**Causa raiz**: o 2º bloco faz `LEFT JOIN` de `E720OPR` — pra esses 10 códigos de `CODCRE`, não existe nenhuma operação vinculada, então `OPR.CODOPR` vem `NULL`. Como `CODOPR` passou a fazer parte da `chaves_merge` (correção anterior), e em SQL `NULL = NULL` **nunca** é verdadeiro, a condição `ON` do `MERGE` nunca reconhecia a linha já existente como "a mesma" — cada execução do script inseria uma cópia nova, silenciosamente, pra sempre (bug que cresceria a cada ciclo se não fosse pego agora).

**Corrigido**: `NVL(OPR.CODOPR, ' ')` no 2º bloco de `dim_centro_custo_producao.py` — mesma convenção que a própria query já usava pra `CODETG`/`DESETG`/`ABRETG` nesse mesmo bloco (`0 AS CODETG`, `' ' AS DESETG` etc., pra representar "não se aplica"). A conferência (`conferencia_dim_centro_custo_producao.py`) também precisou normalizar `CODOPR` com `NVL(CODOPR, ' ')` na lista de colunas comparadas — sem isso, o legado (que guarda `NULL` de verdade, nunca teve esse problema porque `CODOPR` nunca fez parte da chave dele) sempre divergiria da Prata (que agora guarda `' '`) nesses 10 registros, um falso positivo.

**Necessário na VM**: como `upsert()` nunca remove linha, as duplicatas já criadas pelas execuções anteriores continuam na tabela até um `DROP TABLE DW_PRATA.DIM_CENTRO_CUSTO_PRODUCAO` + recarga do zero — só rodar o script de novo (sem dropar) não limpa o que já duplicou.

**Lição geral, vale pra qualquer área futura**: nenhuma coluna usada em `chaves_merge` pode ser nullable sem tratamento (`NVL`/`COALESCE`) antes — coluna com `NULL` numa chave de merge faz o `MERGE` duplicar em vez de atualizar, silenciosamente, todo ciclo. Isso é particularmente fácil de esquecer quando a chave inclui uma coluna vinda de `LEFT JOIN` (que é exatamente onde `NULL` aparece com mais frequência).

### 3º achado na mesma tabela: `CODCRE='2540'` duplicado no próprio legado, `NULL` x `' '` mascarando (22/07/2026)

Depois do fix (2), a tabela foi dropada e recarregada do zero: `195` linhas extraídas, mas só `194` salvas fisicamente (o `upsert()` dedupa dentro da própria carga quando duas linhas da mesma extração compartilham a chave completa). A conferência confirmou: `Teste 1 [OK]` (nada perdido do legado), mas `Teste 2` mostrou 1 divergência (`só na referência`) — sempre a mesma linha, `CODCRE='2540'`/`CODOPR='254001'`.

Investigado com uma consulta rotulando a origem de cada linha (`'BLOCO1'`/`'BLOCO2'`): confirmado que **`CODCRE='2540'` produz 2 linhas com a MESMA chave completa** (`CODCCU`, `CODETG=0`, `CODCRE`, `CODOPR`) — uma vinda do bloco 1 (JOIN natural, porque essa operação já tem `CODETG=0` de verdade no Sapiens) e outra do bloco 2 (lista hardcoded do legado, que já incluía `2540` mesmo sem precisar — a operação já tinha cobertura natural). As duas descrevem o **mesmo fato real**, mas com uma diferença cosmética: `DESETG`/`ABRETG` vêm `NULL` no bloco 1 (o `LEFT JOIN` com `E093ETG` não acha nada pra `CODETG=0`) e `' '` (espaço, hardcoded) no bloco 2 — visualmente idênticos numa tela, mas `NULL ≠ ' '` numa comparação exata. A Prata (com o `MERGE` deduplicando pela chave) guardou 1 das 2 versões; a query de referência (sem dedup, propositalmente, pra pegar bug de carga) contava as 2 como registros distintos.

**Não é bug**: é uma redundância que já existia na lista hardcoded do legado (incluir `2540`, que nunca precisou da lista pra ter estágio, já era coberto pelo bloco 1) — só nunca apareceu porque a chave de merge antiga (sem `CODOPR`) escondia isso, igual escondeu as outras 21 duplicações. **Corrigido só na conferência** (não na carga -- `DESETG`/`ABRETG` não fazem parte da `chaves_merge`, então isso nunca causou duplicação de linha, só uma diferença cosmética de comparação): `NVL(DESETG, ' ')` e `NVL(ABRETG, ' ')` adicionados à lista de colunas comparadas em `conferencia_dim_centro_custo_producao.py`, mesmo princípio já usado pro `CODOPR`.

**Não precisa recarregar a Prata de novo por causa deste achado** — só a conferência mudou (comparação, não carga). Rodar `conferencia_dim_centro_custo_producao.py` de novo deve fechar os 2 testes em `[OK]`.

### Ponto em aberto resolvido: `DIM_CUSTO_PADRAO_PRODUCAO` é dimensão, não fato

`USU_VBIAPROD_CUSTO_PADRAO` (legado) não tem nenhuma coluna de período — só `CODEMPRESA`, `PRODUTO`, `CUSTO_PADRAO`. Antes de classificar, consultamos o legado diretamente: `324 linhas = 324 produtos distintos`, sem nenhuma duplicidade. Confirma que é 1 valor fixo por produto (atributo atual, sem grão de tempo) — `DIM_CUSTO_PADRAO_PRODUCAO`, sem corte de data (Regra 2 — dimensão nunca corta).

### `FAT_DESEMPENHO_PRODUCAO` — fato central, maior risco da área

UNION ALL de 4 naturezas diferentes (`TIPTAB` 1-4: apontamento de processo, consumo de matéria-prima, paradas, custo orçado/realizado), mesmo padrão de denormalização do `FAT_FATURAMENTO` no Comercial. Tem 3 subqueries correlacionadas no bloco DESEMPENHO (mesmo padrão que causou o problema de 1h30 no `FAT_VENDAS_RMA` do Laudos RMA), rodando sobre `E900EOQ` — provavelmente a maior tabela fonte da área. **Decisão: construir fiel ao legado primeiro (a sintaxe já é `JOIN` ANSI moderno em todo o legado da Produção, nada pra modernizar), medir o tempo real na VM, e só depois avaliar redesenho se realmente for lento** — mesma régua conservadora já usada no `FAT_FATURAMENTO` e na `FAT_RASTREABILIDADE`.

Conferência usa colunas dinâmicas (via `ALL_TAB_COLUMNS`, não lista hardcoded) — mesma técnica do `FAT_LAUDOS` (Laudos RMA), ~37 colunas, risco real de erro de transcrição manual numa lista tão grande.

**Observação sobre comentário desatualizado no legado**: o docstring de `vbidesempenho.py` justificava `full_reload` citando "`Ds_Prazo`... laudos em aberto mudam a qualquer ciclo" — terminologia do Laudos RMA, não da Produção (parece um comentário copiado do template errado durante o desenvolvimento original do legado). Não é bug funcional, só comentário — corrigido no `fat_desempenho_producao.py` novo com a justificativa real (UNION ALL de 4 naturezas sem chave única comum, mesmo motivo do `FAT_FATURAMENTO`).

**Próximo passo**: rodar `comercial.bronze.extrator` (dependência) + `producao.bronze.extrator` na VM, depois as 7 tabelas da Prata (`producao.prata.dim_produto_producao`, `dim_centro_custo_producao`, `dim_custo_padrao_producao`, `fat_paradas_producao`, `fat_custo_cc_producao`, `fat_utilizacao_meta_producao`, `fat_desempenho_producao`), e por fim as 7 conferências correspondentes em `conferencias.dw_prata` (precisa do `GRANT SELECT` em cada tabela legada equivalente, se ainda não existir).

---

## Regras de negócio fixas da Fase 2

1. **Nomenclatura**: `FAT_`/`DIM_` + nome da entidade, tudo maiúsculo. Fato = tem medida quantificável por período/dimensão (ex.: faturamento, meta). Dimensão = entidade descritiva (cliente, produto, representante), mesmo carregando algum atributo agregado.
2. **Corte de data**: `01/01/2021` pra frente, em toda tabela **FATO** com grão de data, de todas as áreas. **Dimensão nunca tem corte** (sempre o universo completo e atual das entidades — ex.: todo cliente cadastrado aparece em `DIM_CLIENTE`, independente de quando foi cadastrado). Esse corte só muda o que aparece no Power BI se a área/tabela **não** já tivesse um corte parecido no legado — isso é conferido tabela por tabela antes de aplicar, exatamente pra não mudar resultado sem avisar.
3. **Resultado idêntico ao legado é obrigatório**: cada tabela só é considerada pronta depois de uma conferência formal (dado a dado, não só contagem de linhas) contra a tabela correspondente no schema legado (`BIAQUARIO`). Ver seção "Validação" abaixo.
4. **Metadado técnico — `DW_DATA_INGESTAO` (Bronze) / `DW_DATA_PROCESSAMENTO` (Prata)**: toda tabela, nas duas camadas, ganha essa coluna automaticamente, registrando quando aquela linha foi gravada/atualizada pela última vez. Implementado de forma centralizada no `core/loader.py` — nenhum script de área precisa se preocupar com isso, é automático em toda escrita. Nomes diferentes por camada porque a ação é diferente (Bronze ingere, Prata processa).
5. **Índice comum (não PK) na chave de merge**: toda tabela nova (Bronze ou Prata) já nasce com índice, criado automaticamente no momento da criação da tabela — não precisa de retrofit depois. É índice comum, não constraint de PK (performance de busca praticamente igual, mas não trava a criação se existir alguma duplicata). Tabelas `full_reload` (como `FAT_FATURAMENTO`) não criam índice automático — se precisar, é caso a caso.
6. **`tem_codfil` na Bronze: só `True` se o(s) script(s) legado(s) fixarem a filial explicitamente** (ex.: `AND X.CODFIL = 1`). Bug real encontrado em 17/07/2026: 10 tabelas do catálogo do Comercial (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`, `E085HCL`, `E140IDE`, `E140PVD`) estavam com `tem_codfil: True` sem nenhum script legado realmente restringir filial nos JOINs que as usam — a maioria só filtra `CODEMP` (empresa), ou casa `CODFIL` dinamicamente com a filial da própria linha (`X.CODFIL = Y.CODFIL`), nunca fixando `= 1`. A Bronze filtrada silenciosamente descartava registros de outras filiais, e isso só apareceu na conferência dado-a-dado — contagem de linhas não pega esse tipo de erro. **Regra pra qualquer área nova**: antes de marcar uma tabela do catálogo Bronze como `tem_codfil: True`, confirmar no script legado (JOIN e WHERE) que a filial é fixada em `1` ali — se for casamento dinâmico ou não houver filtro de filial nenhum, é `tem_codfil: False` (Bronze traz o universo completo; quem decide o escopo de filial é a query consumidora na Prata, igual o legado sempre fez). Ver observação de `E140NFV` em `comercial/bronze/tabelas.py` para o caso completo investigado. **Auditoria estendida a todas as áreas em 17/07/2026** — ver seção "Correção do `tem_codfil` nas demais áreas da Bronze" logo abaixo: mais 9 tabelas corrigidas (Estoque, Produção, Laudos RMA), 2 confirmadas corretas como estavam (Expedição, Rastreabilidade).
7. **Nova coluna em tabela de origem (Sapiens) precisa ser avisada precisamente, sempre — combinado com o usuário em 20/07/2026.** Qualquer inclusão de coluna em qualquer tabela do Sapiens usada pelo projeto (em qualquer área) precisa ser informada (nome da tabela + nome da coluna) assim que o usuário souber, mesmo que a coluna ainda não vá ser usada em nenhuma Prata. Motivo: tabelas com carga `upsert` (MERGE incremental) já existem no Oracle com estrutura fixa — se o Sapiens ganha uma coluna nova e a Bronze não é atualizada primeiro, o **próximo ciclo incremental quebra com `ORA-00904`** (coluna referenciada no MERGE não existe na tabela de destino), porque `upsert()` monta o SQL dinamicamente a partir das colunas do DataFrame extraído (`SELECT *`), não da estrutura antiga da tabela Oracle. Tabelas `full_reload`/`full_reload_streaming` não têm esse problema (tabela é dropada e recriada do zero a cada ciclo, a coluna nova entra sozinha) — mas o aviso vale igual, pra manter o catálogo e a documentação em dia. Ver seção "Procedimento: nova coluna em tabela de origem" logo abaixo para o passo a passo.
8. **Tabela de Prata que consome tabela Bronze compartilhada com outra área depende do extrator DESSA outra área também, não só do próprio.** Cada catálogo de Bronze (`<area>/bronze/tabelas.py`) só declara e mantém as tabelas que aquela área realmente extrai — uma tabela usada por 2+ áreas (ex.: `E085CLI`/`E140IPV`/etc. do Comercial, reaproveitadas por Rastreabilidade e Laudos RMA; `USU_VZRASLAU` do Laudos RMA, reaproveitada por Rastreabilidade; `E044CCU`/`R910USU`, escritas tanto pela Produção/Laudos RMA quanto pelo OPEX) só fica atualizada quando o extrator DONO dela roda — rodar o extrator da própria área nunca é suficiente sozinho. Caso real (21/07/2026): a validação de `FAT_RASTREABILIDADE` só bateu 100% depois de rodar `comercial.bronze.extrator` (pra `E085CLI`) e `laudos_rma.bronze.extrator` (pra `USU_VZRASLAU`) além do `rastreabilidade.bronze.extrator` — rodar só este último deixava colunas desatualizadas/nulas vindas das outras 2 áreas. **Regra pra qualquer área nova**: antes de validar (ou de desenhar o orquestrador na fase 3) uma tabela de Prata, listar TODAS as tabelas Bronze que a query usa e conferir, pra cada uma, qual área é a dona (ver "TABELAS COMPARTILHADAS" nos catálogos de Bronze) — o orquestrador final precisa garantir que o ciclo de todas elas já rodou recentemente, não só o da própria área.

---

## Procedimento: nova coluna em tabela de origem (Sapiens)

Sempre que o time de negócio incluir uma coluna nova em qualquer tabela do Sapiens usada pelo projeto (Regra 7 acima):

1. **Confirmar se a tabela é usada em algum catálogo da Bronze** (`<area>/bronze/tabelas.py`, em qualquer uma das 7 áreas). Se a tabela não aparecer em nenhum catálogo, não precisa fazer nada agora — não extraímos ela (caso real: `USU_TANYMKTPED`, verificado em 20/07/2026, não usada em nenhuma área, atual ou legado).

2. **Se a tabela for usada e a estratégia de carga for `upsert` (incremental)**: a coluna precisa existir na Bronze **antes** do próximo ciclo, senão o `MERGE` quebra com `ORA-00904`. Passo a passo:

    ```sql
    -- a) Descobrir o tipo exato da coluna nova no Sapiens
    SELECT column_name, data_type, data_length, data_precision, data_scale
    FROM ALL_TAB_COLUMNS
    WHERE owner = 'SAPIENS' AND table_name = '<TABELA>' AND column_name = '<COLUNA>';

    -- b) Adicionar a mesma coluna na Bronze, com o mesmo tipo
    --    (sem NOT NULL -- linhas já existentes ficam NULL nessa coluna, esperado)
    ALTER TABLE DW_BRONZE.<TABELA> ADD (<COLUNA> <TIPO_IGUAL_AO_SAPIENS>);
    ```

3. **Se a estratégia for `full_reload`/`full_reload_streaming`**: não precisa de `ALTER TABLE` — a tabela é dropada e recriada do zero no próximo ciclo, a coluna nova entra sozinha (o `SELECT *` da extração já traz ela). Mesmo assim, o aviso continua valendo — mantém o catálogo com contexto de quando/por que a coluna apareceu.

4. **A coluna nova só aparece na Prata se algum script `prata/<tabela>.py` referenciar ela explicitamente no `SELECT`** — Bronze é cópia crua (toda coluna via `SELECT *`), Prata é sempre um `SELECT` deliberado com lista de colunas explícita. Incluir na Prata é decisão de negócio separada, feita quando fizer sentido usar o campo — não é automático só porque a coluna existe na Bronze.

---

## Correção do `tem_codfil` nas demais áreas da Bronze (17/07/2026)

Depois de fechar `DIM_CLIENTE` no Comercial, foi feita uma auditoria completa do mesmo bug (Regra 6) nas outras 6 áreas da Bronze (Estoque, Expedição, Produção, Laudos RMA, Rastreabilidade, OPEX) — nenhuma delas tinha passado ainda por essa checagem, porque a Prata dessas áreas ainda não começou (só a Bronze existe hoje). Cada tabela com `tem_codfil: True` no catálogo foi confrontada com o JOIN/WHERE real do script legado correspondente (lido do histórico do Git). Resultado: **9 tabelas corrigidas, 2 confirmadas corretas como já estavam.**

### Tabelas corrigidas (mesmo bug do Comercial — `tem_codfil: True` → `False`)

| Área       | Tabela         | Como era                                                              | Como ficou                                                                                                                                                                                  |
| ---------- | -------------- | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Estoque    | `E420IPO`      | `tem_codfil: True` — Bronze descartava itens de OC de filiais ≠ 1     | `tem_codfil: False` — `vbicompras.py` legado não tem nenhum filtro de `CODEMP`/`CODFIL` no `WHERE`; `CODFIL` só aparece no JOIN com `E420OCP` (`T0.CODFIL = T1.CODFIL`, casamento dinâmico) |
| Estoque    | `E420OCP`      | idem acima                                                            | idem acima — mesmo motivo, mesmo JOIN dinâmico                                                                                                                                              |
| Produção   | `E210MVP`      | `tem_codfil: True` — Bronze descartava movimentação de outras filiais | `tem_codfil: False` — bloco CONSUMO de `vbidesempenho.py` nunca referencia `CODFIL` desta tabela em nenhum JOIN/WHERE                                                                       |
| Produção   | `E621MTC`      | `tem_codfil: True`                                                    | `tem_codfil: False` — usada em 2 pontos de `vbidesempenho.py` (subconsulta `TAXREA` e bloco CUSTO_CC), nenhum filtra `CODFIL` — PK real nem inclui `CODFIL`                                 |
| Produção   | `E900COP`      | `tem_codfil: True`                                                    | `tem_codfil: False` — `vbidesempenho.py` junta por `CODEMP+CODORI+NUMORP` em 2 blocos, nunca por `CODFIL`                                                                                   |
| Produção   | `E930MPR`      | `tem_codfil: True`                                                    | `tem_codfil: False` — bloco PARADAS de `vbidesempenho.py` não filtra `CODFIL` nem no `WHERE` nem nos JOINs                                                                                  |
| Laudos RMA | `USU_TLAUITE`  | `tem_codfil: True`                                                    | `tem_codfil: False` — `vbilaudos.py` não tem filtro de `USU_CODFIL` no `WHERE`; só casamento dinâmico nos JOINs (`T0.USU_CODFIL = T1.USU_CODFIL`, `T0.USU_CODFIL = T15.FILNFV`)             |
| Laudos RMA | `USU_TLAUGER`  | `tem_codfil: True`                                                    | `tem_codfil: False` — mesmo motivo do `USU_TLAUITE`                                                                                                                                         |
| Laudos RMA | `USU_VZRASLAU` | `tem_codfil: True`                                                    | `tem_codfil: False` — casamento dinâmico dos dois lados que a consomem (`vbilaudos.py` e `vbirastreabilidade.py`); quem fixa filial é sempre a query consumidora, nunca esta view           |

Todas as 9 correções seguem exatamente o padrão já documentado na Regra 6: o legado nunca fixava a filial em `1` para essas tabelas — ou não filtrava nada, ou casava dinamicamente com a filial da linha relacionada. A Bronze com `tem_codfil: True` estava descartando silenciosamente dados de filiais diferentes de 1, o mesmo mecanismo do bug já corrigido no Comercial.

### Tabelas confirmadas corretas como estavam (`tem_codfil: True` mantido)

| Área            | Tabela        | Por que está correto                                                                                                                                                            |
| --------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Expedição       | `USU_V120EST` | `vbiexpedicao.py` fixa `PED.CODFIL = 1` no `WHERE` da tabela-âncora (`E120PED`); o JOIN dinâmico (`EST.CODFIL = PED.CODFIL`) fica transitivamente restrito a filial 1           |
| Rastreabilidade | `USU_T140QRC` | `vbirastreabilidade.py` fixa `IPV.CODFIL = 1` no `WHERE` da tabela-âncora (`E140IPV`); o JOIN dinâmico (`IPV.CODFIL = QRC.USU_CODFIL`) fica transitivamente restrito a filial 1 |

Padrão geral que emergiu: `tem_codfil: True` só está correto quando a **tabela-âncora** da query (a que dá nome ao `FROM` principal) já fixa a filial no `WHERE` — nesse caso, qualquer JOIN dinâmico a partir dela herda essa restrição. Quando não existe esse fixador em nenhum lugar da cadeia de JOINs, `tem_codfil` tem que ser `False`.

### Conferência da Bronze reescrita nas 6 áreas

O mesmo furo estrutural do `conferencia_comercial.py` (contagem tautológica — Sapiens e Bronze comparados com o mesmo filtro do catálogo, nunca capaz de pegar um `tem_codfil` errado; e só `COUNT(*)`, nunca valor) existia nas 6 conferências das outras áreas. Todas foram reescritas no mesmo padrão:

- Contagem "oficial" (escopo do catálogo) + contagem do Sapiens **sem filtro de filial**, lado a lado, com `ALERTA` visível quando divergem (sinal pra revisão humana, não decide OK/DIVERGENTE sozinho).
- Checagem de **conteúdo** nova (`--conteudo NOME_TABELA`): MINUS bidirecional em todas as colunas reais (via `ALL_TAB_COLUMNS`), sob demanda por tabela.
- Correção lateral: as versões antigas de Expedição/Laudos RMA quebrariam (`TypeError`) ao tentar conferir `USU_V120EST`/`USU_VZRASLAU` (tabelas sem PK física) usando `montar_query_pks()` — as novas versões usam `montar_query()`/`montar_query_contagem()` (que não dependem de PK) pra essas duas tabelas específicas, sem precisar pular nada.
- OPEX manteve a particularidade de 2 engines (Controladoria + Bronze, servidores físicos separados) — a checagem de conteúdo ali usa comparação em Python (`set` de tuplas), não `MINUS` em SQL, porque não existe DB LINK entre os dois servidores para rodar um MINUS num só SELECT.

Arquivos: `conferencias/dw_bronze/conferencia_estoque.py`, `conferencia_producao.py`, `conferencia_laudos.py`, `conferencia_expedicao.py`, `conferencia_rastreabilidade.py`, `conferencia_opex.py`.

### O que fazer na VM depois desta correção

As 9 tabelas corrigidas mudam o universo de dados que a Bronze vai trazer (mais filiais). Precisa, na VM:

1. Dropar as 9 tabelas na `DW_BRONZE`: `E420IPO`, `E420OCP` (Estoque) · `E210MVP`, `E621MTC`, `E900COP`, `E930MPR` (Produção) · `USU_TLAUITE`, `USU_TLAUGER`, `USU_VZRASLAU` (Laudos RMA).
2. Rodar o extrator de cada área afetada (`estoque.bronze.extrator`, `producao.bronze.extrator`, `laudos_rma.bronze.extrator`) — a ausência da tabela força carga full automaticamente.
3. Rodar a conferência de cada área (`conferencias.dw_bronze.conferencia_estoque`, etc.) pra confirmar `OK` na contagem antes de considerar a área pronta pra quando a Prata dela começar.

Como a Prata dessas áreas ainda não existe, não há impacto em nenhum Power BI de produção agora — esta correção deixa a Bronze pronta e validada **antes** de a Prata ser construída em cima dela, evitando repetir o mesmo ciclo de bugs (achar na conferência da Prata, bem mais tarde) que aconteceu no Comercial.

### Bug lateral encontrado durante o rollout: `remover_orfaos_cross_servidor()` sem `dtype` no staging (18/07/2026)

Ao rodar `--sweep-orfaos` no OPEX pela primeira vez desde essa correção, `USU_T650ORC` deu `ORA-00932: inconsistent datatypes: expected - got CLOB` no `DELETE` da varredura de órfãos. Causa: `remover_orfaos_cross_servidor()` (`core/loader.py`) grava a tabela de staging via `df_pks.to_sql(...)` **sem** passar `dtype=` — o pandas então deixa o SQLAlchemy inferir o tipo, e qualquer coluna de texto vira `CLOB` no Oracle (independente do tamanho real do conteúdo), enquanto a tabela `DW_BRONZE` já existente tem essa mesma coluna como `VARCHAR2`. Comparar `CLOB = VARCHAR2` no `WHERE` do `DELETE` estoura.

Não é o mesmo bug do `tem_codfil` — é um problema de infraestrutura isolado, sem relação com filial. Confirmado que é o único ponto cego: das 5 chamadas `.to_sql()` que existem em todo o projeto (todas em `core/loader.py`), só essa (a de `remover_orfaos_cross_servidor()`) não passava `dtype=dtype_map` — a função irmã `upsert_cross_servidor()` (usada pra carga normal do OPEX, já rodada com sucesso várias vezes) sempre fez isso certo. Faz sentido esse ser o ponto cego: a varredura de órfãos cross-servidor só roda 1x por dia (última execução, flag `--sweep-orfaos`), então é o caminho de código menos exercitado do projeto — essa foi a primeira vez que rodou de fato contra o OPEX.

**Corrigido**: adicionado `dtype_map = build_dtype_map(df_pks)` antes do `to_sql()`, com `dtype=dtype_map` passado — mesmo padrão já usado nas outras 4 chamadas.

---

## Pontos de atenção por tabela (Comercial)

### `DIM_CONDICAO_PAGAMENTO` — validada

Lógica idêntica ao legado, sem observação especial.

### `DIM_PRODUTO` — pronta

Sem observação de negócio especial. Um JOIN da query original (com a família de produto) não é usado em nenhuma coluna final — mantido exatamente como estava, não é objetivo desta migração alterar o que já está validado.

### `DIM_REPRESENTANTE` — pronta

Sem observação de negócio especial.

### `DIM_REGIONAL` — pronta

A query original tinha nomes de responsável fixos pra 3 regionais específicas e 1 login que não formata bem pela regra genérica, misturados dentro do cálculo principal. Essas exceções foram isoladas num bloco separado no topo da query — mesmo resultado, mas fácil de achar e de estender (basta acrescentar uma linha, sem mexer no restante da lógica).

### `FAT_METAS` — pronta

A query original não tem nenhum corte de data — **mantido assim de propósito**. Meta histórica pode precisar ficar visível sem corte, diferente do faturamento; não aplicamos o `01/01/2021` aqui sem confirmar antes que faz sentido pro time de Analytics.

### `DIM_CLIENTE` — validada (17/07/2026), 3 bugs de Bronze encontrados e corrigidos na conferência

Tem um cálculo pesado (1ª/2ª/3ª/4ª compra de cada cliente) que reprocessa todo o histórico de vendas a cada execução. Decisão: manter a lógica exatamente igual ao legado — é insumo de métrica de recorrência/churn, não vale o risco de mudar o cálculo sem uma validação bem cuidadosa. Uma otimização fica como ideia pra um momento futuro dedicado, não agora.

**Bug encontrado na conferência (1)**: 28.984 clientes (≈20%) divergiram do legado — não em formatação, mas com a sequência de 1ª/2ª/3ª/4ª compra deslocada (faltava a compra mais antiga). Causa raiz: o catálogo da Bronze (`comercial/bronze/tabelas.py`) filtrava `CODFIL = 1` nas 7 tabelas grandes/transacionais (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`), mas nenhum script legado (nem `vbicliente.py`, nem `vbifaturamento.py`) filtra `CODFIL` — sempre consideraram todas as filiais da empresa 1. Confirmado com uma nota fiscal real de 2018 sob `CODFIL=2` que sumia da Bronze. **Corrigido**: `tem_codfil` virou `False` nas 7 tabelas (mantendo `tem_codemp: True`).

**Bug encontrado na conferência (2)**: depois do fix acima, a divergência caiu 92% (pra 2.266 clientes), mas ficou um resíduo estável (sempre os mesmos clientes/valores, não some sozinho). Causa raiz: 3 tabelas auxiliares (`E085HCL`, `E140IDE`, `E140PVD`) também filtravam `CODFIL = 1` na Bronze, mas são usadas em JOIN sem essa restrição nos scripts legados (`E140IDE`: casamento só por `NUMNFV`/pela filial da própria nota; `E085HCL`/`E140PVD`: casamento dinâmico pela filial da linha no `FAT_FATURAMENTO`). **Corrigido**: as 3 viraram `tem_codfil: False` também.

Como as duas correções mudam o universo de dados, precisa dropar as tabelas afetadas na `DW_BRONZE` (as 7 grandes + `E085HCL`, `E140IDE`, `E140PVD`) e deixar a próxima execução refazer a carga antes de reconferir. **Afeta também o `FAT_FATURAMENTO`**, que usa as mesmas tabelas.

**Bug encontrado na conferência (3)**: depois dos 2 fixes acima, a divergência caiu pra 35 clientes (99,98% de melhoria) — mas os 35 restantes não eram bug de filial. Comparando Sapiens direto x legado (ambos batendo entre si) x Bronze (diferente dos dois), a causa era outra: `E085CLI` sincronizava incremental por `DATATU >= SYSDATE-60`, mas `DATATU` não captura toda edição de cadastro (endereço, número) — o legado nunca teve esse problema porque relê a base inteira a cada execução (sem filtro de data nenhum), usando `MERGE` só como estratégia de escrita, não de leitura. **Corrigido**: `coluna_data` de `E085CLI` virou `None` — Bronze agora também relê a tabela inteira a cada ciclo (~145 mil linhas, barato), igual ao legado.

**Conferência da Bronze também tinha um furo**: `conferencias/dw_bronze/conferencia_comercial.py` comparava `COUNT(*)` Sapiens x Bronze, mas usava o MESMO filtro do catálogo (`tem_codemp`/`tem_codfil`) nos dois lados — então uma tabela com `tem_codfil=True` errado comparava "Sapiens filtrado" x "Bronze filtrada", os dois erravam igual, e a contagem batia. Foi por isso que os bugs de `CODFIL` não apareceram na conferência da Bronze, só na conferência da Prata contra o legado, bem mais tarde no processo. **Corrigido**: a conferência agora mostra também a contagem do Sapiens **sem** filtro de filial, lado a lado com a oficial, como sinal visível pra revisão humana (não decide OK/DIVERGENTE sozinho — pode ser um `tem_codfil=True` correto, como Expedição/Rastreabilidade). Também ganhou uma checagem de **conteúdo** (MINUS dado a dado, não só contagem), sob demanda por tabela (`--conteudo NOME_TABELA`) — pega divergência de valor que a contagem nunca pegaria (foi assim que achamos o bug do `E085CLI`).

**Resultado final**: com a Bronze corrigida e conferida (contagem + conteúdo, ver `conferencia_comercial.py`), `conferencia_dim_cliente.py` bateu **0 divergências dos dois lados** — `[OK] Dados idênticos`. A pequena diferença de contagem que ainda aparece entre Prata e legado (2 linhas, numa tabela com 145 mil) é esperada: o legado atualiza ao vivo a cada poucos minutos, e a conferência não é atômica (conta os dois lados, depois faz o MINUS, em queries separadas) — não é sinal de dado faltando, o MINUS já prova isso. `DIM_CLIENTE` está considerado validado.

### `FAT_FATURAMENTO` — pronta

A mais complexa das 7: mistura pedidos em aberto (que mudam de valor com o tempo) com vendas e devoluções já emitidas (que não mudam mais). **Decisão confirmada (17/07/2026): mantém `full_reload`**, igual ao legado — os mesmos motivos que levaram a essa estratégia no legado continuam valendo aqui (não faz sentido reorganizar o modelo do Power BI pra ganhar um incremental parcial). Duas melhorias de baixo risco aplicadas (colunas de rastreio de origem adicionadas, hint de banco desatualizado removido); uma terceira melhoria (deduplicar um cálculo repetido) foi cogitada e **descartada conscientemente** — o risco de mexer numa query financeira sem poder testar antes de entregar não compensava o ganho.

---

## Validação Prata x legado

Cada tabela só é considerada pronta depois de bater, **linha a linha e coluna a coluna**, contra a tabela correspondente no legado (`BIAQUARIO`) — não basta a quantidade de registros ser igual, os valores de negócio (faturamento, meta, cadastro etc.) precisam ser exatamente os mesmos. Essa conferência é feita por um script próprio, criado junto com cada tabela nova, e só avançamos pra próxima tabela depois de confirmar que os dados batem 100%.
