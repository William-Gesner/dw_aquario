"""
Conferência Bronze x Sapiens -- Laudos RMA.

Reescrita em 17/07/2026 no mesmo padrão do Comercial (ver
conferencia_comercial.py para o histórico completo do porquê) -- a versão
anterior tinha os mesmos 2 pontos cegos:

    a) Contagem usava o MESMO filtro (tem_codemp/tem_codfil) do catálogo
       pros dois lados -- então o bug de tem_codfil=True em USU_TLAUITE/
       USU_TLAUGER/USU_VZRASLAU (corrigido em 17/07/2026, ver
       laudos_rma/bronze/tabelas.py) nunca teria aparecido aqui.
    b) Só comparava COUNT(*) -- nunca pegaria divergência de valor num
       registro presente dos dois lados.

NOTA: como a versão original, usa montar_query(primeira_carga=True) --
não montar_query_pks() -- para montar o lado Sapiens da contagem, porque
USU_VZRASLAU não tem PK física (chaves_pk=None). montar_query() não
depende de chaves_pk (só do filtro empresa/filial), então funciona igual
para as 9 tabelas desta área, com ou sem PK -- não precisa pular nenhuma.

Só leitura -- não corrige nem apaga nada.

Uso:
    python -m conferencias.dw_bronze.conferencia_laudos
        -> contagem (rápida) nas tabelas do catálogo.

    python -m conferencias.dw_bronze.conferencia_laudos --conteudo USU_TLAUITE
        -> conteúdo (MINUS, dado a dado) só dessa tabela.

Interpretação: ver docstring de conferencia_comercial.py (mesmas regras
de leitura da coluna DIFERENÇA e do ALERTA de filial).
"""

# ----- IMPORTS -----

import sys
import traceback

from sqlalchemy import text

from laudos_rma.bronze.extrator import TABELAS_DESTE_BLOCO, montar_query
from laudos_rma.bronze.tabelas import TABELAS_MULTI_ESCRITOR, buscar_tabela
from laudos_rma.config.settings import CODEMP_AQUARIO, schema_bronze
from core.db import get_engine


# ----- CONTAGENS -----

def contar_sapiens(engine, info: dict) -> int:
    """
    Universo completo e atual da tabela/view no Sapiens, no escopo do
    catálogo. Funciona tanto para tabelas com PK quanto para USU_VZRASLAU
    (sem PK) -- montar_query(primeira_carga=True) não depende de chaves_pk.
    """
    query = f"SELECT COUNT(*) FROM ({montar_query(info, primeira_carga=True)})"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_sapiens_sem_filial(engine, info: dict) -> int | None:
    """
    Contagem do Sapiens só com CODEMP, ignorando CODFIL mesmo quando o
    catálogo diz tem_codfil=True. Puramente informativa -- None quando
    tem_codemp=False.
    """
    if not info["tem_codemp"]:
        return None

    tabela = info["tabela"]
    coluna_codemp = info.get("coluna_codemp", "CODEMP")
    query = f"SELECT COUNT(*) FROM SAPIENS.{tabela} WHERE {coluna_codemp} = {CODEMP_AQUARIO}"
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()


