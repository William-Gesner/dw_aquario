from dotenv import load_dotenv
import os

load_dotenv(r'C:\Users\roqt\Desktop\dw_aquario\.env', override=True)

import oracledb
from sqlalchemy import create_engine, text

oracledb.init_oracle_client(lib_dir=os.environ['ORACLE_CLIENT_LIB_DIR'])

engine = create_engine(
    f"oracle+oracledb://{os.environ['ORACLE_USER']}:{os.environ['ORACLE_PASSWORD']}"
    f"@{os.environ['ORACLE_HOST']}:{os.environ['ORACLE_PORT']}"
    f"/?service_name={os.environ['ORACLE_SERVICE_NAME']}"
)

with engine.begin() as conn:
    conn.execute(text('CREATE TABLE DW_BRONZE.TESTE_OK (ID NUMBER)'))
    print('CREATE OK')
    conn.execute(text('INSERT INTO DW_BRONZE.TESTE_OK VALUES (1)'))
    print('INSERT OK')

with engine.connect() as conn:
    r = conn.execute(text('SELECT COUNT(*) FROM DW_BRONZE.TESTE_OK'))
    print('SELECT OK - linhas:', r.scalar())

with engine.begin() as conn:
    conn.execute(text('DROP TABLE DW_BRONZE.TESTE_OK'))
    print('DROP OK')

print('\nTudo funcionando! Conexão DW_BRONZE está pronta.')