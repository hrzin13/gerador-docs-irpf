import streamlit as st
from PIL import Image, ImageDraw
import io

st.set_page_config(page_title="Gráfico de Crochê Pro", layout="centered")

st.title("🧶 Gerador de Gráfico Pro")
st.write("Crie seu tabuleiro, calcule o tempo de produção e o custo exato.")

imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])

st.write("### Ajustes do Projeto")
tipo_peca = st.radio("Como você vai tecer essa peça?", 
                     ["Circular (Tubo - Ex: Porta Bic, Touca)", 
                      "Plana (Ida e Volta - Ex: Tapete, Blusa)"])

if imagem_carregada is not None:
    img_temp = Image.open(imagem_carregada)
    largura_original, altura_original = img_temp.size
    proporcao = altura_original / largura_original 
    
    st.info(f"📐 Resolução original da imagem: {largura_original}x{altura_original}.")
    
    opcao_tamanho = st.radio(
        "Escolha o Nível de Detalhe (Resolução):",
        ["🟢 Pequeno (Max 30 pontos)", "🟡 Médio (Max 60 pontos)", "🔴 Grande (Max 100 pontos)", "⚙️ Personalizado"]
    )

    if "Pequeno" in opcao_tamanho: max_dim = 30
    elif "Médio" in opcao_tamanho: max_dim = 60
    elif "Grande" in opcao_tamanho: max_dim = 100
    else: max_dim = None

    if max_dim:
        if largura_original > altura_original:
            largura_pontos = max_dim
            altura_carreiras = max(5, int(max_dim * proporcao))
        else:
            altura_carreiras = max_dim
            largura_pontos = max(5, int(max_dim / proporcao))
        st.success(f"**Tamanho ajustado:** {largura_pontos} pontos x {altura_carreiras} carreiras.")
    else:
        col1, col2 = st.columns(2)
        with col1: largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=20)
        with col2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=max(5, int(largura_pontos * proporcao)))
else:
    col1, col2 = st.columns(2)
    with col1: largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=20)
    with col2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=20)

st.write("### Simplificar Cores")
num_cores = st.slider("Quantas cores de linha vai usar?", min_value=2, max_value=20, value=3)

st.divider()
st.write("### 💰 Cálculo de Custo (Opcional)")
col_c1, col_c2 = st.columns(2)
with col_c1: preco_novelo = st.number_input("Preço do Novelo (R$)", min_value=0.0, value=0.0, step=1.0)
with col_c2: metros_novelo = st.number_input("Metros no Novelo (m)", min_value=0.0, value=0.0, step=10.0)

total_pontos = int(largura_pontos * altura_carreiras)
minutos_totais = int(total_pontos / 20)
horas = minutos_totais // 60
minutos_restantes = minutos_totais % 60

metros_gastos = total_pontos * 0.045
custo_total = 0.0 if (preco_novelo == 0 or metros_novelo == 0) else (metros_gastos * (preco_novelo / metros_novelo))

st.divider()
st.subheader("📊 Previsão")
st.write(f"**Pontos:** {total_pontos} | **Tempo:** {horas}h e {minutos_restantes}min")
if custo_total > 0: st.success(f"**Custo material:** R$ {custo_total:.2f}")

if st.button("Gerar Tabuleiro e Baixar", type="primary"):
    if imagem_carregada is not None:
        try:
            img = Image.open(imagem_carregada).convert('RGB').quantize(colors=num_cores).convert('RGB')
            img = img.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
            st.image(img, caption=f"Prévia da peça", width=250)
            
            pixels = img.load()
            cores_encontradas = {}
            contador_cores = 1
            for y in range(altura_carreiras):
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    if rgb not in cores_encontradas:
                        cores_encontradas[rgb] = contador_cores
                        contador_cores += 1

            tamanho_quadrado = 40 
            img_download = Image.new('RGB', (largura_pontos * tamanho_quadrado, altura_carreiras * tamanho_quadrado), color='white')
            draw = ImageDraw.Draw(img_download)
            
            html_grid = "<div style='display: flex; flex-direction: column; gap: 1px; overflow-x: auto; padding-bottom: 10px;'>"
            for y in range(altura_carreiras):
                html_grid += "<div style='display: flex; gap: 1px; min-width: max-content;'>"
                num_carr = altura_carreiras - y
                dir = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                html_grid += f"<div style='width: 50px; text-align: right; font-size: 12px; margin-right: 5px; color: #888;'>C {num_carr} {dir}</div>"
                
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    num_cor = cores_encontradas[rgb]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                    brilho = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
                    cor_texto = "black" if brilho > 128 else "white"
                    
                    tam_tela = "25px" if largura_pontos <= 40 else "12px"
                    fnt_tela = "12px" if largura_pontos <= 40 else "0px"
                    html_grid += f"<div style='background-color: {hex_color}; color: {cor_texto}; width: {tam_tela}; height: {tam_tela}; display: flex; align-items: center; justify-content: center; font-size: {fnt_tela}; font-weight: bold; border-radius: 2px;'>{num_cor}</div>"
                    
                    x0, y0 = x * tamanho_quadrado, y * tamanho_quadrado
                    draw.rectangle([x0, y0, x0+tamanho_quadrado, y0+tamanho_quadrado], fill=rgb, outline="black")
                    if largura_pontos <= 100: draw.text((x0 + 15, y0 + 10), str(num_cor), fill=cor_texto)
                html_grid += "</div>"
            html_grid += "</div>"
            
            buf = io.BytesIO()
            img_download.save(buf, format="PNG")
            st.download_button("📥 Baixar Tabuleiro (PNG)", data=buf.getvalue(), file_name="grafico.png", mime="image/png", type="primary")
            st.write("### Visualização Rápida")
            st.markdown(html_grid, unsafe_allow_html=True)
            
            st.divider()
            for rgb, num_cor in cores_encontradas.items():
                hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                st.markdown(f"**Cor {num_cor}:** <span style='background-color:{hex_color}; padding: 2px 25px; border-radius: 4px; border: 1px solid #aaa;'></span>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Erro: {e}")
