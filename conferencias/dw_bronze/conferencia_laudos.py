"""
Conferência Bronze x Sapiens -- compara COUNT(*) tabela por tabela.

Só leitura -- não corrige nem apaga nada. Mesmo padrão da conferência do
Comercial (comercial/bronze/conferencia.py). Só compara as tabelas de
TABELAS_DESTE_BLOCO (extrator.py) -- as 10 compartilhadas com o Comercial
não entram aqui, já são validadas pela conferência do Comercial.

NOTA: diferente do Comercial, reaproveita montar_query() (não
montar_query_pks()) para montar o lado Sapiens da comparação -- porque
USU_VZRASLAU não tem PK (chaves_pk=None), então montar_query_pks() não se
aplica a ela. montar_query(info, primeira_carga=True) funciona pras duas
situações (com e sem PK), já que não depende de chaves_pk -- só do
filtro de empresa/filial, sem janela de data. Como é só um COUNT(*), não
importa se a query de origem traz "SELECT *" em vez de só as colunas de
PK -- o resultado da contagem é o mesmo.

Uso (dentro da pasta bronze por enquanto -- mover para a pasta de
conferência dedicada ao levar pra VM, junto com os das outras áreas):
    python -m laudos_rma.bronze.conferencia
"""

# ----- IMPORTS -----

import traceback

from sqlalchemy import text

from laudos_rma.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query
from laudos_rma.bronze.tabelas import buscar_tabela
from laudos_rma.config.settings import schema_bronze
from core.db import get_engine


# ----- CONTAGENS -----

def contar_sapiens(engine, info: dict) -> int:
    """
    Conta o universo completo e atual da tabela no Sapiens, no mesmo
    escopo (empresa/filial reais) que a Bronze deveria ter -- sem janela
    de data. Funciona tanto para tabelas com PK quanto para USU_VZRASLAU
    (sem PK) -- montar_query(primeira_carga=True) não depende de chaves_pk.
    """
    query = f"SELECT COUNT(*) FROM ({montar_query(info, primeira_carga=True)})"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_bronze(engine, schema: str, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


# ----- CONFERÊNCIA DE UMA TABELA -----

def conferir_tabela(engine, nome_tabela: str) -> dict:
    info = buscar_tabela(nome_tabela)

    total_sapiens = contar_sapiens(engine, info)
    total_bronze = contar_bronze(engine, schema_bronze, nome_tabela)
    diferenca = total_bronze - total_sapiens

    status = "OK" if diferenca == 0 else "DIVERGENTE"

    return {
        "tabela": nome_tabela,
        "sapiens": total_sapiens,
        "bronze": total_bronze,
        "diferenca": diferenca,
        "status": status,
    }


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine()
    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        try:
            resultados.append(conferir_tabela(engine, nome))
        except Exception:
            print(f"\n  [ERRO] Falha ao conferir {nome}:")
            traceback.print_exc()
            resultados.append({"tabela": nome, "status": "ERRO"})

    print(f"\n{'='*78}")
    print(f"  {'TABELA':<20} {'SAPIENS':>12} {'BRONZE':>12} {'DIFERENÇA':>12}  STATUS")
    print(f"{'='*78}")

    for r in resultados:
        sapiens    = r.get("sapiens", "-")
        bronze     = r.get("bronze", "-")
        diferenca  = r.get("diferenca", "-")

        sapiens_fmt   = f"{sapiens:,}" if isinstance(sapiens, int) else sapiens
        bronze_fmt    = f"{bronze:,}" if isinstance(bronze, int) else bronze
        diferenca_fmt = f"{diferenca:+,}" if isinstance(diferenca, int) else diferenca

        print(f"  {r['tabela']:<20} {sapiens_fmt:>12} {bronze_fmt:>12} {diferenca_fmt:>12}  {r['status']}")

    divergentes = [r for r in resultados if r.get("status") == "DIVERGENTE"]
    erros       = [r for r in resultados if r.get("status") == "ERRO"]

    print(f"{'='*78}")
    print(
        f"  Total: {len(resultados)} tabelas | "
        f"{len(resultados) - len(divergentes) - len(erros)} OK | "
        f"{len(divergentes)} divergente(s) | {len(erros)} erro(s)"
    )
    print(f"{'='*78}")
