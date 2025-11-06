"""
Simulador da fábrica do Papai Noel
- Esteira com variável (padrão: 10).
- Acesso à esteira:
  Grupo INSERE (A/B/C), só um por vez.
  Grupo que RETIRA (E), só um por vez.
- No máx. dois duendes produzindo bolas por vez.
- Vários D (conferência) podem operar juntos, MAS ninguém mexe no trenó enquanto um E deposita.
  => Trava de leitores/escritor no trenó: D = leitores, E = escritor.
- Funciona para qualquer número de duendes de cada tipo.
Executar:  python main.py
"""
from __future__ import annotations

import argparse
import random
import signal
import sys
import threading
import time
from collections import Counter, deque
from datetime import datetime
from typing import Deque, Dict, Optional, Tuple


# === melhorias visuais ===
class Cores:
    RESET = "\033[0m"
    DIM = "\033[2m"
    NEGRITO = "\033[1m"
    VERMELHO = "\033[31m"
    VERDE = "\033[32m"
    AMARELO = "\033[33m"
    AZUL = "\033[34m"
    MAGENTA = "\033[35m"
    CIANO = "\033[36m"


def carimbo_tempo() -> str:
    return datetime.now().strftime("%H:%M:%S")


def dorme_intervalo(a: float, b: float, velocidade: float = 1.0) -> None:
    """Dormir entre [a, b] segundos dividido pela velocidade."""
    t = random.uniform(a, b) / max(0.1, velocidade)
    time.sleep(t)


