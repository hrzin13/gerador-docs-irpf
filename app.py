import streamlit as st
from PIL import Image, ImageDraw
import io

# Configuração da página
st.set_page_config(page_title="Gráfico de Crochê", layout="centered")

st.title("🧶 Gerador de Gráfico Pro")
st.write("Crie seu tabuleiro, mantenha a proporção perfeita e baixe para imprimir.")

# 1. Interface
imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])

st.write("### Ajustes do Projeto")
tipo_peca = st.radio("Como você vai tecer essa peça?", 
                     ["Circular (Tubo - Ex: Porta Bic, Touca)", 
                      "Plana (Ida e Volta - Ex: Tapete, Blusa)"])

# --- A MÁGICA DA PROPORÇÃO AUTOMÁTICA ENTRA AQUI ---
if imagem_carregada is not None:
    # O código abre a imagem escondido só para pegar o tamanho real dela
    img_temp = Image.open(imagem_carregada)
    largura_original, altura_original = img_temp.size
    proporcao = altura_original / largura_original 
    
    st.info(f"📐 A proporção original da sua imagem é {largura_original}x{altura_original}. O aplicativo vai sugerir a altura ideal automaticamente!")
    
    col1, col2 = st.columns(2)
    with col1:
        # Você escolhe a largura primeiro
        largura_pontos = st.number_input("Largura desejada (Pontos)", min_value=5, value=20)
    
    with col2:
        # O código calcula a altura ideal e já preenche a caixinha para você
        altura_calculada = int(largura_pontos * proporcao)
        # Garantir que a altura não seja zero
        altura_calculada = max(5, altura_calculada) 
        altura_carreiras = st.number_input("Altura (Carreiras) - Recomendada", min_value=5, value=altura_calculada)

else:
    # Se ainda não anexou a imagem, mostra as caixas padrão 20x20
    col1, col2 = st.columns(2)
    with col1:
        largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=20)
    with col2:
        altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=20)

st.write("### Simplificar Cores")
num_cores = st.slider("Quantas cores de linha vai usar?", min_value=2, max_value=20, value=3)

# O Botão Mágico
if st.button("Gerar Tabuleiro e Baixar", type="primary"):
    if imagem_carregada is not None:
        try:
            # --- PROCESSAMENTO DA IMAGEM ---
            img = Image.open(imagem_carregada).convert('RGB')
            img = img.quantize(colors=num_cores).convert('RGB')
            img = img.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
            pixels = img.load()
            
            cores_encontradas = {}
            contador_cores = 1
            for y in range(altura_carreiras):
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    if rgb not in cores_encontradas:
                        cores_encontradas[rgb] = contador_cores
                        contador_cores += 1

            # --- GERAÇÃO DA IMAGEM EM ALTA RESOLUÇÃO PARA DOWNLOAD ---
            tamanho_quadrado = 40 
            largura_img = largura_pontos * tamanho_quadrado
            altura_img = altura_carreiras * tamanho_quadrado
            
            img_download = Image.new('RGB', (largura_img, altura_img), color='white')
            draw = ImageDraw.Draw(img_download)
            
            html_grid = "<div style='display: flex; flex-direction: column; gap: 1px; overflow-x: auto; padding-bottom: 10px;'>"
            
            for y in range(altura_carreiras):
                html_grid += "<div style='display: flex; gap: 1px; min-width: max-content;'>"
                
                numero_carreira = altura_carreiras - y
                direcao = "➔" 
                if "Plana" in tipo_peca and numero_carreira % 2 == 0:
                    direcao = "⬅️" 
                
                html_grid += f"<div style='width: 50px; text-align: right; font-size: 12px; margin-right: 5px; color: #888;'>C {numero_carreira} {direcao}</div>"
                
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    num_cor = cores_encontradas[rgb]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                    
                    brilho = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
                    cor_texto = "black" if brilho > 128 else "white"
                    
                    # Desenha no HTML (Celular)
                    tamanho_tela = "25px" if largura_pontos <= 40 else "12px"
                    fonte_tela = "12px" if largura_pontos <= 40 else "0px"
                    cell = f"<div style='background-color: {hex_color}; color: {cor_texto}; width: {tamanho_tela}; height: {tamanho_tela}; display: flex; align-items: center; justify-content: center; font-size: {fonte_tela}; font-weight: bold; border-radius: 2px;'>{num_cor}</div>"
                    html_grid += cell
                    
                    # Desenha na Imagem de Alta Resolução
                    x0 = x * tamanho_quadrado
                    y0 = y * tamanho_quadrado
                    x1 = x0 + tamanho_quadrado
                    y1 = y0 + tamanho_quadrado
                    draw.rectangle([x0, y0, x1, y1], fill=rgb, outline="black")
                    
                    if largura_pontos <= 100: 
                        draw.text((x0 + 15, y0 + 10), str(num_cor), fill=cor_texto)

                html_grid += "</div>"
            html_grid += "</div>"
            
            st.divider()
            
            # --- BOTÃO DE DOWNLOAD ---
            buf = io.BytesIO()
            img_download.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success("✅ Tabuleiro gerado com sucesso sem distorção!")
            st.download_button(
                label="📥 Baixar Tabuleiro para Imprimir (PNG)",
                data=byte_im,
                file_name="meu_grafico_croche_proporcional.png",
                mime="image/png",
                type="primary"
            )
            
            st.write("### Visualização Rápida")
            st.markdown(html_grid, unsafe_allow_html=True)

            st.divider()
            st.subheader("🎨 Legenda de Cores")
            for rgb, num_cor in cores_encontradas.items():
                hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                st.markdown(f"**Cor {num_cor}:** <span style='background-color:{hex_color}; padding: 2px 25px; border-radius: 4px; border: 1px solid #aaa;'></span>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Erro ao gerar o gráfico: {e}")
    else:
        st.warning("⚠️ Anexe a imagem primeiro!")
