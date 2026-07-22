# Orquestrador do módulo Comercial do BI Aquário -- PROJETO NOVO (Bronze/Prata).
#
# Executa sequencialmente: 1) o extrator da Bronze, 2) todas as tabelas da
# Prata do Comercial, em loop contínuo. Mesma estrutura do orquestrador
# legado (aquario/comercial/orquestrador.py), adaptada pra 2 etapas em vez
# de 1 (a Bronze não existia no legado).
#
# AGENDAMENTO: os ciclos começam SEMPRE em horários fixos, múltiplos de
# INTERVALO_ENTRE_CICLOS (10 minutos), e APENAS dentro do horário comercial
# (08:00 às 19:00). Fora dessa janela, o script aguarda até as 08:00 do
# próximo dia (ou do mesmo dia, se ainda não tiver começado o expediente).
#
# Se um ciclo demorar mais do que 10 minutos, o próximo horário da grade que
# já tiver passado é pulado, e o script aguarda até o PRÓXIMO horário
# disponível -- mesma lógica do orquestrador legado.
#
# SWEEP DE ÓRFÃOS: o extrator da Bronze (comercial/bronze/extrator.py)
# aceita a flag --sweep-orfaos pra rodar a varredura de registros deletados
# fisicamente no Sapiens (ver docstring de lá pro porquê de não rodar em
# todo ciclo). Diferente do legado (que agenda isso externamente, via
# Agendador de Tarefas configurado pra 19h), aqui quem decide é o próprio
# loop: toda vez que o ciclo que está começando for o ÚLTIMO dentro do
# horário comercial do dia (ver ultimo_ciclo_do_dia()), a Bronze roda com
# --sweep-orfaos automaticamente nesse ciclo.
#
# Este orquestrador roda de forma completamente independente de qualquer
# outro orquestrador do projeto novo (ex.: o das demais áreas), com
# agendador próprio no Agendador de Tarefas do Windows.
#
# Forma de execução:
#   cd C:\Users\roqt\Desktop\dw_aquario && python -m comercial.orquestrador
#
# Agendador de Tarefas — configuração recomendada:
#   Programa  : python
#   Argumentos: C:\Users\roqt\Desktop\dw_aquario\comercial\orquestrador.py
#   Iniciar em: C:\Users\roqt\Desktop\dw_aquario
#
# ATENÇÃO: NÃO configurar repetição no Agendador de Tarefas.
#   O agendamento (grade fixa de 10 em 10 min, 08h-19h) é controlado pelo
#   próprio script. O Agendador apenas dá a largada inicial do dia.
#
# Logs:
#   Salvos em: C:\Users\roqt\Desktop\dw_aquario\logs\  (pasta exclusiva
#   deste projeto -- não é a mesma pasta de logs do legado)
#   Formato  : comercial_YYYYMMDD_HHMMSS.log
#   Retenção : últimos 10 arquivos (os mais antigos são deletados automaticamente)

# ----- IMPORTS -----

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep, time

# ----- CONFIGURAÇÃO DO PYTHONPATH -----

# Garante que a raiz do projeto esteja no sys.path ao executar diretamente
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from comercial.config.settings import PROJECT_ROOT

# ----- CONFIGURAÇÕES -----

INTERVALO_ENTRE_CICLOS = 10 * 60  # 10 minutos — grade fixa (ex.: 08:00, 08:10, 08:20...)
HORA_INICIO_COMERCIAL  = 8        # 08:00
HORA_FIM_COMERCIAL     = 19       # 19:00 (exclusivo — último ciclo permitido é < 19:00)
LOGS_DIR               = PROJECT_ROOT / "logs"
MAX_LOGS               = 10       # quantos arquivos de log manter

# ----- PASTA DOS SCRIPTS DA PRATA -----

PASTA_SCRIPTS = PROJECT_ROOT / "comercial" / "prata"

# ----- ORDEM DE EXECUÇÃO DA PRATA -----

# Mesma ordem do catálogo (comercial/prata/tabelas.py) -- das dimensões
# mais simples até os 2 fatos, do menos pro mais delicado.
SCRIPTS = [
#    "dim_condicao_pagamento",
#    "dim_produto",
#    "dim_representante",
#    "dim_regional",
#    "fat_metas",
#    "dim_cliente",
    "fat_faturamento",
]

