"""
Catálogo/documentação das tabelas da camada Prata do Comercial.

Diferente do catálogo da Bronze (que alimenta um motor genérico), este
arquivo NÃO é executado por nenhum extrator -- é só documentação viva,
atualizada conforme cada arquivo prata/<nome_tabela>.py é criado e
validado. Serve de referência rápida (nome antigo x novo, estratégia de
carga, classificação) sem precisar abrir os 7 scripts pra saber o status.

Ver doc_nova_arquitetura.md (raiz do projeto) para o histórico completo
de decisões e o porquê de cada uma.
"""

# ----- CATÁLOGO -----

TABELAS = [

    {
        "tabela_nova": "DIM_CONDICAO_PAGAMENTO",
        "tabela_legado": "USU_VBIACONDPGTO",
        "script_legado": "vbicondpgto.py",
        "arquivo_prata": "dim_condicao_pagamento.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CODCPG"],
        "corte_data": None,
        "status": "VALIDADA (16/07/2026) -- extração OK (176 linhas) + conferencia_dim_condicao_pagamento.py bateu [OK] contra o legado",
        "observacao": "Lógica idêntica ao legado, só troca origem (Bronze).",
    },
    {
        "tabela_nova": "DIM_PRODUTO",
        "tabela_legado": "USU_BVIPRODUTOS",
        "script_legado": "vbiproduto.py",
        "arquivo_prata": "dim_produto.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CHAVE_ITEM"],
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_produto.py)",
        "observacao": None,
    },
    {
        "tabela_nova": "DIM_REPRESENTANTE",
        "tabela_legado": "USU_VBIREPRESENTANTES",
        "script_legado": "vbirepresentantes.py",
        "arquivo_prata": "dim_representante.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CODREP"],
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_representante.py)",
        "observacao": None,
    },
    {
        "tabela_nova": "DIM_REGIONAL",
        "tabela_legado": "USU_VBIREGIONAIS",
        "script_legado": "vbiregionais.py",
        "arquivo_prata": "dim_regional.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["ID_REGIONAL"],
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_regional.py)",
        "observacao": (
            "Overrides hardcoded de responsável (3 regionais por ID + 1 "
            "login) isolados em 2 CTEs no topo da query (WITH "
            "OVERRIDES_POR_REGIONAL / OVERRIDES_POR_LOGIN), combinados via "
            "COALESCE -- mesmo resultado do CASE original, mais fácil de "
            "estender. Tentativa inicial de fazer isso em pandas (pós-"
            "processando o DataFrame) foi descartada -- upsert() reexecuta "
            "a query original como SQL puro dentro do MERGE, então a "
            "correção precisa estar na própria query."
        ),
    },
    {
        "tabela_nova": "FAT_METAS",
        "tabela_legado": "USU_VBIMETAS",
        "script_legado": "vbimetas.py",
        "arquivo_prata": "fat_metas.py",
        "classificacao": "FATO",
        "tipo_carga": "upsert",
        "chaves_merge": ["CODEMP", "MESANO", "CODTIP", "SEQREG"],
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_metas.py)",
        "observacao": "Sem corte de data no legado -- confirmar antes de aplicar 2021.",
    },
    {
        "tabela_nova": "DIM_CLIENTE",
        "tabela_legado": "USU_BVIACLIENTES",
        "script_legado": "vbicliente.py",
        "arquivo_prata": "dim_cliente.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "upsert",
        "chaves_merge": ["COD_CLIENTE"],
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_cliente.py; mais pesada das 5, pode demorar mais)",
        "observacao": (
            "Tem CTE pesada (ranking de dia de compra via DENSE_RANK sobre "
            "todo o histórico de E140NFV) -- mantida idêntica, sem "
            "otimização incremental por enquanto (risco de drift silencioso "
            "-- ver doc_nova_arquitetura.md)."
        ),
    },
    {
        "tabela_nova": "FAT_FATURAMENTO",
        "tabela_legado": "USU_VBIAFATURAMENTO",
        "script_legado": "vbifaturamento.py",
        "arquivo_prata": "fat_faturamento.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",  # CONFIRMADO com o usuário em 17/07/2026
        "chaves_merge": None,
        "corte_data": "01/01/2021",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_faturamento.py)",
        "observacao": (
            "Mais complexa das 7: UNION ALL de 4 naturezas diferentes "
            "(pedido em aberto -- mutável -- e vendas/devoluções -- "
            "imutáveis), sem chave natural 100% confiável -- full_reload "
            "confirmado (não muda) pelos mesmos motivos do legado. "
            "Melhorias aplicadas: colunas de sequência de origem "
            "(SEQIPD/SEQIPV/SEQISV/SEQIPC) adicionadas por bloco -- "
            "aditivo, não existem no legado, ficam fora da conferência de "
            "propósito. Hint manual do Oracle (bloco DEV) removido -- só "
            "afeta plano de execução, nunca resultado. Deduplicação do "
            "cálculo de FUNDPOB foi cogitada e **descartada** -- risco de "
            "reestruturar uma query financeira sem poder testar contra "
            "Oracle real não compensa o ganho; mantido igual ao legado, "
            "candidato a otimização futura."
        ),
    },

]

# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(tabela_nova: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome novo (ex.: 'DIM_CLIENTE')."""
    for t in TABELAS:
        if t["tabela_nova"] == tabela_nova:
            return t
    raise KeyError(f"Tabela '{tabela_nova}' não encontrada no catálogo da Prata Comercial.")
