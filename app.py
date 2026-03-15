import streamlit as st
from PIL import Image, ImageDraw, ImageColor
import io
import json
import os
import csv
from datetime import datetime
import math 

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BLINDAGEM DO CELULAR
# ==========================================
st.set_page_config(page_title="Estúdio de Crochê Pro", layout="centered")

st.markdown("""
<style>
    /* BLOQUEAR O PULL-TO-REFRESH NO CELULAR (Não recarrega perdendo dados) */
    html, body, .stApp {
        overscroll-behavior-y: contain; 
        overflow-y: auto;
    }
    /* Esconder elementos do Streamlit para parecer App Nativo */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA (SESSÃO)
# ==========================================
if 'ponto_parada' not in st.session_state:
    st.session_state.ponto_parada = 1
if 'grafico_ativo' not in st.session_state:
    st.session_state.grafico_ativo = False

# ==========================================
# MOTOR DE BASE DE DADOS (JSON) COM HISTÓRICO
# ==========================================
FICHEIRO_BD = "contabilidade_croche.json"

def carregar_bd():
    if not os.path.exists(FICHEIRO_BD):
        return {"inventario": {}, "lucro_acumulado": 0.0, "pecas_produzidas": 0, "historico_vendas": []}
    with open(FICHEIRO_BD, "r", encoding="utf-8") as f:
        dados = json.load(f)
        if "historico_vendas" not in dados:
            dados["historico_vendas"] = []
        return dados

def guardar_bd(dados):
    with open(FICHEIRO_BD, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4)

bd = carregar_bd()

st.title("🧶 Estúdio de Crochê Pro")
st.write("Gere gráficos, controle o inventário e exporte os seus relatórios financeiros.")

tab_gerador, tab_gestao = st.tabs(["🎨 Gerador de Gráfico", "📊 Gestão, Inventário e Relatórios"])

# ==========================================
# SEPARADOR 1: GERADOR DE GRÁFICO
# ==========================================
with tab_gerador:
    st.header("1️⃣ Parte 1: Gerador de Gráfico")

    tipo_peca = st.radio("Como você vai tecer essa peça?", 
                         ["Circular (Tubo - Ex: Porta Bic, Touca)", 
                          "Plana (Ida e Volta - Ex: Tapete, Blusa)"])

    st.write("### Como deseja criar o desenho?")
    modo_entrada = st.radio("", ["📸 Subir Imagem do Celular", "📐 Gerar Padrão Matemático (Automático)"])

    largura_pontos = 20
    altura_carreiras = 20
    img_processada = None

    if modo_entrada == "📸 Subir Imagem do Celular":
        imagem_carregada = st.file_uploader("Anexe o seu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])
        
        if imagem_carregada is not None:
            img_temp = Image.open(imagem_carregada).convert('RGB')
            largura_original, altura_original = img_temp.size
            proporcao = altura_original / largura_original 
            
            st.info(f"📐 Resolução original da imagem: {largura_original}x{altura_original}.")
            
            opcao_tamanho = st.radio("Escolha o Nível de Detalhe:", ["🟢 Pequeno (Max 30 pts)", "🟡 Médio (Max 60 pts)", "🔴 Grande (Max 100 pts)", "⚙️ Personalizado"])

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
            
            img_processada = img_temp.quantize(colors=num_cores).convert('RGB')
            img_processada = img_processada.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)

    else:
        st.write("#### Configure seu Padrão Gerado")
        categoria_padrao = st.selectbox("📁 Escolha a Categoria:", ["Geométricos Clássicos", "Símbolos e Arte", "Times Paulistas"])
        
        if categoria_padrao == "Geométricos Clássicos":
            lista_padroes = ["Xadrez 2x2 (Bloquinhos)", "Xadrez 1x1 (Xadrezinho fino)", "Listras Horizontais", "Listras Verticais", "Diagonal (Escadinha)", "Tijolinhos", "Ziguezague (Chevron)", "Bolinhas (Poá)", "Cruz Central (Única)", "Moldura / Borda", "Losangos"]
        elif categoria_padrao == "Times Paulistas":
            lista_padroes = ["Palmeiras", "São Paulo", "Corinthians", "Santos"]
        else:
            lista_padroes = ["Folha (Arte Botânica)", "Coração (Pixel Art)"]
            
        padrao_geometrico = st.selectbox("✨ Selecione o desenho:", lista_padroes)
        
        col_tam1, col_tam2 = st.columns(2)
        with col_tam1: largura_pontos = st.number_input("Largura (Pontos)", min_value=10, value=40) 
        with col_tam2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=10, value=40)
        
        st.write("Escolha as 2 cores do seu padrão:")
        
        # Inteligência para sugerir as cores certas dos times
        cor_fundo_default = "#2C2C2C"
        cor_desenho_default = "#FFD700"
        if padrao_geometrico == "Palmeiras": 
            cor_fundo_default = "#006400" # Verde Escuro
            cor_desenho_default = "#FFFFFF" # Branco
        elif padrao_geometrico == "São Paulo":
            cor_fundo_default = "#FFFFFF" # Branco
            cor_desenho_default = "#FF0000" # Vermelho
        elif padrao_geometrico == "Corinthians":
            cor_fundo_default = "#000000" # Preto
            cor_desenho_default = "#FFFFFF" # Branco
        elif padrao_geometrico == "Santos":
            cor_fundo_default = "#FFFFFF" # Branco
            cor_desenho_default = "#000000" # Preto
        elif padrao_geometrico == "Folha (Arte Botânica)":
            cor_desenho_default = "#00FF00"
            
        col_cor1, col_cor2 = st.columns(2)
        with col_cor1: cor1_hex = st.color_picker("Cor 1 (Fundo)", cor_fundo_default)
        with col_cor2: cor2_hex = st.color_picker("Cor 2 (Desenho)", cor_desenho_default)
        
        img_processada = Image.new('RGB', (largura_pontos, altura_carreiras))
        pixels_geo = img_processada.load()
        rgb1, rgb2 = ImageColor.getrgb(cor1_hex), ImageColor.getrgb(cor2_hex)
        
        for y in range(altura_carreiras):
            for x in range(largura_pontos):
                if padrao_geometrico == "Xadrez 2x2 (Bloquinhos)": pixels_geo[x, y] = rgb1 if (x // 2 + y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Xadrez 1x1 (Xadrezinho fino)": pixels_geo[x, y] = rgb1 if (x + y) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Horizontais": pixels_geo[x, y] = rgb1 if (y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Verticais": pixels_geo[x, y] = rgb1 if (x // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Diagonal (Escadinha)": pixels_geo[x, y] = rgb1 if (x + y) % 3 == 0 else rgb2
                elif padrao_geometrico == "Tijolinhos": pixels_geo[x, y] = rgb1 if (x + (y // 2) * 3) % 6 < 3 else rgb2
                elif padrao_geometrico == "Ziguezague (Chevron)": pixels_geo[x, y] = rgb2 if (x + y) % 4 == 0 or (x - y) % 4 == 0 else rgb1
                elif padrao_geometrico == "Bolinhas (Poá)": pixels_geo[x, y] = rgb2 if x % 4 == 0 and y % 4 == 0 else rgb1
                elif padrao_geometrico == "Cruz Central (Única)": pixels_geo[x, y] = rgb2 if x == largura_pontos // 2 or y == altura_carreiras // 2 else rgb1
                elif padrao_geometrico == "Moldura / Borda": pixels_geo[x, y] = rgb2 if x < 2 or x > largura_pontos - 3 or y < 2 or y > altura_carreiras - 3 else rgb1
                elif padrao_geometrico == "Losangos": pixels_geo[x, y] = rgb2 if (abs(x % 10 - 5) + abs(y % 10 - 5)) < 4 else rgb1
                elif padrao_geometrico == "Folha (Arte Botânica)":
                    cx, cy = largura_pontos / 2, altura_carreiras * 0.75 
                    dx, dy = x - cx, cy - y 
                    dist, angle = math.hypot(dx, dy), math.atan2(dy, dx) if dx != 0 or dy != 0 else 0
                    if -1 <= dx <= 1 and cy <= y <= cy + (altura_carreiras * 0.2): pixels_geo[x, y] = rgb2
                    elif 0 <= angle <= math.pi:
                        tamanho_max = (altura_carreiras * 0.6) * (1 - 0.3 * abs(math.cos(angle)))
                        limite_raio = tamanho_max * abs(math.sin(7 * angle))
                        pixels_geo[x, y] = rgb2 if dist <= limite_raio else rgb1
                    else: pixels_geo[x, y] = rgb1
                elif padrao_geometrico == "Coração (Pixel Art)":
                    cx, cy, escala = largura_pontos / 2, altura_carreiras / 2, min(largura_pontos, altura_carreiras) / 2.5
                    vx, vy = (x - cx) / escala, (cy - y) / (escala * 1.1)
                    pixels_geo[x, y] = rgb2 if (vx**2 + vy**2 - 1)**3 - (vx**2) * (vy**3) <= 0 else rgb1
                
                # MATEMÁTICA DOS TIMES PAULISTAS:
                elif padrao_geometrico == "Palmeiras":
                    cx, cy = largura_pontos / 2, altura_carreiras / 2
                    r = min(largura_pontos, altura_carreiras) * 0.4
                    dist = math.hypot(x - cx, y - cy)
                    is_logo = False
                    if r * 0.75 <= dist <= r: is_logo = True  # Anel externo
                    elif cx - r*0.3 <= x <= cx - r*0.1 and cy - r*0.5 <= y <= cy + r*0.5: is_logo = True # P vertical
                    elif (x - cx + r*0.1)**2 + (y - cy + r*0.2)**2 <= (r*0.3)**2 and x >= cx - r*0.1:
                        if (x - cx + r*0.1)**2 + (y - cy + r*0.2)**2 >= (r*0.15)**2: is_logo = True # P barriga
                    pixels_geo[x, y] = rgb2 if is_logo else rgb1
                    
                elif padrao_geometrico == "São Paulo":
                    cx, cy = largura_pontos / 2, altura_carreiras / 2
                    r = min(largura_pontos, altura_carreiras) * 0.45
                    is_logo = False
                    if cy - r <= y <= cy - r*0.3 and cx - r <= x <= cx + r: is_logo = True # Topo
                    elif cy - r*0.3 < y <= cy + r and abs(x - cx) <= (cy + r - y) * 0.8: is_logo = True # Base do escudo
                    if is_logo and cy - r*0.6 <= y <= cy - r*0.4: is_logo = False # Faixa vazada SPFC
                    pixels_geo[x, y] = rgb2 if is_logo else rgb1
                    
                elif padrao_geometrico == "Corinthians":
                    cx, cy = largura_pontos / 2, altura_carreiras / 2
                    r = min(largura_pontos, altura_carreiras) * 0.35
                    dist = math.hypot(x - cx, y - cy)
                    is_logo = False
                    if r * 0.8 <= dist <= r: is_logo = True # Anel
                    elif abs(x - cx) < r*0.15 and cy - r*1.3 <= y <= cy + r*1.3: is_logo = True # Ancora vert
                    elif abs(y - cy) < r*0.15 and cx - r*1.3 <= x <= cx + r*1.3: is_logo = True # Ancora horiz
                    if dist < r * 0.6: is_logo = True # Centro
                    if dist < r * 0.4: is_logo = False # Furo do centro
                    pixels_geo[x, y] = rgb2 if is_logo else rgb1
                    
                elif padrao_geometrico == "Santos":
                    cx, cy = largura_pontos / 2, altura_carreiras / 2
                    r = min(largura_pontos, altura_carreiras) * 0.45
                    is_logo = False
                    if cx - r <= x <= cx + r and cy - r <= y <= cy + r*0.2: is_logo = True # Corpo
                    elif (x - cx)**2 + (y - cy - r*0.2)**2 <= r**2 and y > cy + r*0.2: is_logo = True # Fundo redondo
                    if is_logo:
                        # Faixas verticais
                        if y > cy - r*0.4 and int((x - cx + r) / (r*0.35)) % 2 == 1: is_logo = False
                        # Faixa horizontal no topo
                        if cy - r*0.8 <= y <= cy - r*0.6: is_logo = False
                    pixels_geo[x, y] = rgb2 if is_logo else rgb1

    st.divider()
    st.write("### O que mostrar dentro dos quadradinhos?")
    estilo_texto = st.radio("", ["🔢 Número da Cor (Ex: 1, 2, 1...)", "📈 Sequência Total do Ponto (Ex: 1... 7000)"])

    if st.button("🎨 Gerar Tabuleiro e Iniciar Foco", type="primary"):
        if img_processada is not None:
            st.session_state.grafico_ativo = True
            st.session_state.ponto_parada = 1
        else:
            st.warning("⚠️ Forneça uma imagem ou configure um padrão primeiro.")

    # ==========================================
    # LÓGICA DO MODO FOCO, RECEITA E RENDERIZAÇÃO
    # ==========================================
    if st.session_state.grafico_ativo and img_processada is not None:
        try:
            st.image(img_processada, caption=f"Prévia ({largura_pontos}x{altura_carreiras})", width=250)
            total_pontos = int(largura_pontos * altura_carreiras)
            
            st.write("---")
            st.write("### 📍 Onde você parou?")
            st.write("Digite o número exato do ponto. O gráfico destacará onde a agulha deve ir agora.")
            
            st.session_state.ponto_parada = st.number_input(
                "Ponto de Parada Atual:", min_value=1, max_value=total_pontos, value=st.session_state.ponto_parada, step=1
            )
            st.progress(st.session_state.ponto_parada / total_pontos, text=f"Progresso: {st.session_state.ponto_parada} de {total_pontos} pontos")
            
            pixels = img_processada.load()
            cores_encontradas = {}
            contador_cores = 1
            for y in range(altura_carreiras):
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    if rgb not in cores_encontradas:
                        cores_encontradas[rgb] = contador_cores
                        contador_cores += 1

            html_grid = "<div style='display: flex; flex-direction: column; gap: 2px; overflow-x: auto; padding: 10px; background-color: #1E1E1E; border-radius: 10px;'>"
            for y in range(altura_carreiras):
                html_grid += "<div style='display: flex; gap: 1px; min-width: max-content;'>"
                num_carr = altura_carreiras - y
                dir = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                html_grid += f"<div style='width: 50px; text-align: right; font-size: 12px; margin-right: 5px; color: #888; align-self: center;'>C {num_carr} {dir}</div>"
                
                for x in range(largura_pontos):
                    ponto_na_carr = x + 1 if "Plana" in tipo_peca and num_carr % 2 == 0 else largura_pontos - x 
                    ponto_absoluto = ((num_carr - 1) * largura_pontos) + ponto_na_carr
                    
                    rgb = pixels[x, y]
                    num_cor = cores_encontradas[rgb]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                    brilho = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
                    cor_texto = "black" if brilho > 128 else "white"
                    
                    if "Sequência" in estilo_texto:
                        numero_exibicao = str(ponto_absoluto)
                        fnt_tela = "10px" if largura_pontos <= 40 else "0px"
                        if len(numero_exibicao) >= 4 and largura_pontos <= 40: fnt_tela = "8px" 
                    else:
                        numero_exibicao = str(num_cor)
                        fnt_tela = "12px" if largura_pontos <= 40 else "0px"

                    tam_tela = "25px" if largura_pontos <= 40 else "12px"
                    
                    if ponto_absoluto == st.session_state.ponto_parada:
                        estilo = f"opacity: 1; transform: scale(1.3); z-index: 50; border: 3px solid red; box-shadow: 0 0 10px red; border-radius: 4px;"
                    elif ponto_absoluto < st.session_state.ponto_parada:
                        estilo = "opacity: 0.9; border-radius: 2px;"
                    else:
                        estilo = "opacity: 0.2; border-radius: 2px;"
                        
                    html_grid += f"<div style='background-color: {hex_color}; color: {cor_texto}; width: {tam_tela}; height: {tam_tela}; display: flex; align-items: center; justify-content: center; font-size: {fnt_tela}; font-weight: bold; transition: 0.2s; {estilo}'>{numero_exibicao}</div>"
                    
                html_grid += "</div>"
            html_grid += "</div>"
            
            st.write("### Tabuleiro Interativo (Modo Foco)")
            st.markdown(html_grid, unsafe_allow_html=True)

            # ==========================================
            # NOVIDADE: A RECEITA ESCRITA (TRADUTOR)
            # ==========================================
            with st.expander("📝 Ver Receita Escrita (Passo a Passo)"):
                st.write("Siga a receita ponto a ponto. O aplicativo já contou os blocos de cores para você!")
                receita_texto_completa = "RECEITA DE CROCHÊ\n"
                receita_texto_completa += f"Tipo: {tipo_peca}\n"
                receita_texto_completa += f"Tamanho: {largura_pontos} pontos x {altura_carreiras} carreiras\n"
                receita_texto_completa += "-" * 30 + "\n\n"
                
                # Vamos ler da Carreira 1 até a última
                for y in range(altura_carreiras - 1, -1, -1):
                    num_carr = altura_carreiras - y
                    dir_seta = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                    
                    # Define a ordem de leitura (X) dependendo da direção
                    if "Plana" in tipo_peca and num_carr % 2 == 0:
                        range_x = range(largura_pontos) 
                    else:
                        range_x = range(largura_pontos - 1, -1, -1) 
                    
                    sequencia_carreira = []
                    cor_atual = None
                    contagem = 0
                    
                    for x in range_x:
                        rgb = pixels[x, y]
                        num_cor = cores_encontradas[rgb]
                        
                        if cor_atual is None:
                            cor_atual = num_cor
                            contagem = 1
                        elif cor_atual == num_cor:
                            contagem += 1
                        else:
                            sequencia_carreira.append(f"{contagem}x Cor {cor_atual}")
                            cor_atual = num_cor
                            contagem = 1
                    
                    # Salva a última cor da linha
                    if contagem > 0:
                        sequencia_carreira.append(f"{contagem}x Cor {cor_atual}")
                    
                    linha_formatada = f"**Carr {num_carr} {dir_seta}:** " + ", ".join(sequencia_carreira)
                    st.markdown(linha_formatada)
                    receita_texto_completa += f"Carr {num_carr} {dir_seta}: " + ", ".join(sequencia_carreira) + "\n"

                st.download_button("💾 Baixar Receita em Texto", data=receita_texto_completa, file_name="minha_receita.txt", mime="text/plain", type="secondary")

            # --- DOWNLOAD DA IMAGEM ESTÁTICA ---
            tamanho_quadrado = 40 
            margem = 60 
            largura_img, altura_img = (largura_pontos * tamanho_quadrado) + (margem * 2), (altura_carreiras * tamanho_quadrado) + (margem * 2)
            img_download = Image.new('RGB', (largura_img, altura_img), color='white')
            draw = ImageDraw.Draw(img_download)
            
            for y in range(altura_carreiras):
                for x in range(largura_pontos):
                    rgb = pixels[x, y]
                    x0, y0 = (x * tamanho_quadrado) + margem, (y * tamanho_quadrado) + margem
                    draw.rectangle([x0, y0, x0+tamanho_quadrado, y0+tamanho_quadrado], fill=rgb, outline="black")
                    if largura_pontos <= 100:
                        num_cor = cores_encontradas[rgb]
                        brilho = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
                        cor_texto_dl = "black" if brilho > 128 else "white"
                        if "Sequência" in estilo_texto:
                            num_carr = altura_carreiras - y
                            ponto_na_carr = x + 1 if "Plana" in tipo_peca and num_carr % 2 == 0 else largura_pontos - x
                            numero_dl = str(((num_carr - 1) * largura_pontos) + ponto_na_carr)
                        else: numero_dl = str(num_cor)
                        draw.text((x0 + 5, y0 + 10), numero_dl, fill=cor_texto_dl)

            for y_line in range(0, altura_carreiras + 1, 5):
                yp = (y_line * tamanho_quadrado) + margem
                draw.line([(margem, yp), (largura_img - margem, yp)], fill="red", width=3)
            for x_line in range(0, largura_pontos + 1, 5):
                xp = (x_line * tamanho_quadrado) + margem
                draw.line([(xp, margem), (xp, altura_img - margem)], fill="red", width=3)

            for y_num in range(altura_carreiras):
                num_carr = altura_carreiras - y_num
                dir = "<-" if "Plana" in tipo_peca and num_carr % 2 == 0 else "->"
                y_pos = (y_num * tamanho_quadrado) + margem + 12
                draw.text((10, y_pos), f"C{num_carr} {dir}", fill="black")
                draw.text((largura_img - margem + 10, y_pos), f"C{num_carr} {dir}", fill="black")

            for x_num in range(largura_pontos):
                if (x_num + 1) % 5 == 0 or x_num == 0 or x_num == largura_pontos - 1:
                    x_pos = (x_num * tamanho_quadrado) + margem + 15
                    draw.text((x_pos, margem - 25), str(x_num + 1), fill="black")
                    draw.text((x_pos, altura_img - margem + 10), str(x_num + 1), fill="black")
            
            buf = io.BytesIO()
            img_download.save(buf, format="PNG")
            st.download_button("📥 Baixar Tabuleiro (PNG)", data=buf.getvalue(), file_name="grafico_regua.png", mime="image/png", type="secondary")

        except Exception as e: st.error(f"Erro: {e}")

    st.divider()

    # ==========================================
    # INTEGRAÇÃO FINANCEIRA COM INVENTÁRIO
    # ==========================================
    st.header("💰 Parte 2: Orçamento Integrado")
    total_pontos = int(largura_pontos * altura_carreiras)
    metros_gastos = total_pontos * 0.045

    st.write("Selecione o fio que vai usar (Opcional):")
    opcoes_fios = ["Inserir Manualmente"] + list(bd["inventario"].keys())
    fio_selecionado = st.selectbox("Fio principal:", opcoes_fios)

    col_calc1, col_calc2 = st.columns(2)
    with col_calc1:
        if fio_selecionado == "Inserir Manualmente":
            preco_novelo = st.number_input("Preço do Novelo (R$)", min_value=0.0, value=18.0)
            metros_novelo = st.number_input("Metros no Novelo (m)", min_value=1.0, value=150.0)
        else:
            preco_novelo = bd["inventario"][fio_selecionado]["preco"]
            metros_novelo = bd["inventario"][fio_selecionado]["metros_total"]
            st.info(f"Fio associado: Custa R$ {preco_novelo:.2f} por {metros_novelo}m. (Restam {bd['inventario'][fio_selecionado]['metros_restantes']:.2f}m)")
            
    with col_calc2:
        valor_hora = st.number_input("Sua Hora de Trabalho (R$/h)", min_value=0.0, value=25.0, step=1.0)
        margem_lucro = st.number_input("Margem de Lucro (%)", min_value=0.0, value=30.0, step=5.0)

    custo_material = metros_gastos * (preco_novelo / metros_novelo)
    minutos_totais = total_pontos / 20
    horas_totais = minutos_totais / 60
    custo_tempo = horas_totais * valor_hora
    taxa_desgaste = 1.50 
    custo_producao = custo_material + custo_tempo + taxa_desgaste
    valor_lucro = custo_producao * (margem_lucro / 100)
    preco_final = custo_producao + valor_lucro

    st.write("### 🧾 Relatório Financeiro")
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Tempo", f"{int(horas_totais)}h {int(minutos_totais % 60)}m")
    col_res2.metric("Material", f"R$ {custo_material:.2f}")
    col_res3.metric("Mão de Obra", f"R$ {custo_tempo:.2f}")
    st.success(f"### Preço de Venda Sugerido: R$ {preco_final:.2f}")

    if fio_selecionado != "Inserir Manualmente":
        if st.button("✅ Confirmar Produção e Gerar Orçamento", type="primary"):
            if bd["inventario"][fio_selecionado]["metros_restantes"] >= metros_gastos:
                bd["inventario"][fio_selecionado]["metros_restantes"] -= metros_gastos
                bd["lucro_acumulado"] += valor_lucro
                bd["pecas_produzidas"] += 1
                
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                novo_registro = {
                    "Data": data_atual, "Fio Usado": fio_selecionado, "Total de Pontos": total_pontos,
                    "Metros Gastos": round(metros_gastos, 2), "Custo de Producao (R$)": round(custo_producao, 2),
                    "Lucro (R$)": round(valor_lucro, 2), "Preco de Venda (R$)": round(preco_final, 2)
                }
                bd["historico_vendas"].append(novo_registro)
                guardar_bd(bd)
                st.success(f"Orçamento arquivado! Foram descontados {metros_gastos:.2f}m do estoque de '{fio_selecionado}'.")
            else:
                st.error("⚠️ Atenção: Você não tem metros suficientes no estoque para produzir esta peça!")

# ==========================================
# SEPARADOR 2: GESTÃO E RELATÓRIOS
# ==========================================
with tab_gestao:
    st.header("📦 Gestão de Estoque e Finanças")
    st.write("### 📈 Balanço Geral")
    col_ind1, col_ind2 = st.columns(2)
    col_ind1.metric("Lucro Acumulado", f"R$ {bd['lucro_acumulado']:.2f}")
    col_ind2.metric("Orçamentos Confirmados", f"{bd['pecas_produzidas']} peças")
    
    if len(bd["historico_vendas"]) > 0:
        csv_buffer = io.StringIO()
        cabecalhos = ["Data", "Fio Usado", "Total de Pontos", "Metros Gastos", "Custo de Producao (R$)", "Lucro (R$)", "Preco de Venda (R$)"]
        writer = csv.DictWriter(csv_buffer, fieldnames=cabecalhos, delimiter=';')
        writer.writeheader()
        writer.writerows(bd["historico_vendas"])
        st.download_button("📉 Baixar Relatório Completo (Planilha CSV)", data=csv_buffer.getvalue(), file_name="relatorio_orcamentos_croche.csv", mime="text/csv", type="primary")

    st.divider()
    st.write("### ➕ Registrar Novo Fio no Estoque")
    with st.form("form_inventario", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: nome_fio = st.text_input("Nome/Cor do Fio")
        with col_f2: preco_fio = st.number_input("Preço (R$)", min_value=0.01, step=0.50)
        with col_f3: metros_fio = st.number_input("Metragem (m)", min_value=1.0, step=10.0)
        if st.form_submit_button("Guardar no Inventário"):
            if nome_fio:
                bd["inventario"][nome_fio] = {"preco": preco_fio, "metros_total": metros_fio, "metros_restantes": metros_fio}
                guardar_bd(bd)
                st.success(f"Fio '{nome_fio}' registrado com sucesso no estoque!")
                st.rerun() 
            else: st.error("O nome do fio é obrigatório.")

    st.write("### 📋 Seu Estoque Atual")
    if len(bd["inventario"]) > 0:
        for nome, dados in bd["inventario"].items():
            percentagem = (dados["metros_restantes"] / dados["metros_total"]) * 100
            st.write(f"**{nome}** (Custo original: R$ {dados['preco']:.2f})")
            st.progress(int(percentagem), text=f"Restam {dados['metros_restantes']:.2f}m de {dados['metros_total']}m")
            if percentagem <= 20: st.warning(f"⚠️ Atenção: O estoque do fio '{nome}' está no fim!")
            st.write("---")
    else: st.info("Seu inventário está vazio. Registre sua primeira compra acima.")

