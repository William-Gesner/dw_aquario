"""
Catálogo/documentação da tabela da camada Prata da Rastreabilidade.

Diferente do catálogo da Bronze (que alimenta um motor genérico), este
arquivo NÃO é executado por nenhum extrator -- é só documentação viva,
atualizada conforme fat_rastreabilidade.py é criado e validado. Mesmo
padrão do comercial/prata/tabelas.py e opex/prata/tabelas.py.

Igual o OPEX, a Rastreabilidade tem só 1 tabela -- o legado nunca teve
dimensão separada (tudo denormalizado num único resultado, ver
vbirastreabilidade.py).

Ver doc_nova_arquitetura.md (raiz do projeto), seção "Rastreabilidade",
para o histórico completo de decisões e o porquê de cada uma.
"""

# ----- CATÁLOGO -----

TABELAS = [

    {
        "tabela_nova": "FAT_RASTREABILIDADE",
        "tabela_legado": "USU_VBIARAST_RASTREABILIDADE",
        "script_legado": "vbirastreabilidade.py",
        "arquivo_prata": "fat_rastreabilidade.py",
        "classificacao": "FATO",
        "tipo_carga": "full_reload",
        "chaves_merge": None,
        "corte_data": "2023/01/01",
        "status": "PRONTA -- validar na VM (extração + conferencia_fat_rastreabilidade.py)",
        "observacao": (
            "Única tabela desta área -- sem dimensão separada, igual o "
            "legado (denormalizado: descrição de produto/cliente/"
            "representante/região embutida no fato). Grão real é o "
            "código de barras/QR gerado (USU_T140QRC), maior tabela "
            "fonte do projeto (~2,7 milhões de linhas na Bronze). "
            "full_reload mantido igual ao legado -- avaliado desenho "
            "incremental (upsert pela PK de USU_T140QRC, que é "
            "insert-only), mas descartado por enquanto: exigiria "
            "resincronizar separadamente as colunas descritivas "
            "(produto/cliente/representante/região/MIX-ORIGEM do Excel) "
            "a cada ciclo, para não divergir do legado quando um cadastro "
            "mudar depois da linha já carregada. Decisão consciente de "
            "medir o full_reload simples primeiro (lendo da Bronze, já "
            "bem mais rápido que o Sapiens ao vivo) antes de assumir esse "
            "risco -- mesmo caso do FAT_FATURAMENTO, onde a causa real de "
            "lentidão era só um índice faltando, não a estratégia de "
            "carga. JOIN modernizado para sintaxe ANSI (era vírgula + "
            "WHERE + operador (+) no legado) -- só legibilidade, sem "
            "mudança de resultado. Corte de data mantido em 01/01/2023 "
            "(legado já tinha, não é o padrão de 2021 do Comercial)."
        ),
    },

]

# ----- FUNÇÃO AUXILIAR -----

def buscar_tabela(tabela_nova: str) -> dict:
    """Retorna a configuração da tabela do catálogo pelo nome novo (ex.: 'FAT_RASTREABILIDADE')."""
    for t in TABELAS:
        if t["tabela_nova"] == tabela_nova:
            return t
    raise KeyError(f"Tabela '{tabela_nova}' não encontrada no catálogo da Prata Rastreabilidade.")
