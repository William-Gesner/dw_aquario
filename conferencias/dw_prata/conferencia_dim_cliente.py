"""
Conferência DIM_CLIENTE (Prata) x USU_BVIACLIENTES (legado, schema
BIAQUARIO) -- compara os DADOS, não só a contagem.

Ver conferencia_dim_condicao_pagamento.py para a explicação completa da
técnica (MINUS nos dois sentidos). Tabela mais pesada das 7 (query com
CTE de ranking sobre todo o histórico de vendas) -- a conferência pode
demorar mais que as outras.

Só leitura -- não corrige nem apaga nada.

PRÉ-REQUISITO: GRANT SELECT ON BIAQUARIO.USU_BVIACLIENTES TO DW_PRATA;

Uso:
    python -m conferencias.conferencia_dim_cliente
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "DIM_CLIENTE"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_BVIACLIENTES"

COLUNAS = [
    "COD_GRUPO", "NOME_GRUPO", "CODCLI_BASE", "DOC_BASE", "NOME_BASE",
    "UF_BASE", "CIDADE_BASE", "DT_PRIMCOMPRA_BASE", "DT_SEGCOMPRA_BASE",
    "DT_TERCOMPRA_BASE", "DT_QUACOMPRA_BASE", "CODREP_ABERTURA",
    "REP_ABERTURA", "DT_ULTCOMPRA_BASE", "CODREP_ULTVENDA",
    "REP_ULT_VENDA", "COD_REGIONAL", "NOME_REGIONAL", "CODREP_ATUAL",
    "NOME_REP_ATUAL", "COD_CLIENTE", "DOC_CLIENTE", "NOME_CLIENTE",
    "TIPO_CLIENTE", "STATUS_CLIENTE", "COD_RAMO_ATIVIDADE",
    "DESC_RAMO_ATIVIDADE", "DT_CADASTRO", "DT_ULTIMA_ATUALIZACAO",
    "COD_MOD_NEGOCIO", "DESC_MOD_NEGOCIO", "COD_PERFIL", "DESC_PERFIL",
    "COD_GRADUACAO", "DESC_GRADUACAO", "CONSUMIDOR_FINAL",
    "CONTRIBUINTE_ICMS", "LIMITE_APROVADO", "DT_LIMITE_CREDITO",
    "VLR_LIMITE_CREDITO", "COD_COND_PGTO", "DESC_COND_PGTO",
    "COD_FORMA_PGTO", "DESC_FORMA_PGTO", "ENDERECO", "NUMERO",
    "COMPLEMENTO", "BAIRRO", "CEP", "CIDADE_CLIENTE", "UF_CLIENTE",
    "ENDERECO_COMPLETO", "TELEFONE", "TELEFONE2", "EMAIL",
    "COD_TRANSPORTADORA", "NOME_TRANSPORTADORA",
]


# ----- FUNÇÕES -----

def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def divergencias(conn, origem: str, destino: str) -> list:
    colunas_str = ", ".join(COLUNAS)
    query = f"""
        SELECT {colunas_str} FROM {origem}
        MINUS
        SELECT {colunas_str} FROM {destino}
    """
    return conn.execute(text(query)).fetchall()


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine_prata()

    prata_full = f"{SCHEMA_PRATA}.{TABELA_PRATA}"
    legado_full = f"{SCHEMA_LEGADO}.{TABELA_LEGADO}"

    with engine.connect() as conn:
        total_prata = contar(conn, SCHEMA_PRATA, TABELA_PRATA)
        total_legado = contar(conn, SCHEMA_LEGADO, TABELA_LEGADO)

        so_na_prata = divergencias(conn, prata_full, legado_full)
        so_no_legado = divergencias(conn, legado_full, prata_full)

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA -- {TABELA_PRATA} (Prata) x {TABELA_LEGADO} (legado)")
    print(f"{'='*70}")
    print(f"  Linhas na Prata  : {total_prata:>10,}")
    print(f"  Linhas no legado : {total_legado:>10,}")
    print(f"  Só na Prata (sem equivalente idêntico no legado)  : {len(so_na_prata):>6,}")
    print(f"  Só no legado (sem equivalente idêntico na Prata)  : {len(so_no_legado):>6,}")

    if not so_na_prata and not so_no_legado:
        print(f"\n  [OK] Dados idênticos -- todas as colunas de negócio batem.")
    else:
        print(f"\n  [DIVERGENTE] Diferenças encontradas.")

        if so_na_prata:
            print(f"\n  --- Amostra: só na Prata (até 10 de {len(so_na_prata)}) ---")
            for linha in so_na_prata[:10]:
                print(f"    {linha}")

        if so_no_legado:
            print(f"\n  --- Amostra: só no legado (até 10 de {len(so_no_legado)}) ---")
            for linha in so_no_legado[:10]:
                print(f"    {linha}")

    print(f"{'='*70}")
