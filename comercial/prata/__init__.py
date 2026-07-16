"""
Camada Prata do módulo Comercial.

Lê exclusivamente da Bronze (DW_BRONZE) -- nunca do Sapiens direto.
Replica fielmente as regras de negócio do legado (comercial/extract/*.py),
só trocando a origem e o nome da tabela de destino.

Diferente da Bronze (que usa um motor genérico, já que toda tabela segue
o mesmo molde "SELECT * WHERE CODEMP=1"), aqui cada tabela tem sua
própria lógica de negócio -- por isso é 1 arquivo por tabela, nome do
arquivo = nome da tabela em minúsculo (ex.: dim_cliente.py monta e
carrega DIM_CLIENTE). Ver tabelas.py para o catálogo/mapeamento
nome-antigo x nome-novo de cada uma.

Estratégia de carga: fixa por tabela (upsert ou full_reload), igual já
era no legado -- NÃO existe a decisão automática "1ª carga full, depois
incremental por janela" que a Bronze tem (ver core/loader.py). A query
de negócio roda inteira a cada execução; quem decide o que é novo/mudou
é o MERGE (upsert) ou o DROP+recarga (full_reload).
"""
