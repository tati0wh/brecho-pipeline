"""
Simula um drop completo SEM o Redpanda, para o CI.

Usa as mesmas funções do drop de verdade:
    simular_drop.gerar_eventos   ->  gera os eventos (com duplicados, atrasos e bots)
    processar_drop.PainelDrop    ->  processa cada evento, como o consumidor faria
    processar_drop.gravar        ->  grava em raw.drop_eventos e nas tabelas do painel

Só a parte de transporte (enviar e receber pelo Redpanda) fica de fora.
Isso é possível porque a lógica foi escrita separada da comunicação.

Uso:
    python ci/simular_drop_sem_kafka.py
"""
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "streaming"))

import processar_drop  # noqa: E402
import simular_drop  # noqa: E402


def main() -> None:
    random.seed(7)
    pecas = simular_drop.carregar_pecas(20)
    inicio = datetime.now(timezone.utc)
    eventos = simular_drop.gerar_eventos(pecas, clientes=150, duracao=30, inicio=inicio)

    painel = processar_drop.PainelDrop(eventos[0][1]["id_drop"])
    for segundo, evento in eventos:
        painel.processar(evento, recebido_em=inicio + timedelta(seconds=segundo + 0.05))

    engine = processar_drop.conectar()
    processar_drop.gravar(engine, painel, processar_drop.Enriquecedor(engine))
    print(f"OK: drop simulado com {len(eventos)} eventos "
          f"({painel.duplicados} duplicados descartados, {len(painel.alertas)} alertas de bot).")


if __name__ == "__main__":
    main()
