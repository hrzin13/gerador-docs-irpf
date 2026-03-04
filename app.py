import streamlit as st
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Gráfico de Crochê", layout="centered")

st.title("🧶 Gerador de Gráfico: Porta Bic")
st.write("Transforme imagens em um tabuleiro quadriculado para crochê.")

# 1. Interface para anexar a imagem
imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])

st.write("### Ajustes do Gráfico")
col1, col2 = st.columns(2)
with col1:
    largura_pontos = st.number_input("Largura (Pontos)", min_value=5, max_value=50, value=20)
with col2:
    altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, max_value=50, value=20)

# NOVO: Filtro para evitar que a foto tenha 50 cores diferentes
st.write("### Simplificar Cores")
num_cores = st.slider("Quantas cores de linha você vai usar?", min_value=2, max_value=10, value=3)

# O Botão Mágico
if st.button("Gerar Tabuleiro", type="primary"):
    if imagem_carregada is not None:
        try:
            # Abre a imagem
            img = Image.open(imagem_carregada).convert('RGB')
            
            # Força a imagem a ter apenas a quantidade de cores que você escolheu no slider
            img = img.quantize(colors=num_cores).convert('RGB')
            
            # Redimensiona para formar a grade do crochê
            img = img.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
            
            st.image(img, caption="Prévia do desenho simplificado", width=200)

            pixels = img.load()
            
            # Identifica quais são as cores finais
            cores_encontradas = {}
            contador_cores = 1
            
            for y in range(altura_carreiras):
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    if rgb not in cores_encontradas:
                        cores_encontradas[rgb] = contador_cores
                        contador_cores += 1

            st.divider()
            st.subheader("🏁 Seu Tabuleiro de Crochê")
            st.write("Leia de baixo para cima (A carreira 1 é a base do isqueiro).")
            
            # CONSTRÓI O TABULEIRO VISUAL (HTML/CSS)
            html_grid = "<div style='display: flex; flex-direction: column; gap: 2px; overflow-x: auto; padding-bottom: 10px;'>"
            
            for y in range(altura_carreiras):
                html_grid += "<div style='display: flex; gap: 2px; min-width: max-content;'>"
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    num_cor = cores_encontradas[rgb]
                    
                    hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                    
                    # Calcula o brilho da cor para decidir se o número dentro fica preto ou branco (para dar pra ler)
                    brilho = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                    cor_texto = "black" if brilho > 128 else "white"
                    
                    # Desenha cada quadradinho
                    cell = f"<div style='background-color: {hex_color}; color: {cor_texto}; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; border-radius: 3px;'>{num_cor}</div>"
                    html_grid += cell
                
                # Adiciona o número da carreira na lateral direita
                numero_carreira = altura_carreiras - y
                html_grid += f"<div style='width: 40px; text-align: left; font-size: 12px; line-height: 25px; margin-left: 5px; color: #888;'>C {numero_carreira}</div>"
                html_grid += "</div>"
            
            html_grid += "</div>"
            
            # Renderiza o tabuleiro na tela do aplicativo
            st.markdown(html_grid, unsafe_allow_html=True)

            # Legenda
            st.divider()
            st.subheader("🎨 Legenda de Cores")
            for rgb, num_cor in cores_encontradas.items():
                hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                st.markdown(f"**Cor {num_cor}:** <span style='background-color:{hex_color}; padding: 2px 25px; border-radius: 4px; border: 1px solid #aaa;'></span>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gerar o gráfico: {e}")
    else:
        st.warning("⚠️ Anexe a imagem primeiro!")