def contar_bronze(engine, schema: str, tabela: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {schema}.{tabela}")).scalar()


# ----- COLUNAS REAIS (cópia crua -- mesma lista do Sapiens) -----

def colunas_reais(engine, tabela: str) -> list[str]:
    """Lista as colunas reais da tabela, na ordem física do Sapiens (ALL_TAB_COLUMNS)."""
    query = """
        SELECT column_name
        FROM ALL_TAB_COLUMNS
        WHERE owner = 'SAPIENS' AND table_name = :tabela
        ORDER BY column_id
    """
    with engine.connect() as conn:
        linhas = conn.execute(text(query), {"tabela": tabela}).fetchall()
    if not linhas:
        raise ValueError(
            f"Nenhuma coluna encontrada para SAPIENS.{tabela} em ALL_TAB_COLUMNS."
        )
    return [linha[0] for linha in linhas]


# ----- CONFERÊNCIA DE CONTAGEM (rápida, todas as tabelas) -----

def conferir_tabela(engine, nome_tabela: str) -> dict:
    info = buscar_tabela(nome_tabela)

    total_sapiens = contar_sapiens(engine, info)
    total_bronze = contar_bronze(engine, schema_bronze, nome_tabela)
    total_sapiens_sem_filial = contar_sapiens_sem_filial(engine, info)
    diferenca = total_bronze - total_sapiens

    # Tabelas com mais de um escritor (ver TABELAS_MULTI_ESCRITOR): Bronze
    # > universo próprio do Laudos RMA é esperado (fatia extra vem de
    # outra área) -- só Bronze < universo próprio é erro de verdade.
    if nome_tabela in TABELAS_MULTI_ESCRITOR and diferenca > 0:
        status = "OK"
    else:
        status = "OK" if diferenca == 0 else "DIVERGENTE"

    alerta_filial = bool(
        info.get("tem_codfil")
        and total_sapiens_sem_filial is not None
        and total_sapiens_sem_filial != total_sapiens
    )

    return {
        "tabela": nome_tabela,
        "sapiens": total_sapiens,
        "sapiens_sem_filial": total_sapiens_sem_filial,
        "bronze": total_bronze,
        "diferenca": diferenca,
        "status": status,
        "alerta_filial": alerta_filial,
        "multi_escritor": nome_tabela in TABELAS_MULTI_ESCRITOR and diferenca > 0,
    }


# ----- CONFERÊNCIA DE CONTEÚDO (dado a dado, 1 tabela por vez) -----

def conferir_conteudo(engine, nome_tabela: str) -> None:
    """MINUS nos dois sentidos, todas as colunas reais, Bronze x Sapiens."""
    info = buscar_tabela(nome_tabela)

    colunas = colunas_reais(engine, nome_tabela)
    colunas_str = ", ".join(colunas)

    query_sapiens = montar_query(info, primeira_carga=True)
    query_bronze = f"SELECT {colunas_str} FROM {schema_bronze}.{nome_tabela}"

    print(f"\n{'='*70}")
    print(f"  CONFERÊNCIA DE CONTEÚDO -- {nome_tabela} (Bronze x Sapiens)")
    print(f"{'='*70}")
    print(f"  Query Sapiens: {query_sapiens}")

    with engine.connect() as conn:
        so_no_sapiens = conn.execute(
            text(f"{query_sapiens}\nMINUS\n{query_bronze}")
        ).fetchall()
        so_na_bronze = conn.execute(
            text(f"{query_bronze}\nMINUS\n{query_sapiens}")
        ).fetchall()

    print(f"\n  Só no Sapiens (ausente ou desatualizado na Bronze) : {len(so_no_sapiens):>8,}")
    print(f"  Só na Bronze (sem equivalente idêntico no Sapiens) : {len(so_na_bronze):>8,}")

    if not so_no_sapiens and not so_na_bronze:
        print(f"\n  [OK] Conteúdo idêntico.")
    else:
        print(f"\n  [DIVERGENTE]")
        if so_no_sapiens:
            print(f"\n  --- Amostra: só no Sapiens (até 10 de {len(so_no_sapiens)}) ---")
            for linha in so_no_sapiens[:10]:
                print(f"    {dict(zip(colunas, linha))}")
        if so_na_bronze:
            print(f"\n  --- Amostra: só na Bronze (até 10 de {len(so_na_bronze)}) ---")
            for linha in so_na_bronze[:10]:
                print(f"    {dict(zip(colunas, linha))}")
    print(f"{'='*70}")


# ----- EXECUÇÃO -----

if __name__ == "__main__":
    engine = get_engine()

    if "--conteudo" in sys.argv:
        idx = sys.argv.index("--conteudo")
        try:
            nome_tabela = sys.argv[idx + 1]
        except IndexError:
            print("  Uso: python -m conferencias.dw_bronze.conferencia_laudos --conteudo NOME_TABELA")
            sys.exit(1)

        conferir_conteudo(engine, nome_tabela)
        sys.exit(0)

    resultados = []

    for nome in TABELAS_DESTE_BLOCO:
        try:
            resultados.append(conferir_tabela(engine, nome))
        except Exception:
            print(f"\n  [ERRO] Falha ao conferir {nome}:")
            traceback.print_exc()
            resultados.append({"tabela": nome, "status": "ERRO"})

    print(f"\n{'='*92}")
    print(
        f"  {'TABELA':<20} {'SAPIENS':>12} {'S/ FILIAL':>12} {'BRONZE':>12} "
        f"{'DIFERENÇA':>12}  STATUS      ALERTA"
    )
    print(f"{'='*92}")

    for r in resultados:
        sapiens = r.get("sapiens", "-")
        sapiens_sf = r.get("sapiens_sem_filial")
        bronze = r.get("bronze", "-")
        diferenca = r.get("diferenca", "-")

        sapiens_fmt = f"{sapiens:,}" if isinstance(sapiens, int) else sapiens
        sapiens_sf_fmt = f"{sapiens_sf:,}" if isinstance(sapiens_sf, int) else "-"
        bronze_fmt = f"{bronze:,}" if isinstance(bronze, int) else bronze
        diferenca_fmt = f"{diferenca:+,}" if isinstance(diferenca, int) else diferenca
        alerta_fmt = "FILIAL?" if r.get("alerta_filial") else ("MULTI-ESCRITOR" if r.get("multi_escritor") else "")

        print(
            f"  {r['tabela']:<20} {sapiens_fmt:>12} {sapiens_sf_fmt:>12} {bronze_fmt:>12} "
            f"{diferenca_fmt:>12}  {r['status']:<10}  {alerta_fmt}"
        )

    divergentes = [r for r in resultados if r.get("status") == "DIVERGENTE"]
    erros = [r for r in resultados if r.get("status") == "ERRO"]
    alertas = [r for r in resultados if r.get("alerta_filial")]

    print(f"{'='*92}")
    print(
        f"  Total: {len(resultados)} tabelas | "
        f"{len(resultados) - len(divergentes) - len(erros)} OK | "
        f"{len(divergentes)} divergente(s) | {len(erros)} erro(s) | "
        f"{len(alertas)} com alerta de filial"
    )
    print(f"{'='*92}")
