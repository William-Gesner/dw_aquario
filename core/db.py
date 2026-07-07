"""
Conexão com o banco Oracle.

Centraliza a criação dos engines SQLAlchemy para Bronze e Prata.
Como ambos os schemas estão no mesmo banco físico (dbprod/srvoda01),
a diferença entre eles é apenas o usuário que conecta:

    get_engine_bronze() -> conecta como DW_BRONZE
    get_engine_prata()  -> conecta como DW_PRATA

Cada engine é um singleton — criado uma vez e reutilizado em todas
as chamadas subsequentes, evitando múltiplas conexões desnecessárias.

get_engine_controladoria() é diferente dos dois acima: conecta num
servidor Oracle FISICAMENTE SEPARADO (banco de Controladoria,
172.16.0.123), usado hoje só pelo OPEX como origem. Como não é o mesmo
banco físico do destino, tem host/porta/service_name E credencial
próprios -- não dá pra reaproveitar usuário/senha do Bronze, porque esse
usuário só existe no servidor principal. Área que usar esse engine só o
usa para LEITURA (a escrita continua sempre em get_engine_bronze()); ver
core/loader.py -> carregar_bronze(engine_escrita=...) para o motivo de
precisar de dois engines nesse caso (sem DB LINK entre os servidores).

Variáveis de ambiente necessárias (.env):
    ORACLE_HOST          : host do banco (ex.: dbprod)
    ORACLE_PORT          : porta do listener (ex.: 1521)
    ORACLE_SERVICE_NAME  : service name (ex.: dbprod)
    ORACLE_CLIENT_LIB_DIR: caminho do Oracle Instant Client
    ORACLE_USER          : usuário Bronze (ex.: DW_BRONZE)
    ORACLE_PASSWORD      : senha Bronze
    ORACLE_USER_PRATA    : usuário Prata (ex.: DW_PRATA)
    ORACLE_PASSWORD_PRATA: senha Prata

    # Origem exclusiva do OPEX -- servidor de Controladoria
    ORACLE_HOST_CONT         : host do banco de Controladoria (ex.: 172.16.0.123)
    ORACLE_PORT_CONT         : porta do listener
    ORACLE_SERVICE_NAME_CONT : service name (ex.: dbprod)
    ORACLE_USER_CONT         : usuário de leitura no banco de Controladoria
    ORACLE_PASSWORD_CONT     : senha correspondente
"""

# ----- IMPORTS -----

import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# ----- CONFIGURAÇÕES INICIAIS -----

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# ----- SINGLETONS -----

_engine_bronze:        Engine | None = None
_engine_prata:         Engine | None = None
_engine_controladoria: Engine | None = None
_client_initialized = False


# ----- FUNÇÕES INTERNAS -----

def _init_client() -> None:
    """Inicializa o Oracle Instant Client (apenas uma vez)."""
    global _client_initialized
    if not _client_initialized:
        oracledb.init_oracle_client(lib_dir=os.environ["ORACLE_CLIENT_LIB_DIR"])
        _client_initialized = True


def _criar_engine(usuario: str, senha: str, host: str, porta: int, service_name: str) -> Engine:
    """Cria um engine SQLAlchemy para o banco Oracle."""
    _init_client()
    return create_engine(
        f"oracle+oracledb://{usuario}:{senha}@{host}:{porta}/?service_name={service_name}"
    )


# ----- FUNÇÕES PÚBLICAS -----

def get_engine_bronze() -> Engine:
    """Retorna o engine conectado como DW_BRONZE (singleton) -- servidor principal."""
    global _engine_bronze
    if _engine_bronze is None:
        _engine_bronze = _criar_engine(
            usuario=os.environ["ORACLE_USER"],
            senha=os.environ["ORACLE_PASSWORD"],
            host=os.environ["ORACLE_HOST"],
            porta=int(os.environ["ORACLE_PORT"]),
            service_name=os.environ["ORACLE_SERVICE_NAME"],
        )
    return _engine_bronze


def get_engine_prata() -> Engine:
    """Retorna o engine conectado como DW_PRATA (singleton) -- servidor principal."""
    global _engine_prata
    if _engine_prata is None:
        _engine_prata = _criar_engine(
            usuario=os.environ["ORACLE_USER_PRATA"],
            senha=os.environ["ORACLE_PASSWORD_PRATA"],
            host=os.environ["ORACLE_HOST"],
            porta=int(os.environ["ORACLE_PORT"]),
            service_name=os.environ["ORACLE_SERVICE_NAME"],
        )
    return _engine_prata


def get_engine_controladoria() -> Engine:
    """
    Retorna o engine de LEITURA do banco de Controladoria (singleton) --
    servidor Oracle separado do principal, usado hoje só pelo OPEX.

    Só serve para ler (SAPIENS.* de lá) -- a escrita na Bronze continua
    sempre via get_engine_bronze(), no servidor principal.
    """
    global _engine_controladoria
    if _engine_controladoria is None:
        _engine_controladoria = _criar_engine(
            usuario=os.environ["ORACLE_USER_CONT"],
            senha=os.environ["ORACLE_PASSWORD_CONT"],
            host=os.environ["ORACLE_HOST_CONT"],
            porta=int(os.environ["ORACLE_PORT_CONT"]),
            service_name=os.environ["ORACLE_SERVICE_NAME_CONT"],
        )
    return _engine_controladoria


def get_engine() -> Engine:
    """
    Atalho para compatibilidade — retorna o engine Bronze.
    Scripts que chamavam get_engine() continuam funcionando sem alteração.
    """
    return get_engine_bronze()