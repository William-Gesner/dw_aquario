"""
Conferência Bronze x Sapiens -- compara COUNT(*) tabela por tabela.

Só leitura -- não corrige nem apaga nada. Serve pra você validar, tabela por
tabela, se a Bronze bate com o Sapiens antes de considerar a migração de
uma área "fechada" (ver processo de validação combinado: só avança pra
próxima tabela/área depois de bronze validada).

Reaproveita montar_query_pks() (comercial/bronze/extrator.py) pra montar o
lado Sapiens da comparação -- mesma lógica de escopo (tem_codemp/
coluna_codemp, tem_codfil/coluna_codfil), SEM janela de data, ou seja, o
universo completo e atual do Sapiens. É o mesmo escopo que a Bronze deveria
refletir (carga inicial full + incremental + sweep diário de órfãos), então
count(Sapiens) == count(Bronze) é o resultado esperado quando tudo está em
dia.

Interpretação de uma diferença != 0:
    - Pequena (1-2 linhas) rodando em horário comercial: pode ser só uma
      transação nova entre a leitura de um lado e do outro (corrida normal,
      não é bug). Rode de novo pra confirmar se persiste.
    - Diferença maior ou persistente: investigar. Causas prováveis --
      1ª carga incompleta, incremental que falhou silenciosamente em algum
      ciclo, ou (se for logo após corrigir uma tabela) órfãos que ainda não
      foram varridos porque o sweep diário (--sweep-orfaos) ainda não rodou
      hoje.

Uso:
    python -m comercial.bronze.conferencia
"""

# ----- IMPORTS -----

import traceback

from sqlalchemy import text

from comercial.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query_pks
from comercial.bronze.tabelas import buscar_tabela
from comercial.config.settings import schema_bronze
from core.db import get_engine


# ----- CONTAGENS -----

def contar_sapiens(engine, info: dict) -> int:
    """
    Conta o universo completo e atual da tabela no Sapiens, no mesmo escopo
    (CODEMP/CODFIL reais) que a Bronze deveria ter -- sem janela de data.
    """
    query = f"SELECT COUNT(*) FROM ({montar_query_pks(info)})"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_bronze(engine, schema: str, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


# ----- CONFERÊNCIA DE UMA TABELA -----

def conferir_tabela(engine, nome_tabela: str) -> dict:
    info = buscar_tabela(nome_tabela)

    if info["chaves_pk"] is None:
        print(f"  [AVISO] {nome_tabela} não tem PK (é view) -- fora desta conferência.")
        return {"tabela": nome_tabela, "status": "PULADA"}

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
    puladas     = [r for r in resultados if r.get("status") == "PULADA"]
    erros       = [r for r in resultados if r.get("status") == "ERRO"]

    print(f"{'='*78}")
    print(
        f"  Total: {len(resultados)} tabelas | "
        f"{len(resultados) - len(divergentes) - len(puladas) - len(erros)} OK | "
        f"{len(divergentes)} divergente(s) | {len(puladas)} pulada(s) | {len(erros)} erro(s)"
    )
    print(f"{'='*78}")