# ----- CLASSE TEE (console + arquivo simultaneamente) -----

class Tee:
    """
    Redireciona sys.stdout para o console E para um arquivo ao mesmo tempo.
    Uso:
        with Tee(caminho_arquivo):
            print("isso vai pro console e pro arquivo")
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._console = None
        self._arquivo = None

    def __enter__(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._console     = sys.stdout
        self._console_err = sys.stderr
        self._arquivo     = open(self.filepath, "w", encoding="utf-8")
        sys.stdout        = self
        sys.stderr        = self
        return self

    def write(self, texto: str):
        self._console.write(texto)
        self._console.flush()
        self._arquivo.write(texto)
        self._arquivo.flush()

    def flush(self):
        self._console.flush()
        self._arquivo.flush()

    def __exit__(self, *args):
        sys.stdout = self._console
        sys.stderr = self._console_err
        self._arquivo.close()


# ----- GERENCIAMENTO DE LOGS -----

def limpar_logs_antigos() -> None:
    """Mantém apenas os MAX_LOGS arquivos de log do comercial mais recentes."""
    logs = sorted(LOGS_DIR.glob("comercial_*.log"), key=lambda f: f.stat().st_mtime)
    excesso = len(logs) - MAX_LOGS
    if excesso > 0:
        for log_antigo in logs[:excesso]:
            log_antigo.unlink()
            print(f"  [LOG] Removido log antigo: {log_antigo.name}")


# ----- FUNÇÕES -----

def rodar_bronze(sweep_orfaos: bool) -> dict:
    """
    Executa comercial.bronze.extrator via subprocess.

    sweep_orfaos: quando True, passa a flag --sweep-orfaos (ver
    ultimo_ciclo_do_dia() -- só acontece no último ciclo dentro do
    horário comercial do dia).
    """
    nome_exibicao = "comercial.bronze.extrator"
    sufixo = " (--sweep-orfaos)" if sweep_orfaos else ""

    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Iniciando: {nome_exibicao}{sufixo}")

    env    = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    inicio = time()

    comando = ["python", "-m", "comercial.bronze.extrator"]
    if sweep_orfaos:
        comando.append("--sweep-orfaos")

    try:
        resultado = subprocess.run(
            comando,
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        duracao = time() - inicio

        if resultado.stdout:
            print(resultado.stdout)

        if resultado.stderr:
            print("  [STDERR]:")
            print(resultado.stderr)

        if resultado.returncode == 0:
            print(f"  [OK] {nome_exibicao} finalizado em {duracao:.1f}s")
            return {"modulo": nome_exibicao, "status": "OK", "duracao_s": duracao}
        else:
            print(
                f"  [ERRO] {nome_exibicao} finalizou com erro. "
                f"Código de retorno: {resultado.returncode} | Duração: {duracao:.1f}s"
            )
            return {"modulo": nome_exibicao, "status": "ERRO", "duracao_s": duracao}

    except Exception as e:
        duracao = time() - inicio
        print(f"  [EXCEÇÃO] Erro inesperado ao executar {nome_exibicao}: {e}")
        return {"modulo": nome_exibicao, "status": "EXCEÇÃO", "duracao_s": duracao}


def rodar_script(modulo: str) -> dict:
    """
    Executa um módulo Python individualmente via subprocess.
    Cada script é rodado isolado para que erros em um não interrompam os demais.

    Args:
        modulo: nome do módulo em comercial/prata/ (sem .py)

    Returns:
        dict com chaves: modulo, status, duracao_s
    """
    caminho_script  = PASTA_SCRIPTS / f"{modulo}.py"
    nome_exibicao   = f"{modulo}.py"

    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Iniciando: {nome_exibicao}")

    if not caminho_script.exists():
        print(f"  [AVISO] Arquivo não encontrado: {caminho_script}")
        return {"modulo": modulo, "status": "AVISO", "duracao_s": 0.0}

    env    = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    inicio = time()

    try:
        resultado = subprocess.run(
            ["python", "-m", f"comercial.prata.{modulo}"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        duracao = time() - inicio

        if resultado.stdout:
            print(resultado.stdout)

        if resultado.stderr:
            print("  [STDERR]:")
            print(resultado.stderr)

        if resultado.returncode == 0:
            print(f"  [OK] {nome_exibicao} finalizado em {duracao:.1f}s")
            return {"modulo": modulo, "status": "OK", "duracao_s": duracao}
        else:
            print(
                f"  [ERRO] {nome_exibicao} finalizou com erro. "
                f"Código de retorno: {resultado.returncode} | Duração: {duracao:.1f}s"
            )
            return {"modulo": modulo, "status": "ERRO", "duracao_s": duracao}

    except Exception as e:
        duracao = time() - inicio
        print(f"  [EXCEÇÃO] Erro inesperado ao executar {nome_exibicao}: {e}")
        return {"modulo": modulo, "status": "EXCEÇÃO", "duracao_s": duracao}


def dentro_horario_comercial(momento: datetime) -> bool:
    """True se `momento` estiver dentro da janela 08:00 (inclusive) - 19:00 (exclusive)."""
    return HORA_INICIO_COMERCIAL <= momento.hour < HORA_FIM_COMERCIAL


def proximo_horario_grade(referencia: float) -> float:
    """
    Retorna o próximo timestamp múltiplo de INTERVALO_ENTRE_CICLOS,
    estritamente maior que `referencia`, e AJUSTADO para cair dentro do
    horário comercial (08:00–19:00).

    Regras:
      - Se o próximo slot da grade cair fora da janela (>= 19:00 ou < 08:00),
        o horário é empurrado para as 08:00 do dia seguinte.
      - Se `referencia` for antes das 08:00 do mesmo dia, o primeiro slot
        já é diretamente as 08:00 desse dia.
    """
    proximo_ts = ((int(referencia) // INTERVALO_ENTRE_CICLOS) + 1) * INTERVALO_ENTRE_CICLOS
    proximo_dt = datetime.fromtimestamp(proximo_ts)

    if proximo_dt.hour < HORA_INICIO_COMERCIAL:
        # ainda não começou o expediente do próprio dia -> empurra pras 08:00 de hoje
        proximo_dt = proximo_dt.replace(hour=HORA_INICIO_COMERCIAL, minute=0, second=0, microsecond=0)
    elif proximo_dt.hour >= HORA_FIM_COMERCIAL:
        # expediente do dia já encerrou -> empurra pras 08:00 do dia seguinte
        proximo_dt = (proximo_dt + timedelta(days=1)).replace(
            hour=HORA_INICIO_COMERCIAL, minute=0, second=0, microsecond=0
        )

    return proximo_dt.timestamp()


def ultimo_ciclo_do_dia(momento_ts: float) -> bool:
    """
    True se o ciclo que está começando agora (momento_ts) for o ÚLTIMO
    dentro do horário comercial de hoje -- ou seja, o próximo horário da
    grade (proximo_horario_grade) só acontece amanhã.

    Usado pra decidir se passamos --sweep-orfaos pro extrator da Bronze
    nesta execução (mesma regra do resto do projeto: a varredura de
    órfãos só roda 1x por dia, na última execução -- ver docstring de
    comercial/bronze/extrator.py).
    """
    agora_dt   = datetime.fromtimestamp(momento_ts)
    proximo_dt = datetime.fromtimestamp(proximo_horario_grade(momento_ts))
    return proximo_dt.date() != agora_dt.date()


def imprimir_resumo(resultados: list[dict], duracao_total: float, proximo_ciclo: datetime, log_path: Path) -> None:
    total_ok    = sum(1 for r in resultados if r["status"] == "OK")
    total_erro  = sum(1 for r in resultados if r["status"] in ("ERRO", "EXCEÇÃO"))
    total_aviso = sum(1 for r in resultados if r["status"] == "AVISO")

    minutos  = int(duracao_total // 60)
    segundos = duracao_total % 60

    print(f"\n{'='*60}")
    print(f"  RESUMO DO CICLO — COMERCIAL (PROJETO NOVO)")
    print(f"{'='*60}")

    for r in resultados:
        icone       = "[OK]" if r["status"] == "OK" else ("[AVISO]" if r["status"] == "AVISO" else "[ERRO]")
        duracao_fmt = f"{r['duracao_s']:.1f}s" if r["duracao_s"] > 0 else "  -  "
        print(f"  {icone} {r['modulo']:<28} -> {r['status']:<8} ({duracao_fmt})")

    print(f"{'='*60}")
    print(f"  Total: {total_ok} OK | {total_erro} ERRO | {total_aviso} AVISO")
    print(f"  Duração total do ciclo: {minutos}min {segundos:.0f}s")
    print(f"  Próximo ciclo agendado para: {proximo_ciclo:%Y-%m-%d %H:%M:%S}  (grade fixa de {INTERVALO_ENTRE_CICLOS // 60} min, horário comercial 08h-19h)")
    print(f"  Log salvo em: logs/{log_path.name}")
    print(f"{'='*60}")


def executar_ciclo(numero_ciclo: int) -> None:
    """Executa um ciclo completo: Bronze + todas as tabelas da Prata em sequência, salvando log."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path  = LOGS_DIR / f"comercial_{timestamp}.log"

    with Tee(log_path):

        inicio_ciclo = time()
        sweep_orfaos = ultimo_ciclo_do_dia(time())

        print(f"\n{'#'*60}")
        print(f"  BI AQUÁRIO — COMERCIAL (PROJETO NOVO) — CICLO #{numero_ciclo}")
        print(f"  INÍCIO: {datetime.now():%Y-%m-%d %H:%M:%S}")
        if sweep_orfaos:
            print(f"  ÚLTIMA EXECUÇÃO DO DIA -- Bronze vai rodar com --sweep-orfaos")
        print(f"  Log: logs/{log_path.name}")
        print(f"{'#'*60}")

        resultados = [rodar_bronze(sweep_orfaos)]

        for script in SCRIPTS:
            resultados.append(rodar_script(script))

        duracao_total = time() - inicio_ciclo

        print(f"\n{'#'*60}")
        print(f"  BI AQUÁRIO — COMERCIAL (PROJETO NOVO) — FIM DO CICLO #{numero_ciclo}")
        print(f"  {datetime.now():%Y-%m-%d %H:%M:%S}")
        print(f"{'#'*60}")

        proximo_ciclo_ts = proximo_horario_grade(time())
        proximo_ciclo    = datetime.fromtimestamp(proximo_ciclo_ts)
        imprimir_resumo(resultados, duracao_total, proximo_ciclo, log_path)

    # limpeza FORA do Tee — stdout já restaurado
    limpar_logs_antigos()


