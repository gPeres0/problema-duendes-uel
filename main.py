import time
from duendes import treno, esteira_central, DuendeA, DuendeB, DuendeC, DuendeD, DuendeE

def iniciar_fabrica(num_A, num_B, num_C, num_D, num_E, tempo_execucao=10):
    duendes = []
    
    # Cria Duendes Produtores
    for i in range(num_A):
        duendes.append(DuendeA(i+1))
    for i in range(num_B):
        duendes.append(DuendeB(i+1))
    for i in range(num_C):
        duendes.append(DuendeC(i+1))
        
    # Cria Duendes de Carregamento e Conferência
    for i in range(num_E):
        duendes.append(DuendeE(i+1))
    # Vários Duendes D podem trabalhar (não há concorrência entre eles,
    # apenas com E), então podemos ter múltiplos D's.
    for i in range(num_D):
        duendes.append(DuendeD(i+1))

    print("--- 🏭 Iniciando a Fábrica do Papai Noel ---")
    
    # Inicia todas as threads
    for d in duendes:
        d.start()

    # Deixa a fábrica funcionar por um tempo
    print(f"Fábrica rodando por {tempo_execucao} segundos...")
    time.sleep(tempo_execucao)

    # O Papai Noel chama o encerramento (não implementado no loop infinito,
    # mas o programa principal pode terminar as threads se necessário,
    # em um cenário real precisaríamos de um flag de controle).
    # Para este exemplo simples, o programa principal simplesmente encerra.
    print("\n--- 🛑 Encerrando simulação ---")
    print(f"Total de itens na Esteira Central ao fim: {len(esteira_central)}")
    print(f"Total de itens no Trenó ao fim: {len(treno)}")
    print("------------------------------------------")

# Exemplo de uso:
iniciar_fabrica(
    num_A=2, # Duendes A (Carrinhos)
    num_B=1, # Duendes B (Bonecas e Bolas)
    num_C=1, # Duendes C (Bolas)
    num_E=1, # Duendes E (Retiram/Carregam)
    num_D=2, # Duendes D (Conferem)
    tempo_execucao=15 # Simulação por 15 segundos
)