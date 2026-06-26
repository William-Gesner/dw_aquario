"""
Pacote de infraestrutura compartilhada do projeto aquario-bi.

Contém os módulos reutilizados por todas as áreas de negócio:
    - db.py        : fábrica de conexão Oracle (get_engine)
    - dtype_map.py : mapeamento de tipos pandas → SQLAlchemy/Oracle
    - loader.py    : estratégias de carga (upsert e full_reload)
"""