"""
Processa os eventos do drop em tempo real, à medida que chegam do Redpanda.

O que ele faz com cada evento:
    - descarta DUPLICADOS (o mesmo id_evento chegando duas vezes);
    - percebe eventos ATRASADOS (que chegam depois de eventos mais novos);
    - mantém, para cada peça, visualizações, curtidas, carrinhos e se já foi vendida;
    - detecta BOTS: clientes com muitos "adicionou_ao_carrinho" em 10 segundos;
    - ENRIQUECE os eventos com o nome e a marca da peça, buscando no banco
      (os eventos só trazem o código da peça, para serem leves).

A cada 2 segundos, ele grava o resultado no Postgres e mostra um painel no terminal:
    raw.drop_eventos          todos os eventos recebidos, sem duplicados
    streaming.drop_pecas      a situação de cada peça, atualizada ao vivo
    streaming.drop_alertas    as clientes suspeitas de serem bots

Uso (com o Redpanda ligado):
    python scripts/streaming/processar_drop.py

Deixe rodando e, em OUTRO terminal, dispare o drop com o simular_drop.py.
Ele para sozinho depois de 30 segundos sem receber eventos (ou com Ctrl+C).
"""
import argparse
import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

TOPICO = "drop_eventos"
JANELA_BOT_SEGUNDOS = 10
LIMITE_BOT = 10            # mais que isso de carrinhos em 10s = suspeita de bot
TOLERANCIA_ATRASO = 1.0    # segundos


# ---------------------------------------------------------------------------
# estado do drop (lógica pura, sem Redpanda nem banco: fácil de testar)
# ---------------------------------------------------------------------------
class PainelDrop:
    def __init__(self, id_drop: str):
        self.id_drop = id_drop
        self.ids_vistos: set[str] = set()
        self.novos_eventos: list[dict] = []
        self.pecas = defaultdict(lambda: {"visualizacoes": 0, "curtidas": 0, "carrinhos": 0,
                                          "vendida_para": None, "momento_venda": None, "recusadas": 0})
        self.carrinhos_recentes = defaultdict(deque)
        self.alertas: dict[str, dict] = {}
        self.inicio: datetime | None = None
        self.ultimo_momento: datetime | None = None
        self.recebidos = self.duplicados = self.atrasados = 0
        self.soma_latencia = 0.0

    def processar(self, ev: dict, recebido_em: datetime) -> None:
        self.recebidos += 1
        if ev["id_evento"] in self.ids_vistos:
            self.duplicados += 1
            return
        self.ids_vistos.add(ev["id_evento"])

        momento = datetime.fromisoformat(ev["momento_evento"])
        self.inicio = momento if self.inicio is None else min(self.inicio, momento)
        if self.ultimo_momento and (self.ultimo_momento - momento).total_seconds() > TOLERANCIA_ATRASO:
            self.atrasados += 1
        self.ultimo_momento = momento if self.ultimo_momento is None else max(self.ultimo_momento, momento)
        self.soma_latencia += (recebido_em - momento).total_seconds()

        ev = {**ev, "recebido_em": recebido_em.isoformat()}
        self.novos_eventos.append(ev)
        peca = self.pecas[ev["id_peca"]]
        tipo = ev["tipo"]

        if tipo == "visualizou_peca":
            peca["visualizacoes"] += 1
        elif tipo == "curtiu":
            peca["curtidas"] += 1
        elif tipo == "adicionou_ao_carrinho":
            peca["carrinhos"] += 1
            self._verificar_bot(ev["id_cliente"], momento)
        elif tipo == "comprou":
            peca["vendida_para"] = ev["id_cliente"]
            peca["momento_venda"] = momento
        elif tipo == "compra_recusada":
            peca["recusadas"] += 1

    def _verificar_bot(self, cliente: str, momento: datetime) -> None:
        janela = self.carrinhos_recentes[cliente]
        janela.append(momento)
        while janela and (momento - janela[0]).total_seconds() > JANELA_BOT_SEGUNDOS:
            janela.popleft()
        if len(janela) > LIMITE_BOT and cliente not in self.alertas:
            self.alertas[cliente] = {"momento": momento, "carrinhos": len(janela)}

    def segundos_ate_vender(self, id_peca: str) -> float | None:
        venda = self.pecas[id_peca]["momento_venda"]
        return round((venda - self.inicio).total_seconds(), 1) if venda else None

    def latencia_media(self) -> float:
        validos = self.recebidos - self.duplicados
        return self.soma_latencia / validos if validos else 0.0


