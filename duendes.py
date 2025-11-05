import threading
import time
import random
from collections import deque

# --- Variáveis Globais e Semáforos/Locks ---

# Esteira Central: Capacidade de 10
TAMANHO_ESTEIRA = 10
esteira_central = deque(maxlen=TAMANHO_ESTEIRA) # Usamos deque para o buffer

# Semáforos para Produtor-Consumidor (Esteira Central)
# 'vazio' controla quantos espaços vazios há na esteira (máx. 10)
vazio = threading.Semaphore(TAMANHO_ESTEIRA)
# 'cheio' controla quantos itens cheios há na esteira (máx. 10)
cheio = threading.Semaphore(0)

# Lock para exclusão mútua no acesso à Esteira (apenas um duende insere por vez,
# e apenas um duende retira por vez, mas a regra é "acesso restritivo entre os
# elementos de um mesmo grupo", o que pode ser interpretado como:
# um Lock para Inserção e um Lock para Retirada)
lock_insercao_esteira = threading.Lock() # Controla acesso dos Produtores (A, B, C)
lock_remocao_esteira = threading.Lock()  # Controla acesso do Consumidor (E)

# Mesa de Produção de Bolas: Capacidade de 2 bancos
capacidade_mesa_bolas = threading.Semaphore(2) # Controla o número de duendes (B ou C) que podem produzir bolas simultaneamente

# Trenó: Lock para exclusão mútua (Duendes E e D)
lock_treno = threading.Lock()
treno = [] # Representa o trenó

# --- Classes de Duendes (Threads) ---

class Duende(threading.Thread):
    def __init__(self, nome, tipo):
        super().__init__()
        self.nome = nome
        self.tipo = tipo

    def log(self, mensagem):
        print(f"[{self.nome} ({self.tipo})] {mensagem}")

class DuendeA(Duende):
    # Produz Carrinhos
    def __init__(self, id_duende):
        super().__init__(f"DuendeA-{id_duende}", "A")

    def run(self):
        while True:
            # 1. Produz Carrinho
            brinquedo = "Carrinho"
            self.log(f"Produzindo {brinquedo}...")
            time.sleep(random.uniform(0.5, 1.5))

            # 2. Insere na Esteira (Produtor)
            vazio.acquire() # Espera por espaço vazio na esteira

            with lock_insercao_esteira: # Exclusão mútua entre Produtores (A, B, C)
                esteira_central.append(brinquedo)
                self.log(f"Inseriu **{brinquedo}** na Esteira. Tamanho atual: {len(esteira_central)}")

            cheio.release() # Sinaliza que há um item a mais na esteira

class DuendeB(Duende):
    # Produz Bonecas e Bolas (Alternadamente)
    def __init__(self, id_duende):
        super().__init__(f"DuendeB-{id_duende}", "B")
        self.produzindo_bola = False # Começa produzindo boneca

    def run(self):
        while True:
            if not self.produzindo_bola:
                # 1. Produz Boneca (Mesa de Bonecas não tem restrição de capacidade)
                brinquedo = "Boneca"
                self.log(f"Produzindo {brinquedo}...")
                time.sleep(random.uniform(0.5, 1.5))
                self.produzindo_bola = True # Próxima será Bola
            else:
                # 1. Produz Bola (Mesa de Bolas tem 2 bancos)
                brinquedo = "Bola"
                self.log(f"Aguardando banco na Mesa de Bolas...")
                capacidade_mesa_bolas.acquire() # Ocupa um banco na Mesa de Bolas
                try:
                    self.log(f"Produzindo {brinquedo} na Mesa de Bolas...")
                    time.sleep(random.uniform(0.8, 2.0))
                finally:
                    capacidade_mesa_bolas.release() # Libera o banco
                self.produzindo_bola = False # Próxima será Boneca

            # 2. Insere na Esteira (Produtor)
            vazio.acquire() # Espera por espaço vazio na esteira

            with lock_insercao_esteira: # Exclusão mútua entre Produtores (A, B, C)
                esteira_central.append(brinquedo)
                self.log(f"Inseriu **{brinquedo}** na Esteira. Tamanho atual: {len(esteira_central)}")

            cheio.release() # Sinaliza que há um item a mais na esteira

class DuendeC(Duende):
    # Produz Bolas
    def __init__(self, id_duende):
        super().__init__(f"DuendeC-{id_duende}", "C")

    def run(self):
        while True:
            # 1. Produz Bola (Mesa de Bolas tem 2 bancos)
            brinquedo = "Bola"
            self.log(f"Aguardando banco na Mesa de Bolas...")
            capacidade_mesa_bolas.acquire() # Ocupa um banco na Mesa de Bolas
            try:
                self.log(f"Produzindo {brinquedo} na Mesa de Bolas...")
                time.sleep(random.uniform(0.8, 2.0))
            finally:
                capacidade_mesa_bolas.release() # Libera o banco

            # 2. Insere na Esteira (Produtor)
            vazio.acquire() # Espera por espaço vazio na esteira

            with lock_insercao_esteira: # Exclusão mútua entre Produtores (A, B, C)
                esteira_central.append(brinquedo)
                self.log(f"Inseriu **{brinquedo}** na Esteira. Tamanho atual: {len(esteira_central)}")

            cheio.release() # Sinaliza que há um item a mais na esteira

class DuendeE(Duende):
    # Retira da Esteira e Coloca no Trenó (Consumidor/Produtor do Trenó)
    def __init__(self, id_duende):
        super().__init__(f"DuendeE-{id_duende}", "E")

    def run(self):
        while True:
            # 1. Retira da Esteira (Consumidor da Esteira)
            cheio.acquire() # Espera que haja um item na esteira

            with lock_remocao_esteira: # Exclusão mútua entre Duendes E
                brinquedo = esteira_central.popleft()
                self.log(f"Retirou **{brinquedo}** da Esteira. Tamanho atual: {len(esteira_central)}")

            vazio.release() # Sinaliza que há um espaço a mais na esteira

            # 2. Coloca no Trenó (Produtor do Trenó)
            with lock_treno: # Exclusão mútua com Duendes E e D
                treno.append(brinquedo)
                self.log(f"Colocou {brinquedo} no Trenó. Total no Trenó: {len(treno)}")
            
            time.sleep(random.uniform(0.2, 0.8)) # Tempo para colocar no trenó

class DuendeD(Duende):
    # Realiza Conferência do Trenó (Acesso não concorrente, exceto com E)
    # Vários Duendes D podem trabalhar simultaneamente (não há concorrência entre D's)
    # mas o Duende E não permite acesso enquanto deposita.
    def __init__(self, id_duende):
        super().__init__(f"DuendeD-{id_duende}", "D")

    def run(self):
        while True:
            # O acesso é restrito APENAS quando Duende E está depositando.
            # Como a operação de conferência é apenas leitura, e o E usa o lock_treno
            # para escrita, usamos o mesmo lock para D garantir que E não está escrevendo.
            with lock_treno:
                if treno:
                    # Simula a conferência de todos os itens
                    self.log(f"Iniciando conferência de {len(treno)} brinquedos no Trenó...")
                    time.sleep(random.uniform(0.1, 0.5))
                    self.log(f"Conferência concluída. Total no Trenó: {len(treno)}")
                else:
                    self.log("Trenó vazio. Aguardando brinquedos...")

            time.sleep(random.uniform(1.0, 3.0)) # Intervalo entre conferências
