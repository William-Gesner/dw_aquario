# Progresso da migração — Fase 2 (Camada Prata)

> Documento de acompanhamento da Fase 2 (camada Prata): decisões de negócio, convenção de nomes e status por tabela. Não cobre infraestrutura/Bronze (isso fica no `contexto.md` original). Última atualização: 20/07/2026.

---

## O que é a Fase 2, em 3 frases

Com as 7 áreas de negócio já migradas pra Bronze, a Fase 2 recria a camada **Prata** de cada área, **replicando fielmente** as regras de negócio do projeto legado — só muda a arquitetura (lê da Bronze, nunca do Sapiens direto) e a nomenclatura das tabelas. O resultado final (os dados, os números) **precisa ser idêntico** ao que já está em produção hoje — clientes já têm Power BI consumindo o projeto legado, então essa migração é troca de fundação, não de resultado. Começamos pelo **Comercial** (7 tabelas), tabela por tabela, sempre com validação antes de seguir.

---

## Onde fica cada coisa

- **Prata**: `dw_aquario/<area>/prata/` — 1 arquivo por tabela, nome do arquivo = nome da tabela nova em minúsculo (ex.: `dim_cliente.py` gera `DIM_CLIENTE`).
- **Catálogo**: `comercial/prata/tabelas.py` — nome antigo x novo, classificação, estratégia de carga, status de cada tabela do Comercial.
- **Conferência**: `dw_aquario/conferencias/conferencia_<tabela_nova>.py` — valida se a Prata bate com o legado (dado a dado, não só contagem) antes de considerar a tabela pronta.

---

## Status atual (20/07/2026)

**Bronze**: concluída nas 7 áreas — pré-requisito já atendido, todas as tabelas fonte disponíveis. Auditoria do bug de `tem_codfil` (Regra 6) estendida a todas as áreas em 17/07/2026 — 9 tabelas corrigidas fora do Comercial (Estoque, Produção, Laudos RMA), 2 confirmadas corretas (Expedição, Rastreabilidade); ver seção "Correção do `tem_codfil` nas demais áreas da Bronze". OPEX não teve nenhuma tabela com `tem_codfil` (área sem conceito de filial).

**Prata**:

| Área | Status |
|---|---|
| Comercial | **7/7 tabelas construídas, testadas na VM e consideradas finalizadas** (20/07/2026) — ver ressalva na seção "Comercial finalizado" |
| Laudos RMA | **Levantamento em andamento** — 5 scripts legados mapeados, Prata ainda não criada (ver seção própria) |
| OPEX, Produção, Estoque, Expedição, Rastreabilidade | Não iniciada |

### Tabelas da Prata do Comercial

| Tabela nova | Tabela legado | Classificação | Status |
|---|---|---|---|
| `DIM_CONDICAO_PAGAMENTO` | `USU_VBIACONDPGTO` | Dimensão | ✅ **Validada** — dados batem 100% com o legado |
| `DIM_PRODUTO` | `USU_BVIPRODUTOS` | Dimensão | ✅ **Validada** — testada na VM, conferência batendo |
| `DIM_REPRESENTANTE` | `USU_VBIREPRESENTANTES` | Dimensão | ✅ **Validada** — testada na VM, conferência batendo |
| `DIM_REGIONAL` | `USU_VBIREGIONAIS` | Dimensão | ✅ **Validada** — testada na VM, conferência batendo (melhoria aplicada — ver abaixo) |
| `FAT_METAS` | `USU_VBIMETAS` | Fato | ✅ **Validada (20/07/2026)** — testada com troca real de representante em produção (506 → 544), conferência bateu 100% (ver "Comercial finalizado") |
| `DIM_CLIENTE` | `USU_BVIACLIENTES` | Dimensão | ✅ **Validada (17/07/2026)** — 3 bugs de Bronze encontrados e corrigidos na conferência (ver observação abaixo); MINUS final bateu 0 dos dois lados |
| `FAT_FATURAMENTO` | `USU_VBIAFATURAMENTO` | Fato | ✅ **Validada (20/07/2026)** — testada na VM, índices da Bronze corrigidos, validação extra por agregado mensal batendo 100% (ver "Comercial finalizado") |

