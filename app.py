def calcular_preco_justo(pontos_totais, preco_novelo, metros_novelo, valor_hora, margem_lucro):
    print("\n" + "="*40)
    print("💰 CALCULADORA DE PRECIFICAÇÃO PRO")
    print("="*40)

    # 1. Custo de Material (Custo Direto)
    # Sabendo que 1 ponto baixo gasta em média 0.045 metros (4,5 cm)
    metros_gastos = pontos_totais * 0.045
    custo_por_metro = preco_novelo / metros_novelo
    custo_material = metros_gastos * custo_por_metro

    # 2. Custo da Mão de Obra
    # Estimativa de 20 pontos por minuto (com troca de fio conduzido)
    minutos_totais = pontos_totais / 20
    horas_totais = minutos_totais / 60
    custo_tempo = horas_totais * valor_hora

    # 3. Taxa de Desgaste (Fixo)
    # A agulha de bambu e a tesoura sofrem desgaste. 
    # Adicionamos um valor simbólico de reserva para reposição de ferramentas.
    taxa_desgaste = 1.50 

    # 4. Ponto de Equilíbrio (Custo de Produção)
    # Se vender por esse valor, não tem lucro, mas também não paga para trabalhar.
    custo_producao = custo_material + custo_tempo + taxa_desgaste

    # 5. Margem de Lucro (Markup)
    # O valor que efetivamente vai para o bolso do artesão para a empresa crescer.
    valor_lucro = custo_producao * (margem_lucro / 100)
    
    # 6. Preço Final Sugerido
    preco_final = custo_producao + valor_lucro

    # --- EXIBIÇÃO DO RELATÓRIO ---
    print(f"🧶 Tamanho do Projeto: {pontos_totais} pontos")
    print(f"⏱️ Tempo Estimado: {horas_totais:.1f} horas\n")
    
    print("--- ESTRUTURA DE CUSTOS ---")
    print(f"Material (Linha):     R$ {custo_material:.2f}")
    print(f"Mão de Obra:          R$ {custo_tempo:.2f} (a R${valor_hora}/h)")
    print(f"Desgaste Ferramentas: R$ {taxa_desgaste:.2f}")
    print(f"Custo de Produção:    R$ {custo_producao:.2f}\n")
    
    print("--- FECHAMENTO ---")
    print(f"Lucro Desejado ({margem_lucro}%): R$ {valor_lucro:.2f}")
    print(f"PREÇO FINAL SUGERIDO: R$ {preco_final:.2f}")
    print("="*40 + "\n")

    return preco_final

# --- ÁREA DE TESTE ---
# Vamos simular um Porta Bic de 20 pontos de largura x 20 carreiras = 400 pontos.
# Novelo custa R$ 18,00 e vem 150 metros.
# Você quer ganhar R$ 25,00 por hora de trabalho.
# E quer uma margem de lucro de 30% em cima da peça.

calcular_preco_justo(
    pontos_totais=400, 
    preco_novelo=18.00, 
    metros_novelo=150, 
    valor_hora=25.00, 
    margem_lucro=30
)
