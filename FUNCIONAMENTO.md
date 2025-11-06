# Fábrica do Papai Noel
<!--Documentação: JC-->

## Como executar
Requer **Python 3.9+**. Na mesma pasta do `main.py`, rode:

```bash
python main.py
```

### Opções
<!--Opções e UI: Roger-->
- `--A, --B, --C, --D, --E` → **quantidade** de duendes de cada tipo  
  **Padrões:** `A=2, B=1, C=2, D=3, E=2`
- `--capacidade` → capacidade da **esteira** (padrão: `10`)
- `--tempo` → duração da simulação, em segundos (padrão: `20`)
- `--vel` → **velocidade** (maior que 1 acelera) — padrão: `1.25`
- `--semcor` → desativa as cores ANSI
- `--seed` → controlar aleatoriedade (ex.: `--seed 42`)

Exemplo:
```bash
python main.py --A 2 --B 1 --C 2 --D 3 --E 2 --tempo 25 --vel 1.5
```

## O que cada duende faz
- **A** → produz **carrinhos** e insere na **esteira**.  
- **B** → produz **boneca** e **bola** **alternadamente** e insere na esteira.  
- **C** → produz **bola** e insere na esteira.  
- **E** → **retira** da esteira e **deposita** no **trenó**.  
- **D** → faz **conferência** dos brinquedos **no trenó** (apenas leitura).

## Restrições
<!--Funcionamento: Peres-->
- **Esteira (capacidade 10 por padrão)**: estrutura com `Condition` que bloqueia quando cheia/vazia.  
  - Grupo de quem **insere** (A/B/C): **apenas um por vez** no ato de inserir → `portao_inserir` (`Semaphore(1)`).  
  - Grupo de quem **retira** (E): **apenas um por vez** no ato de retirar → `portao_retirar` (`Semaphore(1)`).  
- **Mesa de bolas (2 bancos)**: no máximo **2** duendes produzindo **bola** simultaneamente  
  (B quando for a vez de bola, e todos C) → `bancos_bolas` (`Semaphore(2)`).  
- **Trenó (tamanho “infinito”)**:
  - Vários **D** podem conferir **ao mesmo tempo** → atuam como **leitores**.  
  - Enquanto um **E** deposita, **ninguém** mexe no trenó (nem D, nem outro E) → **escritor exclusivo**.  
  Implementado com **trava leitores–escritor** (`TravaLeitoresEscritor`).

## Mínimo possível de semáforos:
<!--Funcionamento: Peres-->
Somente os necessários pelas regras do enunciado:
- `portao_inserir` (1) para o grupo que **insere** na esteira.
- `portao_retirar` (1) para o grupo que **retira** da esteira.
- `bancos_bolas` (2) para limitar **produção de bolas**.
O restante usa monitor (`Condition`) para a esteira e a trava leitores–escritor para o trenó.

## Visual no terminal
<!--Opções e UI: Roger-->
Cada ação imprime:
- Quem produziu/retirou/depositou (com **emoji** do brinquedo).
- Estado da **esteira** como barra: `[#####.....]` e total no **trenó**.
- Ao final, um **resumo** com contagens **produzidas** e **entregues**.

## Encerramento limpo
<!--Opções e UI: Roger-->
- O programa roda pelo tempo configurado (`--tempo`) e encerra automaticamente.
- `CTRL+C` também finaliza de forma segura (acorda quem estiver bloqueado).

## Decisões relevantes
<!--Funcionamento: Peres-->
- A alternância do **Duende B** é independente **para cada B** (cada thread lembra o último item produzido).  
- **Duendes D** apenas **leem** o trenó (não removem itens).  
- A política da trava leitores–escritor é simples e suficiente para a simulação (não há prioridade sofisticada).