# ---------------------------------------------------------------------------
# banco de dados
# ---------------------------------------------------------------------------
def conectar():
    load_dotenv()
    url = (
        f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("create schema if not exists raw"))
        conn.execute(text("create schema if not exists streaming"))
        conn.execute(text("""
            create table if not exists raw.drop_eventos (
                id_evento text primary key,
                id_drop text not null,
                tipo text not null,
                id_cliente text not null,
                id_peca text not null,
                momento_evento timestamptz not null,
                recebido_em timestamptz not null,
                evento jsonb not null
            )"""))
        conn.execute(text("""
            create table if not exists streaming.drop_pecas (
                id_drop text, id_peca text, nome text, marca text,
                visualizacoes int, curtidas int, carrinhos int,
                vendida boolean, vendida_para text, segundos_ate_vender numeric,
                compras_recusadas int, atualizado_em timestamptz,
                primary key (id_drop, id_peca)
            )"""))
        conn.execute(text("""
            create table if not exists streaming.drop_alertas (
                id_drop text, id_cliente text, momento_alerta timestamptz,
                carrinhos_em_10s int, motivo text,
                primary key (id_drop, id_cliente)
            )"""))
    return engine


class Enriquecedor:
    """Busca nome e marca das peças no banco, guardando em memória o que já buscou."""

    def __init__(self, engine):
        self.engine, self.cache = engine, {}

    def dados(self, ids: list[str]) -> dict[str, tuple]:
        faltando = [i for i in ids if i not in self.cache]
        if faltando:
            with self.engine.connect() as conn:
                linhas = conn.execute(text(
                    "select id_anuncio, nome_da_peca, marca from raw.anuncios where id_anuncio = any(:ids)"
                ), {"ids": faltando}).all()
            for id_anuncio, nome, marca in linhas:
                self.cache[id_anuncio] = (nome, marca)
            for i in faltando:
                self.cache.setdefault(i, (None, None))
        return {i: self.cache[i] for i in ids}


def gravar(engine, painel: PainelDrop, enriquecedor: Enriquecedor) -> None:
    agora = datetime.now(timezone.utc)
    nomes = enriquecedor.dados(list(painel.pecas))
    with engine.begin() as conn:
        if painel.novos_eventos:
            # "on conflict do nothing": se o evento já foi gravado, é ignorado (idempotente)
            conn.execute(text("""
                insert into raw.drop_eventos
                    (id_evento, id_drop, tipo, id_cliente, id_peca, momento_evento, recebido_em, evento)
                values (:id_evento, :id_drop, :tipo, :id_cliente, :id_peca, :momento_evento, :recebido_em, cast(:evento as jsonb))
                on conflict (id_evento) do nothing
            """), [{**{k: e[k] for k in ("id_evento", "id_drop", "tipo", "id_cliente", "id_peca",
                                          "momento_evento", "recebido_em")},
                    "evento": json.dumps(e, ensure_ascii=False)} for e in painel.novos_eventos])
            painel.novos_eventos.clear()

        conn.execute(text("""
            insert into streaming.drop_pecas values
                (:id_drop, :id_peca, :nome, :marca, :visualizacoes, :curtidas, :carrinhos,
                 :vendida, :vendida_para, :segundos, :recusadas, :agora)
            on conflict (id_drop, id_peca) do update set
                visualizacoes = excluded.visualizacoes, curtidas = excluded.curtidas,
                carrinhos = excluded.carrinhos, vendida = excluded.vendida,
                vendida_para = excluded.vendida_para, segundos_ate_vender = excluded.segundos_ate_vender,
                compras_recusadas = excluded.compras_recusadas, atualizado_em = excluded.atualizado_em
        """), [{"id_drop": painel.id_drop, "id_peca": i, "nome": nomes[i][0], "marca": nomes[i][1],
                "visualizacoes": p["visualizacoes"], "curtidas": p["curtidas"], "carrinhos": p["carrinhos"],
                "vendida": p["vendida_para"] is not None, "vendida_para": p["vendida_para"],
                "segundos": painel.segundos_ate_vender(i), "recusadas": p["recusadas"], "agora": agora}
               for i, p in painel.pecas.items()])

        if painel.alertas:
            conn.execute(text("""
                insert into streaming.drop_alertas values (:id_drop, :cliente, :momento, :carrinhos, :motivo)
                on conflict (id_drop, id_cliente) do nothing
            """), [{"id_drop": painel.id_drop, "cliente": c, "momento": a["momento"], "carrinhos": a["carrinhos"],
                    "motivo": f"mais de {LIMITE_BOT} carrinhos em {JANELA_BOT_SEGUNDOS}s"}
                   for c, a in painel.alertas.items()])


