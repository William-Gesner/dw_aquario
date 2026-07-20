"""
Carregamento e exposição das variáveis de ambiente do módulo Comercial.

Variáveis de ambiente necessárias (.env):
    ORACLE_USER            : usuário do banco Oracle
    ORACLE_PASSWORD        : senha do banco Oracle
    ORACLE_HOST            : host/IP do servidor Oracle
    ORACLE_PORT            : porta do listener Oracle (geralmente 1521)
    ORACLE_SERVICE_NAME    : nome do serviço Oracle
    ORACLE_SCHEMA_BRONZE   : schema da camada Bronze (NOVO — ex.: DW_BRONZE)
    ORACLE_SCHEMA_PRATA    : schema da camada Prata (NOVO — ex.: DW_PRATA)
    ORACLE_CLIENT_LIB_DIR  : caminho para o Oracle Instant Client na VM
    PROJECT_ROOT           : (opcional) sobrescreve a detecção automática da raiz
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> comercial -> raiz)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", _PROJECT_ROOT))

# ----- CARREGAMENTO DO .ENV -----

load_dotenv(PROJECT_ROOT / ".env")

# ----- VARIÁVEIS DE CONEXÃO ORACLE -----

usuario = os.environ["ORACLE_USER"]
senha = os.environ["ORACLE_PASSWORD"]
host = os.environ["ORACLE_HOST"]
porta = int(os.environ["ORACLE_PORT"])
service_name = os.environ["ORACLE_SERVICE_NAME"]

# ----- SCHEMAS DE DESTINO — MIGRAÇÃO MEDALHÃO (NOVO) -----

schema_bronze = os.environ["ORACLE_SCHEMA_BRONZE"]
schema_prata = os.environ["ORACLE_SCHEMA_PRATA"]

# ----- VARIÁVEIS DE INFRAESTRUTURA -----

ORACLE_CLIENT_LIB_DIR = os.environ["ORACLE_CLIENT_LIB_DIR"]

# ----- FILTROS ESTRUTURAIS FIXOS DO PROJETO AQUÁRIO -----

# Aquário = CODEMP 1 sempre. O Sapiens é compartilhado com outras empresas
# do grupo (mesmo banco) -- esse filtro é estrutural, não incidental.
CODEMP_AQUARIO = 1

# Única filial ativa hoje. Pode haver outras no futuro.
CODFIL_AQUARIO = 1

# ----- JANELA DE INCREMENTAL DA BRONZE -----

# Válida para TODAS as 33 tabelas da Bronze do Comercial, sem exceção
# (ver core/loader.py -> carregar_bronze()).
JANELA_INCREMENTAL_DIAS = 60

# ----- CORTE DE DATA DA PRATA -----

# Corte fixo pras tabelas FATO da Prata do Comercial (Regra 2 da Fase 2:
# dimensão nunca tem corte). Mesmo corte que o legado já tinha para
# faturamento -- não é mudança de resultado.
DATA_CORTE_FATURAMENTO = "01/01/2021"