# === Estruturas de Sincronização ===
class TravaLeitoresEscritor:
    """Trava leitores-escritor simples.
    - Leitores (D) podem ler em paralelo.
    - Escritor (E) é exclusivo: bloqueia leitores e outros escritores.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._leitores = 0
        self._escritor = False

    def adquirir_leitura(self):
        with self._lock:
            while self._escritor:
                self._cond.wait()
            self._leitores += 1

    def liberar_leitura(self):
        with self._lock:
            self._leitores -= 1
            if self._leitores == 0:
                self._cond.notify_all()

    def adquirir_escrita(self):
        with self._lock:
            while self._escritor or self._leitores > 0:
                self._cond.wait()
            self._escritor = True

    def liberar_escrita(self):
        with self._lock:
            self._escritor = False
            self._cond.notify_all()


# === Modelos ===
Brinquedo = Dict[str, str]  # {"tipo": "carrinho"|"boneca"|"bola", "id": "A-1"}


class Esteira:
    """Esteira com capacidade fixa (buffer) + monitor (Condition)."""
    def __init__(self, capacidade: int):
        self.capacidade = capacidade
        self._buf: Deque[Brinquedo] = deque()
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)

    def colocar(self, item: Brinquedo, evento_parar: threading.Event) -> bool:
        with self._cond:
            ok = self._cond.wait_for(lambda: len(self._buf) < self.capacidade or evento_parar.is_set())
            if not ok or evento_parar.is_set():
                return False
            self._buf.append(item)
            self._cond.notify_all()
            return True

    def retirar(self, evento_parar: threading.Event) -> Optional[Brinquedo]:
        with self._cond:
            ok = self._cond.wait_for(lambda: len(self._buf) > 0 or evento_parar.is_set())
            if not ok or (evento_parar.is_set() and len(self._buf) == 0):
                return None
            item = self._buf.popleft()
            self._cond.notify_all()
            return item

    def instantaneo(self) -> Tuple[int, int]:
        with self._lock:
            return len(self._buf), self.capacidade

    def barra(self) -> str:
        with self._lock:
            usados = len(self._buf)
            cap = self.capacidade
        preenchido = "#" * usados
        vazio = "." * (cap - usados)
        return f"[{preenchido}{vazio}] {usados}/{cap}"


class Treno:
    """Trenó com capacidade 'infinita', com TravaLeitoresEscritor para acesso conjunto."""
    def __init__(self):
        self._itens: Deque[Brinquedo] = deque()
        self._rw = TravaLeitoresEscritor()

    # Usado pelo E (escritor)
    def depositar(self, brinquedo: Brinquedo):
        self._rw.adquirir_escrita()
        try:
            self._itens.append(brinquedo)
        finally:
            self._rw.liberar_escrita()

    # Usado pelo D (leitor)
    def ler_contagens(self) -> Counter:
        self._rw.adquirir_leitura()
        try:
            return Counter(b["tipo"] for b in self._itens)
        finally:
            self._rw.liberar_leitura()


# === Fábrica (recursos compartilhados) ===
class Fabrica:
    def __init__(self, capacidade: int, bancos_bolas: int, usar_cor: bool, velocidade: float):
        self.esteira = Esteira(capacidade)
        self.treno = Treno()
        self.parar = threading.Event()
        self.velocidade = velocidade

        # Regras: acesso exclusivo à esteira por grupo
        self.portao_inserir = threading.Semaphore(1)   # A/B/C (inseridores)
        self.portao_retirar = threading.Semaphore(1)   # E (retiradores)

        # Mesa de bolas com 2 bancos
        self.bancos_bolas = threading.Semaphore(bancos_bolas)

        # Contadores
        self._trava_id = threading.Lock()
        self._seq_brinquedo = 0
        self._trava_contagem = threading.Lock()
        self.produzidos = Counter()
        self.entregues = Counter()

        # Saída
        self.usar_cor = usar_cor

    def proximo_id(self, prefixo: str) -> str:
        with self._trava_id:
            self._seq_brinquedo += 1
            return f"{prefixo}-{self._seq_brinquedo}"

    def colorir(self, s: str, cor: str) -> str:
        if not self.usar_cor:
            return s
        return cor + s + Cores.RESET

    def log(self, msg: str):
        if self.usar_cor:
            print(f"{Cores.DIM}{carimbo_tempo()}{Cores.RESET} {msg}")
        else:
            print(f"{carimbo_tempo()} {msg}")

    def logar_estado(self):
        self.log(f"Esteira {self.esteira.barra()}  |  Trenó: {sum(self.entregues.values())} itens")

    def inc_produzido(self, tipo: str):
        with self._trava_contagem:
            self.produzidos[tipo] += 1

    def inc_entregue(self, tipo: str):
        with self._trava_contagem:
            self.entregues[tipo] += 1


# === Threads de Duendes ===
class DuendeBase(threading.Thread):
    def __init__(self, nome: str, fabrica: Fabrica):
        super().__init__(daemon=True)
        self.nome = nome
        self.f = fabrica

    def executando(self) -> bool:
        return not self.f.parar.is_set()


class DuendeA(DuendeBase):
    """Produz carrinhos e coloca na esteira (produtor)."""
    def run(self):
        while self.executando():
            # Produção (não precisa de banco de bolas)
            dorme_intervalo(0.25, 0.6, self.f.velocidade)
            brinquedo = {"tipo": "carrinho", "id": self.f.proximo_id("A")}

            # Inserir na esteira (grupo de inseridores = exclusivo)
            adquirido = self.f.portao_inserir.acquire(timeout=0.5)
            if not adquirido:
                continue
            try:
                ok = self.f.esteira.colocar(brinquedo, self.f.parar)
                if not ok:
                    break
                self.f.inc_produzido(brinquedo["tipo"])
                self.f.log(self.f.colorir(f"A {self.nome} colocou {emoji_do(brinquedo['tipo'])} {brinquedo['id']} na esteira.", Cores.VERDE))
                self.f.logar_estado()
            finally:
                self.f.portao_inserir.release()


class DuendeB(DuendeBase):
    """Produz boneca/bola alternadamente e coloca na esteira."""
    def __init__(self, nome: str, fabrica: Fabrica):
        super().__init__(nome, fabrica)
        self._proxima_bola = False  # começa com boneca

    def run(self):
        while self.executando():
            if self._proxima_bola:
                # Precisa banco de bolas
                ok_banco = self.f.bancos_bolas.acquire(timeout=0.5)
                if not ok_banco:
                    continue
                try:
                    dorme_intervalo(0.25, 0.6, self.f.velocidade)
                    brinquedo = {"tipo": "bola", "id": self.f.proximo_id("B")}
                finally:
                    self.f.bancos_bolas.release()
            else:
                dorme_intervalo(0.25, 0.6, self.f.velocidade)
                brinquedo = {"tipo": "boneca", "id": self.f.proximo_id("B")}

            self._proxima_bola = not self._proxima_bola

            adquirido = self.f.portao_inserir.acquire(timeout=0.5)
            if not adquirido:
                continue
            try:
                ok = self.f.esteira.colocar(brinquedo, self.f.parar)
                if not ok:
                    break
                self.f.inc_produzido(brinquedo["tipo"])
                self.f.log(self.f.colorir(f"B {self.nome} colocou {emoji_do(brinquedo['tipo'])} {brinquedo['id']} na esteira.", Cores.VERDE))
                self.f.logar_estado()
            finally:
                self.f.portao_inserir.release()


class DuendeC(DuendeBase):
    """Produz bolas e coloca na esteira."""
    def run(self):
        while self.executando():
            ok_banco = self.f.bancos_bolas.acquire(timeout=0.5)
            if not ok_banco:
                continue
            try:
                dorme_intervalo(0.25, 0.6, self.f.velocidade)
                brinquedo = {"tipo": "bola", "id": self.f.proximo_id("C")}
            finally:
                self.f.bancos_bolas.release()

            adquirido = self.f.portao_inserir.acquire(timeout=0.5)
            if not adquirido:
                continue
            try:
                ok = self.f.esteira.colocar(brinquedo, self.f.parar)
                if not ok:
                    break
                self.f.inc_produzido(brinquedo["tipo"])
                self.f.log(self.f.colorir(f"C {self.nome} colocou {emoji_do(brinquedo['tipo'])} {brinquedo['id']} na esteira.", Cores.VERDE))
                self.f.logar_estado()
            finally:
                self.f.portao_inserir.release()


class DuendeE(DuendeBase):
    """Retira brinquedos da esteira e deposita no trenó (consumidor / escritor)."""
    def run(self):
        while self.executando():
            # Acesso exclusivo do grupo E à esteira
            adquirido = self.f.portao_retirar.acquire(timeout=0.5)
            if not adquirido:
                continue
            try:
                brinquedo = self.f.esteira.retirar(self.f.parar)
                if brinquedo is None:
                    break
                self.f.log(self.f.colorir(f"E {self.nome} retirou {emoji_do(brinquedo['tipo'])} {brinquedo['id']} da esteira.", Cores.AMARELO))
            finally:
                self.f.portao_retirar.release()

            # Depositar no trenó – escritor exclusivo (bloqueia Ds e outros Es)
            self.f.treno.depositar(brinquedo)
            self.f.inc_entregue(brinquedo["tipo"])
            self.f.log(self.f.colorir(f"E {self.nome} depositou {emoji_do(brinquedo['tipo'])} {brinquedo['id']} no trenó.", Cores.AMARELO))
            self.f.logar_estado()
            dorme_intervalo(0.05, 0.2, self.f.velocidade)


class DuendeD(DuendeBase):
    """Conferência dos brinquedos no trenó (leitor concorrente)."""
    def run(self):
        while self.executando():
            contagens = self.f.treno.ler_contagens()
            total = sum(contagens.values())
            nice = ", ".join(f"{k}:{v}" for k, v in sorted(contagens.items()))
            self.f.log(self.f.colorir(f"D {self.nome} conferiu trenó: total={total} ({nice})", Cores.CIANO))
            dorme_intervalo(0.3, 0.8, self.f.velocidade)


# === Emoji/helper ===
def emoji_do(tipo: str) -> str:
    return {"carrinho": "🚗", "boneca": "🪆", "bola": "⚽"}.get(tipo, "🎁")


# === Execução ===
def argumentos(argv=None):
    p = argparse.ArgumentParser(description="Simulador dos duendes (threads)")
    p.add_argument("--A", type=int, default=2, help="Quantidade de duendes A (carrinhos)")
    p.add_argument("--B", type=int, default=1, help="Quantidade de duendes B (boneca/bola alternado)")
    p.add_argument("--C", type=int, default=2, help="Quantidade de duendes C (bolas)")
    p.add_argument("--D", type=int, default=3, help="Quantidade de duendes D (conferência)")
    p.add_argument("--E", type=int, default=2, help="Quantidade de duendes E (retira/deposita)")
    p.add_argument("--capacidade", type=int, default=10, help="Capacidade da esteira (padrão=10)")
    p.add_argument("--tempo", type=int, default=20, help="Duração da simulação em segundos (padrão=20)")
    p.add_argument("--semcor", action="store_true", help="Desativa cores ANSI no terminal")
    p.add_argument("--vel", type=float, default=1.25, help="Velocidade (>1.0 acelera a simulação; padrão=1.25)")
    p.add_argument("--seed", type=int, default=None, help="Semente do gerador aleatório (reprodutibilidade)")
    return p.parse_args(argv)


def principal(argv=None):
    args = argumentos(argv)
    if args.seed is not None:
        random.seed(args.seed)

    fabrica = Fabrica(
        capacidade=args.capacidade,
        bancos_bolas=2,
        usar_cor=not args.semcor,
        velocidade=args.vel
    )

    # Instanciar threads
    threads = []
    for i in range(args.A):
        threads.append(DuendeA(nome=f"A{i+1}", fabrica=fabrica))
    for i in range(args.B):
        threads.append(DuendeB(nome=f"B{i+1}", fabrica=fabrica))
    for i in range(args.C):
        threads.append(DuendeC(nome=f"C{i+1}", fabrica=fabrica))
    for i in range(args.E):
        threads.append(DuendeE(nome=f"E{i+1}", fabrica=fabrica))
    for i in range(args.D):
        threads.append(DuendeD(nome=f"D{i+1}", fabrica=fabrica))

    # Boas-vindas
    print(Cores.NEGRITO + "=== Fábrica do Papai Noel: Simulação de Concorrência ===" + Cores.RESET)
    print(f"Configuração: A={args.A}, B={args.B}, C={args.C}, D={args.D}, E={args.E}, "
          f"esteira={args.capacidade}, bancos_bola=2, tempo={args.tempo}s, vel={args.vel}")
    print("")

    # Tratador de CTRL+C para encerrar bem
    def tratar_sigint(sig, frame):
        print("\nEncerrando...")
        fabrica.parar.set()
        # Acorda quem estiver esperando na esteira
        with fabrica.esteira._cond:
            fabrica.esteira._cond.notify_all()

    signal.signal(signal.SIGINT, tratar_sigint)

    # Início
    for t in threads:
        t.start()

    # Roda por tempo definido
    t_fim = time.time() + max(1, args.tempo)
    while time.time() < t_fim:
        time.sleep(0.2)

    # Parar
    fabrica.parar.set()
    with fabrica.esteira._cond:
        fabrica.esteira._cond.notify_all()

    for t in threads:
        t.join(timeout=2.0)

    # Resumo final
    print("\n" + Cores.NEGRITO + "=== Resumo ===" + Cores.RESET)
    print("Produzidos:", dict(fabrica.produzidos))
    print("Entregues no trenó:", dict(fabrica.entregues))
    print("FIM! 🎄")


if __name__ == "__main__":
    principal()
