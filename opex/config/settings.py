"""
Carregamento e exposição das variáveis de ambiente do módulo OPEX.

Variáveis de ambiente necessárias (.env), além das já usadas por outras
áreas (ORACLE_SCHEMA_BRONZE, ORACLE_SCHEMA_PRATA, ORACLE_CLIENT_LIB_DIR):

    # Conexão com o banco de Controladoria (origem exclusiva do OPEX --
    # servidor Oracle SEPARADO do ERP principal). Ver core/db.py ->
    # get_engine_controladoria().
    ORACLE_HOST_CONT         : host do banco de Controladoria (ex.: 172.16.0.123)
    ORACLE_PORT_CONT         : porta do listener (geralmente 1521)
    ORACLE_SERVICE_NAME_CONT : service name (ex.: dbprod)
    ORACLE_USER_CONT         : usuário de leitura no banco de Controladoria
    ORACLE_PASSWORD_CONT     : senha correspondente
"""

# ----- IMPORTS -----

import os
from pathlib import Path

from dotenv import load_dotenv

# ----- CONFIGURAÇÃO DA RAIZ DO PROJETO -----

# Detecta a raiz do projeto (3 níveis acima: settings.py -> config -> opex -> raiz)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", _PROJECT_ROOT))

# ----- CARREGAMENTO DO .ENV -----

load_dotenv(PROJECT_ROOT / ".env")

# ----- SCHEMAS DE DESTINO — MIGRAÇÃO MEDALHÃO -----

schema_bronze = os.environ["ORACLE_SCHEMA_BRONZE"]
schema_prata = os.environ["ORACLE_SCHEMA_PRATA"]

# ----- VARIÁVEIS DE INFRAESTRUTURA -----

ORACLE_CLIENT_LIB_DIR = os.environ["ORACLE_CLIENT_LIB_DIR"]

# ----- FILTRO ESTRUTURAL DO OPEX — EXCEÇÃO DOCUMENTADA -----

# Diferente das demais áreas (CODEMP = 1 sempre -- ver
# comercial/config/settings.py), o OPEX consolida dados de DUAS razões
# sociais do mesmo grupo Aquário. Confirmado com o cliente em 07/07/2026.
# Vale só para as tabelas de Controladoria que têm coluna de empresa
# (E044CCU, USU_T650CUS, USU_T650ORC) -- E043PCM e R910USU são globais,
# sem CODEMP (confirmado via ALL_TAB_COLUMNS em 07/07/2026).
CODEMP_AQUARIO_OPEX = (1, 50)

# ----- JANELA DE INCREMENTAL DA BRONZE -----

# Mesma regra do resto do projeto (ver core/loader.py -> carregar_bronze()).
JANELA_INCREMENTAL_DIAS = 60
