import streamlit as st
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Gráfico de Crochê", layout="centered")

st.title("🧶 Gerador de Gráfico: Porta Bic")
st.write("Transforme imagens em receitas escritas de crochê.")

# 1. Interface para anexar a imagem (Botão de Upload)
imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])

# 2. Caixas para você digitar o tamanho do isqueiro
st.write("### Ajuste o tamanho da peça")
col1, col2 = st.columns(2)
with col1:
    largura_pontos = st.number_input("Largura (Pontos)", min_value=5, max_value=50, value=16)
with col2:
    altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, max_value=50, value=15)

# 3. O Botão Mágico
if st.button("Gerar Receita Escrita", type="primary"):
    if imagem_carregada is not None:
        try:
            # Abre a imagem que você subiu
            img = Image.open(imagem_carregada).convert('RGB')
            # Redimensiona para o tamanho dos pontos, mantendo o estilo pixel art
            img = img.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
            
            # Mostra a imagem como ela vai ficar no crochê
            st.image(img, caption="Prévia de como vai ficar no crochê", width=200)

            pixels = img.load()
            cores_encontradas = {}
            contador_cores = 1
            
            st.divider()
            st.subheader(f"📝 Passo a Passo ({largura_pontos} pontos por carreira)")
            st.write("Lendo de baixo para cima (padrão circular):")
            
            # A lógica pesada lendo a matriz
            for y in range(altura_carreiras - 1, -1, -1):
                carreira_atual = []
                cor_atual = None
                contagem = 0
                
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    if rgb not in cores_encontradas:
                        cores_encontradas[rgb] = f"Cor {contador_cores}"
                        contador_cores += 1
                    
                    nome_cor = cores_encontradas[rgb]
                    
                    if nome_cor == cor_atual:
                        contagem += 1
                    else:
                        if cor_atual is not None:
                            carreira_atual.append(f"**{contagem}** {cor_atual}")
                        cor_atual = nome_cor
                        contagem = 1
                        
                if cor_atual is not None:
                    carreira_atual.append(f"**{contagem}** {cor_atual}")
                    
                numero_carreira = altura_carreiras - y
                texto_carreira = " ➔ ".join(carreira_atual)
                
                # Escreve a carreira na tela do Streamlit
                st.write(f"**Carr {numero_carreira}:** {texto_carreira}")

            # Mostra a legenda de cores
            st.divider()
            st.subheader("🎨 Legenda de Cores")
            for rgb, nome in cores_encontradas.items():
                hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                # Cria um bloquinho de cor HTML para facilitar a visualização
                st.markdown(f"**{nome}:** <span style='background-color:{hex_color}; padding: 2px 15px; border-radius: 4px; border: 1px solid #ddd;'></span>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Opa, deu um erro ao processar a imagem: {e}")
    else:
        st.warning("⚠️ Você esqueceu de anexar a imagem ali em cima!")
