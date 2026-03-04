from PIL import Image

def gerar_receita_croche(caminho_imagem, largura_pontos=16, altura_carreiras=20):
    print("Iniciando a leitura do gráfico...")
    
    try:
        # Abre a imagem e redimensiona para a matriz do porta Bic
        # Usamos NEAREST para não embaçar a imagem e manter o estilo "pixel art"
        img = Image.open(caminho_imagem).convert('RGB')
        img = img.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
    except Exception as e:
        print(f"Erro ao abrir a imagem: {e}")
        print("Dica: Verifique se o nome do arquivo está certinho e na mesma pasta do script.")
        return

    pixels = img.load()

    # Dicionário para dar nomes fáceis às cores (Cor 1, Cor 2...)
    cores_encontradas = {}
    contador_cores = 1

    print(f"\n--- RECEITA DE CROCHÊ: PORTA BIC ({largura_pontos} pontos) ---")
    print("Lendo de baixo para cima (padrão cilíndrico):\n")

    # O loop lê de baixo (altura_carreiras - 1) até o topo (0)
    for y in range(altura_carreiras - 1, -1, -1):
        carreira_atual = []
        cor_atual = None
        contagem = 0

        # Lê os pontos da esquerda para a direita
        for x in range(largura_pontos):
            rgb = pixels[x, y]

            # Se for uma cor nova, registra no dicionário
            if rgb not in cores_encontradas:
                cores_encontradas[rgb] = f"Cor {contador_cores}"
                contador_cores += 1

            nome_cor = cores_encontradas[rgb]

            # Lógica para agrupar pontos da mesma cor em sequência
            if nome_cor == cor_atual:
                contagem += 1
            else:
                if cor_atual is not None:
                    carreira_atual.append(f"{contagem} {cor_atual}")
                cor_atual = nome_cor
                contagem = 1

        # Adiciona o último bloco de cor daquela linha
        if cor_atual is not None:
            carreira_atual.append(f"{contagem} {cor_atual}")

        numero_carreira = altura_carreiras - y
        texto_carreira = ", ".join(carreira_atual)
        print(f"Carreira {numero_carreira}: {texto_carreira}")

    print("\n--- LEGENDA DE CORES (Baseado no RGB) ---")
    for rgb, nome in cores_encontradas.items():
        print(f"{nome}: {rgb}")

# COMO USAR:
# 1. Salve uma imagem simples (ex: um coração pixel art) na mesma pasta.
# 2. Mude 'sua_imagem.jpg' para o nome do seu arquivo.
# 3. Ajuste a largura para a quantidade de pontos do seu isqueiro.
gerar_receita_croche('sua_imagem.jpg', largura_pontos=16, altura_carreiras=15)
