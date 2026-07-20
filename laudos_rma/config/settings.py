"""
Carregamento e exposição das variáveis de ambiente do módulo Laudos RMA.

Mesmo servidor Oracle do Comercial (não precisa de credencial separada,
diferente do OPEX) -- usa core.db.get_engine_bronze() normalmente.

Variáveis de ambiente necessárias (.env): já cobertas pelas usadas por
outras áreas (ORACLE_SCHEMA_BRONZE, ORACLE_SCHEMA_PRATA,
ORACLE_CLIENT_LIB_DIR, ORACLE_USER/ORACLE_PASSWORD).
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> laudos_rma -> raiz)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", _PROJECT_ROOT))

# ----- CARREGAMENTO DO .ENV -----

load_dotenv(PROJECT_ROOT / ".env")

# ----- SCHEMAS DE DESTINO — MIGRAÇÃO MEDALHÃO -----

schema_bronze = os.environ["ORACLE_SCHEMA_BRONZE"]
schema_prata = os.environ["ORACLE_SCHEMA_PRATA"]

# ----- VARIÁVEIS DE INFRAESTRUTURA -----

ORACLE_CLIENT_LIB_DIR = os.environ["ORACLE_CLIENT_LIB_DIR"]

# ----- FILTROS ESTRUTURAIS FIXOS DO PROJETO AQUÁRIO -----

# Aquário = CODEMP 1 sempre (regra padrão do projeto -- diferente do OPEX,
# que tem exceção documentada CODEMP IN (1, 50) só pras tabelas de
# Controladoria; ver opex/config/settings.py).
CODEMP_AQUARIO = 1
CODFIL_AQUARIO = 1

# ----- JANELA DE INCREMENTAL DA BRONZE -----

JANELA_INCREMENTAL_DIAS = 60

# ----- CORTE DE DATA DA PRATA -----

# Corte já existente no legado (vbilaudos.py e vbivendas.py filtram
# DATENT/DATEMI >= 01/01/2023) -- MANTIDO, não é o mesmo corte de
# 01/01/2021 usado no Comercial. Regra 2 da Fase 2: só aplicamos um corte
# novo quando o legado não tinha nenhum; aqui o legado já cortava em
# 2023, então preservamos exatamente esse valor para não trazer mais
# histórico do que o Power BI já mostra hoje.
DATA_CORTE_LAUDOS = "01/01/2023"

# ----- CAMINHOS DE ARQUIVOS EXTERNOS -----

# Pasta local na VM (drive Z:) onde ficam os arquivos Excel do projeto.
# NÃO mover os arquivos -- são alimentados manualmente pelo time de
# negócio. Mesmo caminho usado pelo legado (aquario/laudos_rma/config/
# settings.py) -- as 3 tabelas de Excel continuam lendo direto daqui,
# sem passar pela Bronze (não há Bronze de Excel neste projeto).
PASTA_DADOS_EXTERNOS = Path(r"Z:\Dados")

# DefeitosProdutosRMA.xlsx -- reclassificação de defeitos e produtos.
#   Aba DescDefeitos    : reclassificação de defeitos por produto  -> dim_reclassif_defeitos.py
#   Aba ClassifProdutos : classificação e situação dos produtos    -> dim_reclassif_produtos.py
EXCEL_DEFEITOS_PRODUTOS = PASTA_DADOS_EXTERNOS / "DefeitosProdutosRMA.xlsx"

# IndiceRMA.xlsx -- estrutura hierárquica do Índice RMA (Pai/ID/Nome).
#   Aba Planilha1 : hierarquia do índice -> dim_indice_rma.py
EXCEL_INDICE_RMA = PASTA_DADOS_EXTERNOS / "IndiceRMA.xlsx"
