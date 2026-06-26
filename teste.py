"""
diagnostico_privilegios.py

NÃO faz parte do pipeline -- é só uma ferramenta de diagnóstico pontual.

Usa exatamente a MESMA forma de conexão que comercial/bronze/extrator.py usa
(core.db.get_engine(), mesmo .env) para responder, sem depender de relato de
terceiros:

    1. Em qual banco/host essa conexão Python está caindo de fato.
    2. Quais privilégios o usuário BIAQUARIO realmente tem NESSA conexão.

Rodar da raiz do projeto:
    python diagnostico_privilegios.py
"""

# ----- IMPORTS -----

from sqlalchemy import text

from core.db import get_engine


# ----- DIAGNÓSTICO -----

def main():
    engine = get_engine()

    with engine.connect() as conn:
        print("\n" + "=" * 60)
        print("  IDENTIFICAÇÃO DA CONEXÃO (de onde o script ESTÁ rodando)")
        print("=" * 60)
        resultado = conn.execute(text(
            "SELECT "
            "  USER AS usuario_logado, "
            "  SYS_CONTEXT('USERENV', 'DB_NAME')      AS db_name, "
            "  SYS_CONTEXT('USERENV', 'SERVER_HOST')  AS server_host, "
            "  SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS service_name, "
            "  SYS_CONTEXT('USERENV', 'INSTANCE_NAME') AS instance_name "
            "FROM DUAL"
        ))
        for linha in resultado:
            print(f"  Usuário logado   : {linha.usuario_logado}")
            print(f"  DB_NAME          : {linha.db_name}")
            print(f"  SERVER_HOST      : {linha.server_host}")
            print(f"  SERVICE_NAME     : {linha.service_name}")
            print(f"  INSTANCE_NAME    : {linha.instance_name}")

        print("\n" + "=" * 60)
        print("  PRIVILÉGIOS DO USUÁRIO NESSA CONEXÃO (USER_SYS_PRIVS)")
        print("=" * 60)
        resultado = conn.execute(text("SELECT * FROM USER_SYS_PRIVS ORDER BY PRIVILEGE"))
        privilegios = [linha.privilege for linha in resultado]

        if not privilegios:
            print("  Nenhum privilégio de sistema encontrado.")
        else:
            for p in privilegios:
                print(f"  - {p}")

        print("\n" + "=" * 60)
        print("  VEREDITO")
        print("=" * 60)
        if "CREATE ANY TABLE" in privilegios:
            print("  CREATE ANY TABLE está presente -- o grant chegou nessa conexão.")
            print("  Se o extrator ainda falhar, o problema é outro (não é privilégio).")
        else:
            print("  CREATE ANY TABLE NÃO aparece nessa conexão.")
            print("  O grant não chegou aqui -- compara o SERVER_HOST/DB_NAME acima")
            print("  com o banco onde o administrador confirmou ter rodado o GRANT.")


if __name__ == "__main__":
    main()