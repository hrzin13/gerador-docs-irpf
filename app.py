import streamlit as st
from PIL import Image, ImageDraw, ImageColor
import io

# Configuração da página
st.set_page_config(page_title="Estúdio de Crochê Pro", layout="centered")

st.title("🧶 Estúdio de Crochê Pro")
st.write("Gere seus gráficos (por foto ou padrões automáticos) e calcule o preço de venda.")

# ==========================================
# PARTE 1: CONFIGURAÇÃO DO GRÁFICO
# ==========================================
st.header("1️⃣ Parte 1: Gerador de Gráfico")

tipo_peca = st.radio("Como você vai tecer essa peça?", 
                     ["Circular (Tubo - Ex: Porta Bic, Touca)", 
                      "Plana (Ida e Volta - Ex: Tapete, Blusa)"])

st.write("### Como deseja criar o desenho?")
modo_entrada = st.radio("", ["📸 Subir Imagem do Celular", "📐 Gerar Padrão Geométrico (Automático)"])

# Variáveis globais para compartilhar entre as partes do código
largura_pontos = 20
altura_carreiras = 20
img_processada = None

# ---------------------------------------------------------
# MODO 1: SUBIR IMAGEM
# ---------------------------------------------------------
if modo_entrada == "📸 Subir Imagem do Celular":
    imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])
    
    if imagem_carregada is not None:
        img_temp = Image.open(imagem_carregada).convert('RGB')
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
        
        num_cores = st.slider("Quantas cores de linha vai usar?", min_value=2, max_value=20, value=3)
        
        # Prepara a imagem escolhida
        img_processada = img_temp.quantize(colors=num_cores).convert('RGB')
        img_processada = img_processada.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)

# ---------------------------------------------------------
# MODO 2: PADRÃO GEOMÉTRICO MATEMÁTICO
# ---------------------------------------------------------
else:
    st.write("#### Configure seu Padrão Geométrico")
    padrao_geometrico = st.selectbox("Selecione o desenho:", [
        "Xadrez 2x2 (Bloquinhos)", 
        "Xadrez 1x1 (Xadrezinho fino)", 
        "Listras Horizontais", 
        "Listras Verticais", 
        "Diagonal (Escadinha)"
    ])
    
    col_tam1, col_tam2 = st.columns(2)
    with col_tam1: largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=20)
    with col_tam2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=20)
    
    st.write("Escolha as 2 cores do seu padrão:")
    col_cor1, col_cor2 = st.columns(2)
    with col_cor1: cor1_hex = st.color_picker("Cor 1 (Fundo)", "#4A4A4A")
    with col_cor2: cor2_hex = st.color_picker("Cor 2 (Desenho)", "#FFD700")
    
    # Cria a imagem 100% via código matemático
    img_processada = Image.new('RGB', (largura_pontos, altura_carreiras))
    pixels_geo = img_processada.load()
    rgb1 = ImageColor.getrgb(cor1_hex)
    rgb2 = ImageColor.getrgb(cor2_hex)
    
    for y in range(altura_carreiras):
        for x in range(largura_pontos):
            if padrao_geometrico == "Xadrez 2x2 (Bloquinhos)":
                if (x // 2 + y // 2) % 2 == 0: pixels_geo[x, y] = rgb1
                else: pixels_geo[x, y] = rgb2
            elif padrao_geometrico == "Xadrez 1x1 (Xadrezinho fino)":
                if (x + y) % 2 == 0: pixels_geo[x, y] = rgb1
                else: pixels_geo[x, y] = rgb2
            elif padrao_geometrico == "Listras Horizontais":
                if (y // 2) % 2 == 0: pixels_geo[x, y] = rgb1
                else: pixels_geo[x, y] = rgb2
            elif padrao_geometrico == "Listras Verticais":
                if (x // 2) % 2 == 0: pixels_geo[x, y] = rgb1
                else: pixels_geo[x, y] = rgb2
            elif padrao_geometrico == "Diagonal (Escadinha)":
                if (x + y) % 3 == 0: pixels_geo[x, y] = rgb1
                else: pixels_geo[x, y] = rgb2


# ==========================================
# GERAÇÃO DO TABULEIRO VISUAL E BOTÃO
# ==========================================
if st.button("🎨 Gerar Tabuleiro e Baixar", type="primary"):
    if img_processada is not None:
        try:
            st.image(img_processada, caption=f"Prévia do Gráfico ({largura_pontos}x{altura_carreiras})", width=250)
            
            pixels = img_processada.load()
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
            st.download_button("📥 Baixar Tabuleiro (PNG)", data=buf.getvalue(), file_name="meu_grafico_croche.png", mime="image/png", type="secondary")
            
            st.write("### Visualização Rápida")
            st.markdown(html_grid, unsafe_allow_html=True)
            
            st.write("### Legenda de Cores")
            for rgb, num_cor in cores_encontradas.items():
                hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                st.markdown(f"**Cor {num_cor}:** <span style='background-color:{hex_color}; padding: 2px 25px; border-radius: 4px; border: 1px solid #aaa;'></span>", unsafe_allow_html=True)
        except Exception as e: st.error(f"Erro: {e}")
    else:
        st.warning("⚠️ Forneça uma imagem ou configure um padrão primeiro antes de gerar o tabuleiro.")

st.divider()

# ==========================================
# PARTE 2: CALCULADORA DE PRECIFICAÇÃO
# ==========================================
st.header("💰 Parte 2: Precificação Automática")
st.write("A matemática se baseia no tamanho do projeto ajustado na Parte 1.")

total_pontos = int(largura_pontos * altura_carreiras)
st.info(f"🧶 **Tamanho do projeto atual:** {total_pontos} pontos a serem tecidos.")

col_calc1, col_calc2 = st.columns(2)
with col_calc1:
    preco_novelo = st.number_input("Preço médio do Novelo (R$)", min_value=0.0, value=18.0, step=1.0)
    metros_novelo = st.number_input("Metros no Novelo (m)", min_value=1.0, value=150.0, step=10.0)
with col_calc2:
    valor_hora = st.number_input("Sua Hora de Trabalho (R$/h)", min_value=0.0, value=25.0, step=1.0)
    margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0.0, value=30.0, step=5.0)

metros_gastos = total_pontos * 0.045
custo_material = metros_gastos * (preco_novelo / metros_novelo)

minutos_totais = total_pontos / 20
horas_totais = minutos_totais / 60
custo_tempo = horas_totais * valor_hora

taxa_desgaste = 1.50 # Fixo para desgaste da agulha e materiais auxiliares
custo_producao = custo_material + custo_tempo + taxa_desgaste
valor_lucro = custo_producao * (margem_lucro / 100)
preco_final = custo_producao + valor_lucro

st.write("### 🧾 Relatório Financeiro")
col_res1, col_res2, col_res3 = st.columns(3)
col_res1.metric("Tempo Estimado", f"{int(horas_totais)}h {int(minutos_totais % 60)}m")
col_res2.metric("Custo Material", f"R$ {custo_material:.2f}")
col_res3.metric("Custo Mão de Obra", f"R$ {custo_tempo:.2f}")

st.success(f"### Preço Sugerido de Venda: R$ {preco_final:.2f}")
st.caption(f"*O preço sugerido cobre a sua mão de obra (R$ {custo_tempo:.2f}), o material gasto, o desgaste das ferramentas (R$ {taxa_desgaste:.2f}) e ainda garante R$ {valor_lucro:.2f} de lucro limpo para você ou para investir.*")