**As 7 tabelas do Comercial estão construídas e testadas na VM.** Ver seção "Comercial finalizado" logo abaixo.

---

## Comercial finalizado (20/07/2026)

Todas as 7 tabelas testadas na VM (extração + conferência). Achados relevantes desta última rodada:

- **Performance / índices da Bronze**: `fat_faturamento.py` estava demorando bastante. Causa raiz: `full_reload_streaming()` (`core/loader.py`) nunca cria índice automático — só `upsert()` faz isso (via `_ensure_table`), e só na criação da tabela. As 7 tabelas grandes/transacionais da Bronze (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`) tinham perdido o índice quando foram dropadas e recarregadas para o fix do `tem_codfil` (17/07/2026) — a recarga (`full_reload_streaming`) não recriou o índice que existia antes do DROP. Índices recriados manualmente na VM; tempo total de extração+carga do `FAT_FATURAMENTO` caiu de bem lento para ~65s. **Pendência conhecida, não corrigida no código**: `full_reload_streaming()` continua sem criar índice — qualquer futuro "dropar e deixar recarregar" (padrão de correção usado várias vezes neste projeto) vai repetir esse mesmo problema até isso ser corrigido na função.
- **FAT_FATURAMENTO — validação extra por agregado mensal**: além da conferência linha a linha, validamos meses fechados (abril, maio, junho/2026) comparando soma de `VLR_LIQ`/`VLRBRUTO_TOTAL` e contagem por `TIPOREG`, direto no Sapiens x Prata — bateu 100% nos 3 meses. O pequeno resíduo visto em notas de janeiro/2026 (campos `CODCLIBASE`/`CODREGREP`/`CODREGCLI` de `E140NFV`) foi rastreado a uma oscilação ativa do próprio Sapiens (o valor mudava de um minuto pro outro em consultas diretas) — não é bug de pipeline, é instabilidade do dado de origem.
- **FAT_METAS — validado com mudança real de produção**: testado durante uma troca real de representante (saída do 506, entrada do 544) na meta de julho/2026. Confirmou que o fluxo Bronze → Prata → conferência reflete corretamente tanto atualização quanto substituição de linha (o Sapiens criou um `SEQREG` novo para o 544 em vez de editar o do 506 — ou seja, testou também o caminho de "linha órfã" que a limpeza de órfãos da Bronze precisa cobrir).

**Ressalva importante**: o Comercial não está sendo considerado 100% fechado em definitivo. Várias tabelas da Bronze são compartilhadas com outras áreas ainda não migradas (Laudos RMA, Rastreabilidade, Produção, Estoque) — pode surgir alguma divergência nova quando essas dependências forem exercitadas por elas. Mas a área em si (as 7 tabelas, suas regras de negócio e a validação contra o legado) está migrada e testada.

---

## Laudos RMA (20/07/2026, em andamento)

Segunda área a migrar, seguindo o mesmo processo do Comercial: analisar os 5 scripts legados (`aquario/laudos_rma/extract/`), decidir `DIM_`/`FAT_`, confirmar que a Bronze já tem tudo, só depois criar a Prata.

### Tabelas da Prata do Laudos RMA

| Tabela nova | Tabela legado | Classificação | Origem | Status |
|---|---|---|---|---|
| `DIM_RECLASSIF_DEFEITOS` | `USU_VBIARMA_RECLASSIF_DEFEITOS` | Dimensão | Excel (`Z:\Dados\DefeitosProdutosRMA.xlsx`, aba `DescDefeitos`) | 🔶 Pronta — aguardando teste na VM |
| `DIM_RECLASSIF_PRODUTOS` | `USU_VBIARMA_RECLASSIF_PRODUTOS` | Dimensão | Excel (mesmo arquivo, aba `ClassifProdutos`) | 🔶 Pronta — aguardando teste na VM |
| `DIM_INDICE_RMA` | `USU_VBIARMA_INDICE_RMA` | Dimensão | Excel (`Z:\Dados\IndiceRMA.xlsx`, aba `Planilha1`) | 🔶 Pronta — aguardando teste na VM |
| `FAT_VENDAS_RMA` | `USU_VBIARMA_VENDAS` | Fato | DW_BRONZE (E140NFV, E140IPV, E140IDE, E001TNS) | ✅ **Validada (20/07/2026)** — reescrita (agregação + window function) testada na VM: 3,6s total (contra 190s do legado e >1h30 da 1ª versão); conferência bateu com 1 linha de diferença (nota do dia corrente, esperado) |
| `FAT_LAUDOS` | `USU_VBIARMA_LAUDOS` | Fato | DW_BRONZE (USU_TLAUITE + 13 JOINs) | ✅ **Validada (20/07/2026)** — testada na VM depois de 2 correções na Bronze (ver seção própria); conferência caiu de 35 mil divergências pra 1 linha (laudo aberto no dia, esperado) |

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

---

## Regras de negócio fixas da Fase 2

1. **Nomenclatura**: `FAT_`/`DIM_` + nome da entidade, tudo maiúsculo. Fato = tem medida quantificável por período/dimensão (ex.: faturamento, meta). Dimensão = entidade descritiva (cliente, produto, representante), mesmo carregando algum atributo agregado.
2. **Corte de data**: `01/01/2021` pra frente, em toda tabela **FATO** com grão de data, de todas as áreas. **Dimensão nunca tem corte** (sempre o universo completo e atual das entidades — ex.: todo cliente cadastrado aparece em `DIM_CLIENTE`, independente de quando foi cadastrado). Esse corte só muda o que aparece no Power BI se a área/tabela **não** já tivesse um corte parecido no legado — isso é conferido tabela por tabela antes de aplicar, exatamente pra não mudar resultado sem avisar.
3. **Resultado idêntico ao legado é obrigatório**: cada tabela só é considerada pronta depois de uma conferência formal (dado a dado, não só contagem de linhas) contra a tabela correspondente no schema legado (`BIAQUARIO`). Ver seção "Validação" abaixo.
4. **Metadado técnico — `DW_DATA_INGESTAO` (Bronze) / `DW_DATA_PROCESSAMENTO` (Prata)**: toda tabela, nas duas camadas, ganha essa coluna automaticamente, registrando quando aquela linha foi gravada/atualizada pela última vez. Implementado de forma centralizada no `core/loader.py` — nenhum script de área precisa se preocupar com isso, é automático em toda escrita. Nomes diferentes por camada porque a ação é diferente (Bronze ingere, Prata processa).
5. **Índice comum (não PK) na chave de merge**: toda tabela nova (Bronze ou Prata) já nasce com índice, criado automaticamente no momento da criação da tabela — não precisa de retrofit depois. É índice comum, não constraint de PK (performance de busca praticamente igual, mas não trava a criação se existir alguma duplicata). Tabelas `full_reload` (como `FAT_FATURAMENTO`) não criam índice automático — se precisar, é caso a caso.
6. **`tem_codfil` na Bronze: só `True` se o(s) script(s) legado(s) fixarem a filial explicitamente** (ex.: `AND X.CODFIL = 1`). Bug real encontrado em 17/07/2026: 10 tabelas do catálogo do Comercial (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`, `E085HCL`, `E140IDE`, `E140PVD`) estavam com `tem_codfil: True` sem nenhum script legado realmente restringir filial nos JOINs que as usam — a maioria só filtra `CODEMP` (empresa), ou casa `CODFIL` dinamicamente com a filial da própria linha (`X.CODFIL = Y.CODFIL`), nunca fixando `= 1`. A Bronze filtrada silenciosamente descartava registros de outras filiais, e isso só apareceu na conferência dado-a-dado — contagem de linhas não pega esse tipo de erro. **Regra pra qualquer área nova**: antes de marcar uma tabela do catálogo Bronze como `tem_codfil: True`, confirmar no script legado (JOIN e WHERE) que a filial é fixada em `1` ali — se for casamento dinâmico ou não houver filtro de filial nenhum, é `tem_codfil: False` (Bronze traz o universo completo; quem decide o escopo de filial é a query consumidora na Prata, igual o legado sempre fez). Ver observação de `E140NFV` em `comercial/bronze/tabelas.py` para o caso completo investigado. **Auditoria estendida a todas as áreas em 17/07/2026** — ver seção "Correção do `tem_codfil` nas demais áreas da Bronze" logo abaixo: mais 9 tabelas corrigidas (Estoque, Produção, Laudos RMA), 2 confirmadas corretas como estavam (Expedição, Rastreabilidade).

