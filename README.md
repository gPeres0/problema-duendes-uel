# Problema dos Duendes
Trabalho 1 da disciplina de Sistemas Operacionais.  
*Gabriel Peres de Souza, Rodrigo M Silva Jr, João Carlos dos Santos Correa.*  

## ESPECIFIAÇÃO
O Papai Noel está fazendo as entregas dos presentes de Natal, para isso conta com a ajuda dos
duendes na produção e carregamento do trenó.
Elementos do fábrica do Papai Noel:
1. **Esteira central**: possui 10 lugares, não pode haver sobreposição de elementos, o acesso a
esteira é restritivo entre os elementos de um mesmo grupos de duendes, ou seja, dentro do
grupo que insere, somente um doente tem acesso por vez e dentro do grupo que retira,
somente um acesso por vez;  
◦ Duendes que inserem brinquedos na esteira: A, B e C;  
◦ Duendes que retiram brinquedos da esteira: E;

2. **Trenó**: tamanho infinito;
3. **Duende do tipo A**: produz carrinhos e insere na esteira;
4. **Duende do tipo B**: produz bonecas e bolas (alternadamente) e os coloca na esteira;
5. **Duende do tipo C**: produz bolas e as coloca na esteira;
6. **Duende do tipo D**: realiza a conferência dos brinquedos colocados no trenó;
7. **Duende do tipo E**: retira brinquedos da esteira e coloca no trenó;

Existem vários duendes D trabalhando simultaneamente, pois não há concorrência entre eles.  
O duente E não permite que outros estejam mechendo no trenó enquanto ele deposita os brinquedos, ou seja, nenhum duende E ou D pode estar acessando o trenó.  
A mesa de produção de bolas possui somente dois bancos (ou seja, no máximo dois duendes podem estar trabalhando simultaneamente).  
Implemente threads para representar cada um dos tipos de duendes, utilize o menor número possível de semáforo para sincronizar as atividades. Sua solução deve funcionar para um número qualquer de duendes de cada tipo.