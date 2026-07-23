"""
Catálogo/documentação das tabelas da camada Prata da Produção.

Diferente do catálogo da Bronze (que alimenta um motor genérico), este
arquivo NÃO é executado por nenhum extrator -- é só documentação viva,
atualizada conforme cada arquivo prata/<nome_tabela>.py é criado e
validado. Mesmo padrão do comercial/prata/tabelas.py.

Ver doc_nova_arquitetura.md (raiz do projeto), seção "Produção", para o
histórico completo de decisões e o porquê de cada uma.
"""

# ----- CATÁLOGO -----

TABELAS = [

    {
        "tabela_nova": "DIM_PRODUTO_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_PRODUTO",
        "script_legado": "vbiproduto.py",
        "arquivo_prata": "dim_produto_producao.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CODEMP", "CODPRO"],
        "corte_data": None,
        "status": "VALIDADA (22/07/2026, confirmado na VM em 23/07/2026) -- resíduo de CODDER corrigido (desempate amarrado ao legado), conferência batendo 0/0, ver observação",
        "observacao": (
            "Sufixo _PRODUCAO -- já existe DIM_PRODUTO no Comercial, com "
            "campos completamente diferentes (esta tem CODORI, CODAGE, "
            "CURABC, DEPPAD, específicos de manufatura). Depende de "
            "E075PRO/E075DER/E013AGP/E012FAM, compartilhadas com o "
            "Comercial (Regra 8 -- precisa de comercial.bronze.extrator "
            "em dia). BUG CORRIGIDO (22/07/2026, achado 1): 512 linhas "
            "'só na Prata' eram órfãos reais em E075PRO (deletados no "
            "Sapiens, nunca varridos da Bronze -- coluna_data incremental "
            "não pega exclusão, só --sweep-orfaos pega). Resolvido "
            "rodando comercial.bronze.extrator --sweep-orfaos + DROP "
            "TABLE + recarga (upsert nunca remove linha sozinho). "
            "BUG CORRIGIDO (22/07/2026, achado 2): ~96 produtos têm mais "
            "de 1 linha em E075DER (múltiplas derivações reais, ex.: "
            "CODPRO=4K01 tem CODDER='B'/'N'/'U', todas com SITDER='A' -- "
            "não é histórico de status, são registros comerciais "
            "coexistentes e válidos, sem nenhuma coluna que indique qual "
            "é 'a' correta). Como chaves_merge é só [CODEMP, CODPRO] "
            "(mesma do legado), o MERGE só guarda 1 CODDER por produto -- "
            "e SEM critério de desempate de verdade, a escolha dependia "
            "só da ordem física com que o Oracle devolvia as linhas do "
            "JOIN, que MUDA entre Sapiens (legado) e Bronze (Prata) "
            "mesmo com dados idênticos -- 96 divergências na conferência, "
            "confirmado por amostragem que não segue nenhum padrão "
            "alfabético/coluna (às vezes 'ganha' o maior CODDER, às "
            "vezes o menor, sem consistência). "
            "DECISÃO (22/07/2026, confirmada com o usuário): NÃO mudar a "
            "granularidade pra CODPRO+CODDER (motivo original ainda vale "
            "-- Power BI/FAT_DESEMPENHO_PRODUCAO relacionam por CODPRO "
            "só, mudar a chave causaria fan-out). Em vez disso, "
            "desempate passou a preferir explicitamente o CODDER que já "
            "está gravado hoje em BIAQUARIO.USU_VBIAPROD_PRODUTO (LEFT "
            "JOIN só pra esse fim, coluna PRIORIDADE_LEGADO removida do "
            "df antes da carga -- nunca vira coluna física). Fallback "
            "determinístico (CODDER ASC) cobre produto sem linha no "
            "legado. LIMITAÇÃO CONHECIDA: esse amarramento só funciona "
            "enquanto USU_VBIAPROD_PRODUTO existir -- quando o legado for "
            "desligado, a ambiguidade volta e precisa de nova decisão "
            "(ex.: revisitar granularidade CODPRO+CODDER). Ver "
            "dw_aquario/doc_nova_arquitetura.md, seção 'Produção', e o "
            "docstring de dim_produto_producao.py para o histórico "
            "completo."
        ),
    },
    {
        "tabela_nova": "DIM_CENTRO_CUSTO_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_CENTROCUSTO",
        "script_legado": "vbicentrocusto.py",
        "arquivo_prata": "dim_centro_custo_producao.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CODCCU", "CODETG", "CODCRE", "CODOPR"],
        "corte_data": None,
        "status": "VALIDADA (22/07/2026) -- 3 achados corrigidos, os 2 testes de conferencia_dim_centro_custo_producao.py batendo [OK]",
        "observacao": (
            "UNION ALL de 2 blocos (estrutura principal + centros de "
            "recurso sem estágio, lista hardcoded fiel ao legado). "
            "Todas as 4 tabelas fonte são exclusivas do catálogo da "
            "Produção. CORRIGIDO (1) em 21/07/2026: chaves_merge do "
            "legado ([CODCCU, CODETG, CODCRE], sem CODOPR) descartava "
            "operações duplicadas por grupo -- confirmado em E720OPR que "
            "são 21 grupos reais com mais de 1 operação (até 23 num só "
            "grupo). Adicionado CODOPR à chave -- tabela cresce de ~133 "
            "para ~195 linhas (granularidade correta, não inflação). "
            "CORRIGIDO (2) em 22/07/2026: CODOPR pode ser NULL (2º bloco, "
            "LEFT JOIN sem operação vinculada -- 10 dos 11 códigos "
            "hardcoded) -- como NULL nunca combina com NULL num MERGE, "
            "essas 10 linhas duplicavam a cada execução (confirmado na "
            "VM: 10 grupos com 2 cópias idênticas cada, crescendo a cada "
            "rodada). Corrigido com NVL(CODOPR, ' ') no 2º bloco -- "
            "mesma convenção já usada nesta query pra CODETG/DESETG. "
            "LIÇÃO GERAL: nenhuma coluna nullable pode entrar em "
            "chaves_merge sem NVL/COALESCE antes. ACHADO (3) em "
            "22/07/2026: CODCRE=2540 aparece nos 2 blocos com a mesma "
            "chave (já tem cobertura natural no bloco 1, redundante na "
            "lista hardcoded do bloco 2) -- diferença cosmética NULL x "
            "' ' em DESETG/ABRETG mascarava como divergência na "
            "conferência. Corrigido só na conferência (NVL nas colunas "
            "comparadas), não na carga -- essas colunas não fazem parte "
            "da chaves_merge. Resultado final: 194 linhas na Prata, "
            "conferência batendo [OK] nos 2 testes (regressão contra o "
            "legado + completude contra a Bronze). Conferência não usa "
            "mais o padrão MINUS-simétrico contra o legado (ele tem a "
            "mesma limitação de chave que o legado sempre teve) -- ver "
            "conferencia_dim_centro_custo_producao.py."
        ),
    },
    {
        "tabela_nova": "DIM_CUSTO_PADRAO_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_CUSTO_PADRAO",
        "script_legado": "vbicustopadrao.py",
        "arquivo_prata": "dim_custo_padrao_producao.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_custo_padrao_producao.py)",
        "observacao": (
            "Excel (Z:\\Dados\\TempoDisponivelCC.xlsx, aba CP) -- fora da "
            "Bronze, mesma exceção das dimensões de Excel do Laudos RMA. "
            "Classificação DIM confirmada via consulta no legado em "
            "21/07/2026: 324 linhas = 324 produtos distintos, sem "
            "duplicidade -- 1 valor fixo por produto, sem grão de "
            "período."
        ),
    },
    {
        "tabela_nova": "FAT_PARADAS_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_PARADAS",
        "script_legado": "vbiparadas.py",
        "arquivo_prata": "fat_paradas_producao.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": "01/01/2021",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_paradas_producao.py)",
        "observacao": (
            "Legado cortava em 01/01/2018 (DATA_INICIO_HISTORICO) -- "
            "trocado para 01/01/2021 por decisão explícita do usuário "
            "em 21/07/2026 (padrão único pra toda a área)."
        ),
    },
    {
        "tabela_nova": "FAT_CUSTO_CC_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_CUSTOCC",
        "script_legado": "vbicustocc.py",
        "arquivo_prata": "fat_custo_cc_producao.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": "01/01/2021",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_custo_cc_producao.py)",
        "observacao": (
            "CORTE NOVO -- o legado não tinha corte de data nenhum "
            "nesta tabela. Adicionado 01/01/2021 (T2.DATINI) por decisão "
            "explícita do usuário em 21/07/2026, mesmo sem precedente no "
            "legado -- muda o volume visível no Power BI (esconde "
            "DATINI < 2021), mudança de escopo consciente."
        ),
    },
    {
        "tabela_nova": "FAT_UTILIZACAO_META_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_UTILIZACAO_META",
        "script_legado": "vbiutilizacaometa.py",
        "arquivo_prata": "fat_utilizacao_meta_producao.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": "01/01/2021",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_utilizacao_meta_producao.py)",
        "observacao": (
            "Excel (Z:\\Dados\\TempoDisponivelCC.xlsx, aba BD) -- fora da "
            "Bronze. CORTE NOVO (legado não tinha), mesma decisão do "
            "FAT_CUSTO_CC_PRODUCAO -- na prática deve remover pouco ou "
            "nada, já que é meta corrente mantida manualmente."
        ),
    },
    {
        "tabela_nova": "FAT_DESEMPENHO_PRODUCAO",
        "tabela_legado": "USU_VBIAPROD_DESEMPENHO",
        "script_legado": "vbidesempenho.py",
        "arquivo_prata": "fat_desempenho_producao.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": "01/01/2021",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_desempenho_producao.py; mais pesada das 7, 3 subqueries correlacionadas no bloco DESEMPENHO -- medir tempo real antes de considerar otimizar, mesma régua do FAT_FATURAMENTO/Rastreabilidade)",
        "observacao": (
            "Fato central -- UNION ALL de 4 naturezas (DESEMPENHO/"
            "CONSUMO/PARADAS/CUSTO_CC), mesmo padrão do FAT_FATURAMENTO. "
            "Corte de 2021 nos blocos 1/2/3 (era 2018 no legado) + corte "
            "NOVO no bloco 4 (CUSTO_CC, sem precedente no legado) -- "
            "mesma decisão do FAT_CUSTO_CC_PRODUCAO."
        ),
    },

]

# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(tabela_nova: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome novo (ex.: 'FAT_DESEMPENHO_PRODUCAO')."""
    for t in TABELAS:
        if t["tabela_nova"] == tabela_nova:
            return t
    raise KeyError(f"Tabela '{tabela_nova}' não encontrada no catálogo da Prata Produção.")