---

## Correção do `tem_codfil` nas demais áreas da Bronze (17/07/2026)

Depois de fechar `DIM_CLIENTE` no Comercial, foi feita uma auditoria completa do mesmo bug (Regra 6) nas outras 6 áreas da Bronze (Estoque, Expedição, Produção, Laudos RMA, Rastreabilidade, OPEX) — nenhuma delas tinha passado ainda por essa checagem, porque a Prata dessas áreas ainda não começou (só a Bronze existe hoje). Cada tabela com `tem_codfil: True` no catálogo foi confrontada com o JOIN/WHERE real do script legado correspondente (lido do histórico do Git). Resultado: **9 tabelas corrigidas, 2 confirmadas corretas como já estavam.**

### Tabelas corrigidas (mesmo bug do Comercial — `tem_codfil: True` → `False`)

| Área | Tabela | Como era | Como ficou |
|---|---|---|---|
| Estoque | `E420IPO` | `tem_codfil: True` — Bronze descartava itens de OC de filiais ≠ 1 | `tem_codfil: False` — `vbicompras.py` legado não tem nenhum filtro de `CODEMP`/`CODFIL` no `WHERE`; `CODFIL` só aparece no JOIN com `E420OCP` (`T0.CODFIL = T1.CODFIL`, casamento dinâmico) |
| Estoque | `E420OCP` | idem acima | idem acima — mesmo motivo, mesmo JOIN dinâmico |
| Produção | `E210MVP` | `tem_codfil: True` — Bronze descartava movimentação de outras filiais | `tem_codfil: False` — bloco CONSUMO de `vbidesempenho.py` nunca referencia `CODFIL` desta tabela em nenhum JOIN/WHERE |
| Produção | `E621MTC` | `tem_codfil: True` | `tem_codfil: False` — usada em 2 pontos de `vbidesempenho.py` (subconsulta `TAXREA` e bloco CUSTO_CC), nenhum filtra `CODFIL` — PK real nem inclui `CODFIL` |
| Produção | `E900COP` | `tem_codfil: True` | `tem_codfil: False` — `vbidesempenho.py` junta por `CODEMP+CODORI+NUMORP` em 2 blocos, nunca por `CODFIL` |
| Produção | `E930MPR` | `tem_codfil: True` | `tem_codfil: False` — bloco PARADAS de `vbidesempenho.py` não filtra `CODFIL` nem no `WHERE` nem nos JOINs |
| Laudos RMA | `USU_TLAUITE` | `tem_codfil: True` | `tem_codfil: False` — `vbilaudos.py` não tem filtro de `USU_CODFIL` no `WHERE`; só casamento dinâmico nos JOINs (`T0.USU_CODFIL = T1.USU_CODFIL`, `T0.USU_CODFIL = T15.FILNFV`) |
| Laudos RMA | `USU_TLAUGER` | `tem_codfil: True` | `tem_codfil: False` — mesmo motivo do `USU_TLAUITE` |
| Laudos RMA | `USU_VZRASLAU` | `tem_codfil: True` | `tem_codfil: False` — casamento dinâmico dos dois lados que a consomem (`vbilaudos.py` e `vbirastreabilidade.py`); quem fixa filial é sempre a query consumidora, nunca esta view |

Todas as 9 correções seguem exatamente o padrão já documentado na Regra 6: o legado nunca fixava a filial em `1` para essas tabelas — ou não filtrava nada, ou casava dinamicamente com a filial da linha relacionada. A Bronze com `tem_codfil: True` estava descartando silenciosamente dados de filiais diferentes de 1, o mesmo mecanismo do bug já corrigido no Comercial.

### Tabelas confirmadas corretas como estavam (`tem_codfil: True` mantido)

| Área | Tabela | Por que está correto |
|---|---|---|
| Expedição | `USU_V120EST` | `vbiexpedicao.py` fixa `PED.CODFIL = 1` no `WHERE` da tabela-âncora (`E120PED`); o JOIN dinâmico (`EST.CODFIL = PED.CODFIL`) fica transitivamente restrito a filial 1 |
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
