"""
Conferência DIM_CONDICAO_PAGAMENTO (Prata) x USU_VBIACONDPGTO (legado,
schema BIAQUARIO) -- compara os DADOS, não só a contagem.

Diferente da conferência da Bronze (só compara COUNT(*) contra o Sapiens,
porque a Bronze é cópia crua sem transformação), a Prata aplica regra de
negócio -- então bater a quantidade de linhas não é suficiente, precisa
bater o CONTEÚDO de cada coluna também.

Usa MINUS nos dois sentidos (Prata -> legado e legado -> Prata): se as
duas consultas não devolverem NENHUMA linha, os dois lados têm exatamente
as mesmas linhas com exatamente os mesmos valores -- é a forma padrão em
SQL de provar que dois conjuntos de dados são idênticos, sem precisar de
lógica de comparação campo a campo.

A coluna técnica DW_DATA_PROCESSAMENTO (metadado da Prata) é excluída de
propósito -- não existe no legado e não faz parte do resultado de
negócio que precisa bater.

Só leitura -- não corrige nem apaga nada.

PRÉ-REQUISITO: a engine usada aqui precisa enxergar os dois schemas
(DW_PRATA e BIAQUARIO). Se faltar grant no legado, rode:
    GRANT SELECT ON BIAQUARIO.USU_VBIACONDPGTO TO DW_PRATA;

Uso:
    python -m conferencias.conferencia_dim_condicao_pagamento
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine_prata

# ----- CONFIGURAÇÃO -----

SCHEMA_PRATA = "DW_PRATA"
TABELA_PRATA = "DIM_CONDICAO_PAGAMENTO"

SCHEMA_LEGADO = "BIAQUARIO"
TABELA_LEGADO = "USU_VBIACONDPGTO"

# Colunas de negócio -- exclui DW_DATA_PROCESSAMENTO (só existe na Prata)
COLUNAS = [
    "CODCPG", "DESCPG", "DESCPGTO", "ABREVCPG", "PRZMED",
    "QTDPARC", "SITCPG", "SITCPG_DESC", "DATCAD", "ULTATU",
]


# ----- FUNÇÕES -----

def contar(conn, schema: str, tabela: str) -> int:
    return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


def divergencias(conn, origem: str, destino: str) -> list:
    """
    Retorna as linhas que existem em `origem` mas não têm equivalente
    IDÊNTICO (mesma chave + mesmos valores) em `destino`.
    origem/destino: 'schema.tabela' completos.
    """
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
