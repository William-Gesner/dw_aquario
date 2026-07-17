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

**Bronze**: concluída nas 7 áreas — pré-requisito já atendido, todas as tabelas fonte disponíveis.

**Prata**:

| Área | Status |
|---|---|
| Comercial | **7/7 tabelas construídas** — 1 validada, 6 aguardando teste na VM |
| OPEX, Produção, Estoque, Expedição, Laudos RMA, Rastreabilidade | Não iniciada |

### Tabelas da Prata do Comercial

| Tabela nova | Tabela legado | Classificação | Status |
|---|---|---|---|
| `DIM_CONDICAO_PAGAMENTO` | `USU_VBIACONDPGTO` | Dimensão | ✅ **Validada** — dados batem 100% com o legado |
| `DIM_PRODUTO` | `USU_BVIPRODUTOS` | Dimensão | 🔶 Pronta — aguardando teste na VM |
| `DIM_REPRESENTANTE` | `USU_VBIREPRESENTANTES` | Dimensão | 🔶 Pronta — aguardando teste na VM |
| `DIM_REGIONAL` | `USU_VBIREGIONAIS` | Dimensão | 🔶 Pronta — aguardando teste na VM (melhoria aplicada — ver abaixo) |
| `FAT_METAS` | `USU_VBIMETAS` | Fato | 🔶 Pronta — aguardando teste na VM |
| `DIM_CLIENTE` | `USU_BVIACLIENTES` | Dimensão | 🔶 Pronta — aguardando teste na VM (ver observação abaixo) |
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

### `DIM_CLIENTE` — pronta, conferência revelou bug na Bronze (corrigido em 17/07/2026)
Tem um cálculo pesado (1ª/2ª/3ª/4ª compra de cada cliente) que reprocessa todo o histórico de vendas a cada execução. Decisão: manter a lógica exatamente igual ao legado — é insumo de métrica de recorrência/churn, não vale o risco de mudar o cálculo sem uma validação bem cuidadosa. Uma otimização fica como ideia pra um momento futuro dedicado, não agora.

**Bug encontrado na conferência**: 28.984 clientes (≈20%) divergiram do legado — não em formatação, mas com a sequência de 1ª/2ª/3ª/4ª compra deslocada (faltava a compra mais antiga). Causa raiz: o catálogo da Bronze (`comercial/bronze/tabelas.py`) filtrava `CODFIL = 1` nas 7 tabelas grandes/transacionais (`E120IPD`, `E120PED`, `E140IPV`, `E140ISV`, `E140NFV`, `E440IPC`, `E440NFC`), mas nenhum script legado (nem `vbicliente.py`, nem `vbifaturamento.py`) filtra `CODFIL` — sempre consideraram todas as filiais da empresa 1. Confirmado com uma nota fiscal real de 2018 sob `CODFIL=2` que sumia da Bronze. **Corrigido**: `tem_codfil` virou `False` nas 7 tabelas (mantendo `tem_codemp: True`). Como isso muda o universo de dados, precisa dropar essas 7 tabelas na `DW_BRONZE` e deixar a próxima execução refazer a 1ª carga do zero antes de reconferir. **Afeta também o `FAT_FATURAMENTO`**, que usa as mesmas 7 tabelas.

### `FAT_FATURAMENTO` — pronta
A mais complexa das 7: mistura pedidos em aberto (que mudam de valor com o tempo) com vendas e devoluções já emitidas (que não mudam mais). **Decisão confirmada (17/07/2026): mantém `full_reload`**, igual ao legado — os mesmos motivos que levaram a essa estratégia no legado continuam valendo aqui (não faz sentido reorganizar o modelo do Power BI pra ganhar um incremental parcial). Duas melhorias de baixo risco aplicadas (colunas de rastreio de origem adicionadas, hint de banco desatualizado removido); uma terceira melhoria (deduplicar um cálculo repetido) foi cogitada e **descartada conscientemente** — o risco de mexer numa query financeira sem poder testar antes de entregar não compensava o ganho.

---

## Validação Prata x legado

Cada tabela só é considerada pronta depois de bater, **linha a linha e coluna a coluna**, contra a tabela correspondente no legado (`BIAQUARIO`) — não basta a quantidade de registros ser igual, os valores de negócio (faturamento, meta, cadastro etc.) precisam ser exatamente os mesmos. Essa conferência é feita por um script próprio, criado junto com cada tabela nova, e só avançamos pra próxima tabela depois de confirmar que os dados batem 100%.