# ----- LOOP PRINCIPAL -----

if __name__ == "__main__":
    numero_ciclo = 0

    # Se o processo for iniciado fora do horário comercial (ex.: Agendador
    # dispara às 07:00 ou de madrugada), aguarda até as 08:00 antes do 1º ciclo.
    agora = datetime.now()
    if not dentro_horario_comercial(agora):
        primeiro_horario_ts = proximo_horario_grade(time() - INTERVALO_ENTRE_CICLOS)
        espera_inicial = max(0, primeiro_horario_ts - time())
        print(
            f"  Fora do horário comercial (08h-19h). "
            f"Aguardando até {datetime.fromtimestamp(primeiro_horario_ts):%Y-%m-%d %H:%M:%S} "
            f"para iniciar o primeiro ciclo..."
        )
        sleep(espera_inicial)

    while True:
        numero_ciclo += 1
        executar_ciclo(numero_ciclo)

        agora = time()

        # Próximo horário da grade fixa de 10 em 10 min, dentro do horário comercial
        proxima_execucao = proximo_horario_grade(agora)
        espera            = proxima_execucao - agora

        # Se o ciclo demorou mais que o intervalo, um ou mais horários da
        # grade foram pulados — deixa isso explícito no console/log.
        if espera > INTERVALO_ENTRE_CICLOS + 60:
            print(
                f"\n  [AVISO] Ciclo terminou fora da grade normal "
                f"(fim do horário comercial ou atraso): aguardando até o próximo horário disponível."
            )
        elif espera > INTERVALO_ENTRE_CICLOS - 1:
            print(
                f"\n  [AVISO] O ciclo demorou mais que {INTERVALO_ENTRE_CICLOS // 60} min: "
                f"um ou mais horários da grade foram pulados."
            )

        print(
            f"\n  Aguardando {espera:.0f} segundos "
            f"até o próximo horário da grade..."
        )
        print(
            f"  Próxima execução: "
            f"{datetime.fromtimestamp(proxima_execucao):%Y-%m-%d %H:%M:%S}"
        )
        print("  (Ctrl+C para interromper)\n")

        sleep(espera)
