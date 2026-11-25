"""
Simula um "drop" do marketplace: o brechó solta várias peças únicas num horário
marcado e centenas de clientes correm para ver, curtir e comprar.

Cada clique vira um EVENTO, enviado na hora para o Redpanda (compatível com Kafka),
no tópico "drop_eventos". O consumidor (processar_drop.py) lê esses eventos em
tempo real.

Tipos de evento:
    visualizou_peca, curtiu, adicionou_ao_carrinho, removeu_do_carrinho,
    comprou, compra_recusada (alguém tentou comprar uma peça que já foi vendida)

Para parecer real, o simulador também produz os problemas típicos de streaming:
    - pico de acessos no início do drop, que depois vai caindo;
    - eventos duplicados (o celular reenvia quando a rede oscila);
    - eventos atrasados, que chegam fora de ordem;
    - disputa pela mesma peça (duas clientes tentando comprar quase juntas);
    - bots: contas que adicionam dezenas de peças ao carrinho em poucos segundos.

As peças do drop são sorteadas entre os anúncios mais recentes do próprio site
(data/landing), então rode antes o gerar_anuncios.py pelo menos uma vez.

Uso (com o Redpanda ligado e o processar_drop.py rodando em outro terminal):
    python scripts/streaming/simular_drop.py
    python scripts/streaming/simular_drop.py --pecas 30 --clientes 400 --duracao 90
"""
import argparse
import json
import math
import os
import random
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOPICO = "drop_eventos"
PASTA_ANUNCIOS = Path("data/landing/anuncios")


# ---------------------------------------------------------------------------
# as peças do drop
# ---------------------------------------------------------------------------
def preco_para_numero(texto: str) -> float:
    return float(re.sub(r",(?=.*,)", "", texto).replace(",", ".")) if texto else 0.0


def carregar_pecas(quantidade: int) -> list[dict]:
    arquivos = sorted(PASTA_ANUNCIOS.glob("data=*/anuncios.jsonl"))
    if not arquivos:
        raise SystemExit("Nenhum anúncio encontrado. Rode antes: python scripts/simulador/gerar_anuncios.py")
    anuncios = [json.loads(linha) for linha in arquivos[-1].read_text(encoding="utf-8").splitlines()]
    escolhidos = random.sample(anuncios, min(quantidade, len(anuncios)))
    return [
        {
            "id_peca": a["id_anuncio"],
            "nome": a["nome_da_peca"],
            "marca": a["marca"],
            "preco": preco_para_numero(a["preco_com_desconto"]),
        }
        for a in escolhidos
    ]


