"""
Catálogo/documentação das tabelas da camada Prata do Laudos RMA.

Diferente do catálogo da Bronze (que alimenta um motor genérico), este
arquivo NÃO é executado por nenhum extrator -- é só documentação viva,
atualizada conforme cada arquivo prata/<nome_tabela>.py é criado e
validado.

Ver doc_nova_arquitetura.md (raiz do projeto) para o histórico completo
de decisões e o porquê de cada uma.
"""

# ----- CATÁLOGO -----

TABELAS = [

    {
        "tabela_nova": "DIM_RECLASSIF_DEFEITOS",
        "tabela_legado": "USU_VBIARMA_RECLASSIF_DEFEITOS",
        "script_legado": "vbireclassif_defeitos.py",
        "arquivo_prata": "dim_reclassif_defeitos.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "origem": "Excel (Z:\\Dados\\DefeitosProdutosRMA.xlsx, aba DescDefeitos) -- não passa pela Bronze",
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_reclassif_defeitos.py)",
        "observacao": "Lógica idêntica ao legado. Chave PROD_COD_DEF (Produto|Código) usada no modelo semântico do Power BI para juntar com FAT_LAUDOS.",
    },
    {
        "tabela_nova": "DIM_RECLASSIF_PRODUTOS",
        "tabela_legado": "USU_VBIARMA_RECLASSIF_PRODUTOS",
        "script_legado": "vbireclassif_produtos.py",
        "arquivo_prata": "dim_reclassif_produtos.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "origem": "Excel (Z:\\Dados\\DefeitosProdutosRMA.xlsx, aba ClassifProdutos) -- não passa pela Bronze",
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_reclassif_produtos.py)",
        "observacao": "Lógica idêntica ao legado. Chave CD_PRODUTO usada no modelo semântico do Power BI para juntar com FAT_LAUDOS.",
    },
    {
        "tabela_nova": "DIM_INDICE_RMA",
        "tabela_legado": "USU_VBIARMA_INDICE_RMA",
        "script_legado": "vbiindice_rma.py",
        "arquivo_prata": "dim_indice_rma.py",
        "classificacao": "DIMENSAO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "origem": "Excel (Z:\\Dados\\IndiceRMA.xlsx, aba Planilha1) -- não passa pela Bronze",
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_dim_indice_rma.py)",
        "observacao": "Hierarquia (Pai/ID/Nome) do Índice RMA. Lógica idêntica ao legado.",
    },
    {
        "tabela_nova": "FAT_VENDAS_RMA",
        "tabela_legado": "USU_VBIARMA_VENDAS",
        "script_legado": "vbivendas.py",
        "arquivo_prata": "fat_vendas_rma.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "origem": "DW_BRONZE (E140NFV, E140IPV, E140IDE, E001TNS -- compartilhadas com o Comercial)",
        "corte_data": "01/01/2023 (já existia no legado -- mantido, ver laudos_rma/config/settings.py DATA_CORTE_LAUDOS)",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_vendas_rma.py)",
        "observacao": (
            "Volume médio de vendas dos últimos 6 meses por produto/mês -- "
            "denominador do cálculo do Índice RMA. Grão: mês (LAST_DAY) x "
            "produto, não por transação. Subquery correlacionada (QTDMED) "
            "mantida idêntica ao legado -- já roda sobre dado agregado por "
            "mês/produto, não por linha de venda, então o custo é bem menor "
            "que o padrão de self-join visto em FAT_LAUDOS."
        ),
    },
    {
        "tabela_nova": "FAT_LAUDOS",
        "tabela_legado": "USU_VBIARMA_LAUDOS",
        "script_legado": "vbilaudos.py",
        "arquivo_prata": "fat_laudos.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "origem": "DW_BRONZE (USU_TLAUITE + 13 JOINs -- 6 exclusivas do Laudos RMA, 10 compartilhadas com o Comercial)",
        "corte_data": "01/01/2023 (já existia no legado -- mantido, ver laudos_rma/config/settings.py DATA_CORTE_LAUDOS)",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_laudos.py; a mais complexa das 5, tem lógica de negócio em pandas, não só SQL)",
        "observacao": (
            "full_reload mantido de propósito (igual legado) -- DS_PRAZO e "
            "DIAS_PRAZO_LAUDO usam a data de hoje (SYSDATE/date.today()), "
            "então o resultado muda todo dia mesmo sem nenhum laudo novo. "
            "Grão: item do laudo (1 linha por USU_SEQUNI). "
            "\n\n"
            "MELHORIA APLICADA (1): a subquery de reincidência do legado "
            "era um self-join (USU_TLAUITE/E440NFC contra si mesma, com "
            "T1.DATENT > Tz.DATENT + GROUP BY MAX) -- custo O(n²)-like por "
            "número de série. Trocado por LAG(DATENT) OVER (PARTITION BY "
            "USU_SERMAC ORDER BY DATENT), que calcula 'a entrada anterior "
            "mais recente do mesmo número de série' em uma única passada "
            "ordenada -- resultado matematicamente idêntico (o valor "
            "anterior mais recente numa sequência ordenada É o valor "
            "imediatamente anterior). Validado pela conferencia_fat_laudos.py "
            "(MINUS dado a dado) antes de ser considerada pronta -- se "
            "algum caso de borda divergir, a conferência pega. "
            "\n\n"
            "MELHORIA APLICADA (2): _int_str() do legado convertia NUMBER "
            "para string linha a linha via .apply() em Python puro (lento "
            "em volume). Trocado por versão vetorizada (pd.to_numeric + "
            "Int64), mesmo resultado (ex.: 14.0 -> '14', NULL -> ''), sem "
            "loop em Python. "
            "\n\n"
            "NÃO ALTERADO: toda a lógica de DS_PRAZO/REINCIDENTE/"
            "MACRO_REGIAO/DS_CLASSIF_ENTREGA etc. já usa np.select/np.where "
            "(vetorizado) -- mantida exatamente igual ao legado, sem "
            "reescrever para SQL (risco maior que o ganho, mesmo critério "
            "usado para rejeitar a deduplicação do FUNDPOB no "
            "FAT_FATURAMENTO)."
        ),
    },

]

# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(tabela_nova: str) -> dict:
    """Retorna a configuração de uma tabela do catálogo pelo nome novo (ex.: 'FAT_LAUDOS')."""
    for t in TABELAS:
        if t["tabela_nova"] == tabela_nova:
            return t
    raise KeyError(f"Tabela '{tabela_nova}' não encontrada no catálogo da Prata Laudos RMA.")