# ---------------------------------------------------------------------------
# painel no terminal
# ---------------------------------------------------------------------------
def mostrar(painel: PainelDrop, enriquecedor: Enriquecedor) -> None:
    vendidas = sum(1 for p in painel.pecas.values() if p["vendida_para"])
    recusadas = sum(p["recusadas"] for p in painel.pecas.values())
    mais_vistas = sorted(painel.pecas.items(), key=lambda kv: kv[1]["visualizacoes"], reverse=True)[:5]
    nomes = enriquecedor.dados([i for i, _ in mais_vistas])

    print("\n" + "=" * 70)
    print(f" {painel.id_drop}   |   {datetime.now():%H:%M:%S}")
    print(f" Eventos: {painel.recebidos}  (duplicados descartados: {painel.duplicados}, "
          f"atrasados: {painel.atrasados})   latência média: {painel.latencia_media():.2f}s")
    print(f" Peças vendidas: {vendidas} de {len(painel.pecas)}   |   compras recusadas (disputa): {recusadas}"
          f"   |   alertas de bot: {len(painel.alertas)}")
    print(" Mais vistas:")
    for id_peca, p in mais_vistas:
        nome = (nomes[id_peca][0] or id_peca[:8])[:38]
        situacao = f"VENDIDA em {painel.segundos_ate_vender(id_peca)}s" if p["vendida_para"] else "disponível"
        print(f"   {p['visualizacoes']:>4} views  {p['carrinhos']:>3} carrinhos   {nome:<38} {situacao}")


# ---------------------------------------------------------------------------
# laço principal: ler do Redpanda, processar, gravar
# ---------------------------------------------------------------------------
def main() -> None:
    from confluent_kafka import Consumer, KafkaException

    parser = argparse.ArgumentParser(description="Processa os eventos do drop em tempo real.")
    parser.add_argument("--parar-apos", type=int, default=30, help="segundos sem eventos até parar")
    args = parser.parse_args()

    engine = conectar()
    enriquecedor = Enriquecedor(engine)
    consumidor = Consumer({
        "bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092"),
        "group.id": "painel_drop",
        "auto.offset.reset": "earliest",
    })
    consumidor.subscribe([TOPICO])
    print(f"Aguardando eventos do tópico {TOPICO}... (Ctrl+C para parar)")

    paineis: dict[str, PainelDrop] = {}
    ultimo_evento = time.monotonic()
    ultima_gravacao = time.monotonic()
    try:
        while time.monotonic() - ultimo_evento < args.parar_apos:
            mensagem = consumidor.poll(0.5)
            if mensagem is not None and not mensagem.error():
                ev = json.loads(mensagem.value())
                painel = paineis.setdefault(ev["id_drop"], PainelDrop(ev["id_drop"]))
                painel.processar(ev, datetime.now(timezone.utc))
                ultimo_evento = time.monotonic()
            elif mensagem is not None and mensagem.error().fatal():
                raise KafkaException(mensagem.error())

            if time.monotonic() - ultima_gravacao >= 2 and paineis:
                for painel in paineis.values():
                    gravar(engine, painel, enriquecedor)
                mostrar(max(paineis.values(), key=lambda p: p.ultimo_momento or datetime.min.replace(tzinfo=timezone.utc)),
                        enriquecedor)
                ultima_gravacao = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        for painel in paineis.values():
            gravar(engine, painel, enriquecedor)
        consumidor.close()
        print("\nConsumidor encerrado. Resultados em streaming.drop_pecas e streaming.drop_alertas.")


if __name__ == "__main__":
    main()