# ---------------------------------------------------------------------------
# geração dos eventos (lógica pura, sem Redpanda: fácil de testar)
# ---------------------------------------------------------------------------
def gerar_eventos(pecas: list[dict], clientes: int, duracao: int, inicio: datetime) -> list[tuple[float, dict]]:
    """Devolve a lista de (segundo_de_envio, evento), já com duplicados e atrasos."""
    id_drop = f"drop-{inicio:%Y%m%d-%H%M}"
    ids_clientes = [f"c-{uuid.uuid4().hex[:6]}" for _ in range(clientes)]
    bots = random.sample(ids_clientes, 2)

    # algumas peças são muito mais desejadas que outras
    popularidade = [1 / (i + 1) ** 0.8 for i in range(len(pecas))]
    random.shuffle(popularidade)

    vendida_para: dict[str, str] = {}
    carrinhos: dict[str, set] = {c: set() for c in ids_clientes}
    vistas: dict[str, set] = {c: set() for c in ids_clientes}
    eventos: list[tuple[float, dict]] = []

    def evento(segundo: float, tipo: str, cliente: str, peca: dict, **extra) -> None:
        momento = inicio + timedelta(seconds=segundo)
        eventos.append((segundo, {
            "id_evento": str(uuid.uuid4()),
            "id_drop": id_drop,
            "tipo": tipo,
            "id_cliente": cliente,
            "id_peca": peca["id_peca"],
            "momento_evento": momento.isoformat(timespec="milliseconds"),
            "dispositivo": random.choice(["mobile", "mobile", "mobile", "desktop"]),
            **extra,
        }))

    # ritmo de acessos: pico no início, caindo exponencialmente
    passo = 0.1
    segundo = 0.0
    while segundo < duracao:
        taxa = 60 * math.exp(-segundo / (duracao / 4)) + 2      # ações por segundo
        for _ in range(_poisson(taxa * passo)):
            cliente = random.choice(ids_clientes)
            # quem já tem peças no carrinho ou já viu alguma tende a voltar nelas
            if carrinhos[cliente] and random.random() < 0.5:
                id_escolhida = random.choice(sorted(carrinhos[cliente]))
                peca = next(p for p in pecas if p["id_peca"] == id_escolhida)
            elif vistas[cliente] and random.random() < 0.4:
                id_escolhida = random.choice(sorted(vistas[cliente]))
                peca = next(p for p in pecas if p["id_peca"] == id_escolhida)
            else:
                peca = random.choices(pecas, weights=popularidade)[0]
            id_peca = peca["id_peca"]
            momento = segundo + random.uniform(0, passo)

            if id_peca not in vistas[cliente]:
                vistas[cliente].add(id_peca)
                evento(momento, "visualizou_peca", cliente, peca)
            elif id_peca in carrinhos[cliente] and random.random() < 0.6:
                # tentativa de compra: só a primeira leva a peça
                if id_peca in vendida_para:
                    evento(momento, "compra_recusada", cliente, peca, motivo="peca_ja_vendida")
                else:
                    vendida_para[id_peca] = cliente
                    evento(momento, "comprou", cliente, peca, preco=peca["preco"])
                carrinhos[cliente].discard(id_peca)
            elif id_peca in carrinhos[cliente]:
                carrinhos[cliente].discard(id_peca)
                evento(momento, "removeu_do_carrinho", cliente, peca)
            elif random.random() < 0.25:
                evento(momento, "curtiu", cliente, peca)
            elif id_peca not in vendida_para:
                carrinhos[cliente].add(id_peca)
                evento(momento, "adicionou_ao_carrinho", cliente, peca)
            else:
                evento(momento, "visualizou_peca", cliente, peca)
        segundo += passo

    # bots: dezenas de peças no carrinho em poucos segundos, logo no início
    for bot in bots:
        comeco = random.uniform(1, 5)
        for i, peca in enumerate(random.sample(pecas, min(25, len(pecas)))):
            evento(comeco + i * 0.08, "adicionou_ao_carrinho", bot, peca)

    # problemas de rede: duplicados e atrasados (o momento_evento não muda)
    enviados = []
    for segundo_envio, ev in eventos:
        if random.random() < 0.03:
            segundo_envio += random.uniform(2, 6)          # chega atrasado
        enviados.append((segundo_envio, ev))
        if random.random() < 0.02:
            enviados.append((segundo_envio + random.uniform(0.1, 3), dict(ev)))  # duplicado
    enviados.sort(key=lambda par: par[0])
    return enviados


def _poisson(media: float) -> int:
    limite, k, p = math.exp(-media), 0, 1.0
    while True:
        p *= random.random()
        if p <= limite:
            return k
        k += 1


# ---------------------------------------------------------------------------
# envio para o Redpanda
# ---------------------------------------------------------------------------
def enviar(eventos: list[tuple[float, dict]], velocidade: float) -> None:
    from confluent_kafka import Producer
    from confluent_kafka.admin import AdminClient, NewTopic

    servidor = os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092")

    # 3 partições: eventos com a mesma chave (a peça) caem sempre na mesma
    # partição, então os eventos de uma peça ficam em ordem entre si
    admin = AdminClient({"bootstrap.servers": servidor})
    if TOPICO not in admin.list_topics(timeout=10).topics:
        admin.create_topics([NewTopic(TOPICO, num_partitions=3, replication_factor=1)])[TOPICO].result()
        print(f"Tópico {TOPICO} criado.")

    produtor = Producer({"bootstrap.servers": servidor})
    comeco = time.monotonic()
    for i, (segundo, ev) in enumerate(eventos, start=1):
        espera = segundo / velocidade - (time.monotonic() - comeco)
        if espera > 0:
            time.sleep(espera)
        produtor.produce(TOPICO, key=ev["id_peca"], value=json.dumps(ev, ensure_ascii=False))
        produtor.poll(0)
        if i % 200 == 0:
            print(f"  {i} eventos enviados ({segundo:.0f}s de drop)")
    produtor.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simula um drop de peças, enviando eventos ao Redpanda.")
    parser.add_argument("--pecas", type=int, default=30, help="quantas peças entram no drop")
    parser.add_argument("--clientes", type=int, default=300, help="quantas clientes participam")
    parser.add_argument("--duracao", type=int, default=60, help="duração do drop, em segundos")
    parser.add_argument("--velocidade", type=float, default=1.0, help="2 = o drop passa duas vezes mais rápido")
    args = parser.parse_args()

    pecas = carregar_pecas(args.pecas)
    eventos = gerar_eventos(pecas, args.clientes, args.duracao, datetime.now(timezone.utc))
    print(f"Drop com {len(pecas)} peças e {args.clientes} clientes: {len(eventos)} eventos em {args.duracao}s.")
    enviar(eventos, args.velocidade)
    print("Drop encerrado.")


if __name__ == "__main__":
    main()
