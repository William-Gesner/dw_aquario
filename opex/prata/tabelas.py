"""
Catálogo/documentação da tabela da camada Prata do OPEX.

Diferente do catálogo da Bronze (que alimenta um motor genérico), este
arquivo NÃO é executado por nenhum extrator -- é só documentação viva,
atualizada conforme fat_orcamento_opex.py é criado e validado. Mesmo
padrão do comercial/prata/tabelas.py e laudos_rma/prata/tabelas.py.

Diferente das outras áreas (7 tabelas no Comercial, 5 no Laudos RMA), o
OPEX tem só 1 tabela -- o legado nunca teve dimensão separada (tudo já
vem denormalizado num único resultado, ver vbiopex.py).

Ver doc_nova_arquitetura.md (raiz do projeto), seção "OPEX", para o
histórico completo de decisões e o porquê de cada uma.
"""

# ----- CATÁLOGO -----

TABELAS = [

    {
        "tabela_nova": "FAT_ORCAMENTO_OPEX",
        "tabela_legado": "USU_VBIAOPEX_ORCAMENTO",
        "script_legado": "vbiopex.py",
        "arquivo_prata": "fat_orcamento_opex.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": None,
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_orcamento_opex.py)",
        "observacao": (
            "Única tabela desta área -- sem dimensão separada, igual o "
            "legado (denormalizado: descrição de centro de custo, plano "
            "de contas e nome de dono/coordenador embutidos no fato). "
            "full_reload pelo mesmo motivo do FAT_FATURAMENTO: FULL OUTER "
            "JOIN entre orçamento e realizado sem chave natural 100% "
            "confiável para MERGE. Sem corte de data -- mesma decisão já "
            "tomada para FAT_METAS (fato de planejamento, não de "
            "transação). CODEMP_AQUARIO_OPEX = (1, 50) mantido (exceção "
            "documentada, 2 razões sociais). Mudança real de arquitetura: "
            "lê da DW_BRONZE em vez do Sapiens Controladoria direto -- só "
            "precisa de get_engine_prata(), não mais de "
            "get_engine_controladoria()."
        ),
    },

]

# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(tabela_nova: str) -> dict:
    """Retorna a configuração da tabela do catálogo pelo nome novo (ex.: 'FAT_ORCAMENTO_OPEX')."""
    for t in TABELAS:
        if t["tabela_nova"] == tabela_nova:
            return t
    raise KeyError(f"Tabela '{tabela_nova}' não encontrada no catálogo da Prata OPEX.")
