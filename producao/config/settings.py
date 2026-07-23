"""
Carregamento e exposição das variáveis de ambiente do módulo Produção.

Mesmo servidor Oracle do Comercial/Laudos RMA (não precisa de credencial
separada, diferente do OPEX) -- usa core.db.get_engine() normalmente.

Variáveis de ambiente necessárias (.env): já cobertas pelas usadas por
outras áreas (ORACLE_SCHEMA_BRONZE, ORACLE_SCHEMA_PRATA,
ORACLE_CLIENT_LIB_DIR, ORACLE_USER/ORACLE_PASSWORD).
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> producao -> raiz)
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

# Aquário = CODEMP 1 sempre (regra padrão do projeto -- sem exceção aqui,
# diferente do OPEX).
CODEMP_AQUARIO = 1
CODFIL_AQUARIO = 1

# ----- JANELA DE INCREMENTAL DA BRONZE -----

JANELA_INCREMENTAL_DIAS = 60

# ----- CORTE DE DATA DA PRATA -----

# Decisão confirmada com o usuário em 21/07/2026: TODAS as tabelas FATO
# da Produção com grão de data usam 01/01/2021 -- inclusive as que o
# legado cortava em 01/01/2018 (FAT_PARADAS_PRODUCAO, blocos DESEMPENHO/
# CONSUMO de FAT_DESEMPENHO_PRODUCAO) e as que o legado não cortava
# nenhuma (FAT_CUSTO_CC_PRODUCAO, bloco CUSTO_CC de
# FAT_DESEMPENHO_PRODUCAO) -- diferente da regra geral da Fase 2 (só
# aplicar corte novo quando o legado não tinha nenhum), aqui foi pedido
# explicitamente o padrão único de 2021 pra toda a área.
DATA_CORTE_PRODUCAO = "01/01/2021"

# ----- JANELA DE BUSCA DO APONTAMENTO DE REFERÊNCIA (bloco CONSUMO) -----

# NÃO confundir com DATA_CORTE_PRODUCAO acima -- são decisões diferentes.
# DATA_CORTE_PRODUCAO decide QUAIS REGISTROS entram no histórico (regra de
# negócio, 21/07/2026). Esta aqui é o alcance de uma busca TÉCNICA dentro
# do bloco CONSUMO de fat_desempenho_producao.py: quando não há apontamento
# (E900EOQ) com data exata igual ao movimento, a query cai num fallback que
# procura "o apontamento mais próximo dessa OP", dentro desta janela.
#
# BUG CORRIGIDO (23/07/2026): essa busca usava DATA_CORTE_PRODUCAO (2021)
# até essa correção -- registros de consumo logo após 01/01/2021 (ex.:
# 05/01/2021) não achavam o apontamento de referência (dez/2020), porque a
# busca não enxergava nada antes de 2021, e a Prata voltava com DATREA nulo
# onde o legado (que usa DATA_INICIO_HISTORICO = 2018 nesse mesmo ponto,
# ver aquario/producao/extract/vbidesempenho.py) achava o valor certo.
# Corrigido usando o mesmo valor do legado aqui -- mantém as duas buscas
# (a de negócio, 2021, e a técnica, 2018) desacopladas de propósito.
DATA_MINIMA_APONTAMENTO_CONSUMO = "01/01/2018"

# ----- CAMINHOS DE ARQUIVOS EXTERNOS -----

# Pasta local na VM (drive Z:) onde ficam os arquivos Excel -- mesmo
# caminho já usado pelo legado (producao/config/settings.py).
PASTA_DADOS_EXTERNOS = Path(r"Z:\Dados")

# TempoDisponivelCC.xlsx -- usado por DOIS módulos (Estoque e Produção).
#   Aba BD : meta de utilização por CC e dia   -> vbiutilizacaometa.py (ESTE módulo)
#   Aba CP : custo padrão por produto          -> vbicustopadrao.py    (ESTE módulo e Estoque)
EXCEL_TEMPO_DISPONIVEL = PASTA_DADOS_EXTERNOS / "TempoDisponivelCC.xlsx"
