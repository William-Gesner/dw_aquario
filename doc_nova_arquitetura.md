# Progresso da migração — Fase 2 (Camada Prata)

> Documento de acompanhamento da Fase 2 (camada Prata): decisões de negócio, convenção de nomes e status por tabela. Não cobre infraestrutura/Bronze (isso fica no `contexto.md` original). Última atualização: 17/07/2026.

---

## O que é a Fase 2, em 3 frases

Com as 7 áreas de negócio já migradas pra Bronze, a Fase 2 recria a camada **Prata** de cada área, **replicando fielmente** as regras de negócio do projeto legado — só muda a arquitetura (lê da Bronze, nunca do Sapiens direto) e a nomenclatura das tabelas. O resultado final (os dados, os números) **precisa ser idêntico** ao que já está em produção hoje — clientes já têm Power BI consumindo o projeto legado, então essa migração é troca de fundação, não de resultado. Começamos pelo **Comercial** (7 tabelas), tabela por tabela, sempre com validação antes de seguir.

---

## Onde fica cada coisa

- **Prata**: `dw_aquario/<area>/prata/` — 1 arquivo por tabela, nome do arquivo = nome da tabela nova em minúsculo (ex.: `dim_cliente.py` gera `DIM_CLIENTE`).
- **Catálogo**: `comercial/prata/tabelas.py` — nome antigo x novo, classificação, estratégia de carga, status de cada tabela do Comercial.
- **Conferência**: `dw_aquario/conferencias/conferencia_<tabela_nova>.py` — valida se a Prata bate com o legado (dado a dado, não só contagem) antes de considerar a tabela pronta.

---

## Status atual (17/07/2026)

**Bronze**: concluída nas 7 áreas — pré-requisito já atendido, todas as tabelas fonte disponíveis. Auditoria do bug de `tem_codfil` (Regra 6) estendida a todas as áreas em 17/07/2026 — 9 tabelas corrigidas fora do Comercial (Estoque, Produção, Laudos RMA), 2 confirmadas corretas (Expedição, Rastreabilidade); ver seção "Correção do `tem_codfil` nas demais áreas da Bronze". OPEX não teve nenhuma tabela com `tem_codfil` (área sem conceito de filial).

**Prata**:

| Área | Status |
|---|---|
| Comercial | **7/7 tabelas construídas** — 2 validadas, 5 aguardando teste na VM |
| OPEX, Produção, Estoque, Expedição, Laudos RMA, Rastreabilidade | Não iniciada |

### Tabelas da Prata do Comercial

| Tabela nova | Tabela legado | Classificação | Status |
|---|---|---|---|
| `DIM_CONDICAO_PAGAMENTO` | `USU_VBIACONDPGTO` | Dimensão | ✅ **Validada** — dados batem 100% com o legado |
| `DIM_PRODUTO` | `USU_BVIPRODUTOS` | Dimensão | 🔶 Pronta — aguardando teste na VM |
| `DIM_REPRESENTANTE` | `USU_VBIREPRESENTANTES` | Dimensão | 🔶 Pronta — aguardando teste na VM |
| `DIM_REGIONAL` | `USU_VBIREGIONAIS` | Dimensão | 🔶 Pronta — aguardando teste na VM (melhoria aplicada — ver abaixo) |
| `FAT_METAS` | `USU_VBIMETAS` | Fato | 🔶 Pronta — aguardando teste na VM |
| `DIM_CLIENTE` | `USU_BVIACLIENTES` | Dimensão | ✅ **Validada (17/07/2026)** — 3 bugs de Bronze encontrados e corrigidos na conferência (ver observação abaixo); MINUS final bateu 0 dos dois lados |
| `FAT_FATURAMENTO` | `USU_VBIAFATURAMENTO` | Fato | 🔶 Pronta — aguardando teste na VM (estratégia de carga confirmada — ver abaixo) |

**As 7 tabelas do Comercial estão construídas.** Falta só validar as 6 restantes na VM (extração + conferência de cada uma) pra fechar a área por completo.

**Ordem de construção**: da mais simples pra mais delicada — `DIM_CONDICAO_PAGAMENTO` → `DIM_PRODUTO` → `DIM_REPRESENTANTE` → `DIM_REGIONAL` → `FAT_METAS` → `DIM_CLIENTE` → `FAT_FATURAMENTO` (por último, de propósito).

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
