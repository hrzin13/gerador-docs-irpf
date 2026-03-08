import streamlit as st
from PIL import Image, ImageDraw, ImageColor
import io
import json
import os

# ==========================================
# MOTOR DE BASE DE DADOS (JSON)
# ==========================================
FICHEIRO_BD = "contabilidade_croche.json"

def carregar_bd():
    if not os.path.exists(FICHEIRO_BD):
        # Cria a estrutura inicial do balanço
        return {"inventario": {}, "lucro_acumulado": 0.0, "pecas_produzidas": 0}
    with open(FICHEIRO_BD, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_bd(dados):
    with open(FICHEIRO_BD, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4)

bd = carregar_bd()

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Estúdio de Crochê Pro", layout="centered")

st.title("🧶 Estúdio de Crochê Pro")
st.write("Gere gráficos, controle o inventário e apure os lucros num só lugar.")

# Criação dos Separadores (Tabs)
tab_gerador, tab_gestao = st.tabs(["🎨 Gerador de Gráfico", "📊 Gestão e Inventário"])

# ==========================================
# SEPARADOR 1: GERADOR DE GRÁFICO (O TEU CÓDIGO INTACTO)
# ==========================================
with tab_gerador:
    st.header("1️⃣ Parte 1: Gerador de Gráfico")

    tipo_peca = st.radio("Como vais tecer esta peça?", 
                         ["Circular (Tubo - Ex: Porta Isqueiro, Touca)", 
                          "Plana (Ida e Volta - Ex: Tapete, Blusa)"])

    st.write("### Como desejas criar o desenho?")
    modo_entrada = st.radio("", ["📸 Subir Imagem do Telemóvel", "📐 Gerar Padrão Geométrico (Automático)"])

    # Variáveis globais
    largura_pontos = 20
    altura_carreiras = 20
    img_processada = None

    if modo_entrada == "📸 Subir Imagem do Telemóvel":
        imagem_carregada = st.file_uploader("Anexa o teu desenho aqui (png, jpg)", type=["png", "jpg", "jpeg"])
        
        if imagem_carregada is not None:
            img_temp = Image.open(imagem_carregada).convert('RGB')
            largura_original, altura_original = img_temp.size
            proporcao = altura_original / largura_original 
            
            st.info(f"📐 Resolução original da imagem: {largura_original}x{altura_original}.")
            
            opcao_tamanho = st.radio(
                "Escolhe o Nível de Detalhe (Resolução):",
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
            
            num_cores = st.slider("Quantas cores de fio vais usar?", min_value=2, max_value=20, value=3)
            
            img_processada = img_temp.quantize(colors=num_cores).convert('RGB')
            img_processada = img_processada.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)

    else:
        st.write("#### Configura o teu Padrão Geométrico")
        padrao_geometrico = st.selectbox("Seleciona o desenho:", [
            "Xadrez 2x2 (Blocos)", "Xadrez 1x1 (Fino)", "Listras Horizontais", 
            "Listras Verticais", "Diagonal (Escada)", "Tijolos",
            "Ziguezague (Chevron)", "Bolinhas (Poá)", "Cruz Central (Única)",
            "Moldura / Borda", "Losangos"
        ])
        
        col_tam1, col_tam2 = st.columns(2)
        with col_tam1: largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=20)
        with col_tam2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=20)
        
        st.write("Escolhe as 2 cores do teu padrão:")
        col_cor1, col_cor2 = st.columns(2)
        with col_cor1: cor1_hex = st.color_picker("Cor 1 (Fundo)", "#4A4A4A")
        with col_cor2: cor2_hex = st.color_picker("Cor 2 (Desenho)", "#FFD700")
        
        img_processada = Image.new('RGB', (largura_pontos, altura_carreiras))
        pixels_geo = img_processada.load()
        rgb1 = ImageColor.getrgb(cor1_hex)
        rgb2 = ImageColor.getrgb(cor2_hex)
        
        for y in range(altura_carreiras):
            for x in range(largura_pontos):
                if padrao_geometrico == "Xadrez 2x2 (Blocos)":
                    pixels_geo[x, y] = rgb1 if (x // 2 + y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Xadrez 1x1 (Fino)":
                    pixels_geo[x, y] = rgb1 if (x + y) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Horizontais":
                    pixels_geo[x, y] = rgb1 if (y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Verticais":
                    pixels_geo[x, y] = rgb1 if (x // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Diagonal (Escada)":
                    pixels_geo[x, y] = rgb1 if (x + y) % 3 == 0 else rgb2
                elif padrao_geometrico == "Tijolos":
                    pixels_geo[x, y] = rgb1 if (x + (y // 2) * 3) % 6 < 3 else rgb2
                elif padrao_geometrico == "Ziguezague (Chevron)":
                    pixels_geo[x, y] = rgb2 if (x + y) % 4 == 0 or (x - y) % 4 == 0 else rgb1
                elif padrao_geometrico == "Bolinhas (Poá)":
                    pixels_geo[x, y] = rgb2 if x % 4 == 0 and y % 4 == 0 else rgb1
                elif padrao_geometrico == "Cruz Central (Única)":
                    pixels_geo[x, y] = rgb2 if x == largura_pontos // 2 or y == altura_carreiras // 2 else rgb1
                elif padrao_geometrico == "Moldura / Borda":
                    pixels_geo[x, y] = rgb2 if x < 2 or x > largura_pontos - 3 or y < 2 or y > altura_carreiras - 3 else rgb1
                elif padrao_geometrico == "Losangos":
                    pixels_geo[x, y] = rgb2 if (abs(x % 10 - 5) + abs(y % 10 - 5)) < 4 else rgb1

    st.divider()
    st.write("### O que mostrar dentro dos quadradinhos?")
    estilo_texto = st.radio("", ["🔢 Número da Cor (Ex: 1, 2, 1...)", "📈 Sequência Total do Ponto (Ex: 1... 7000)"])

    if st.button("🎨 Gerar Tabuleiro e Baixar", type="primary"):
        if img_processada is not None:
            try:
                st.image(img_processada, caption=f"Prévia ({largura_pontos}x{altura_carreiras})", width=250)
                
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
                margem = 60 
                largura_img = (largura_pontos * tamanho_quadrado) + (margem * 2)
                altura_img = (altura_carreiras * tamanho_quadrado) + (margem * 2)
                
                img_download = Image.new('RGB', (largura_img, altura_img), color='white')
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
                        
                        if "Sequência" in estilo_texto:
                            ponto_na_carr = x + 1 if "Plana" in tipo_peca and num_carr % 2 == 0 else largura_pontos - x 
                            numero_exibicao = str(((num_carr - 1) * largura_pontos) + ponto_na_carr)
                            fnt_tela = "10px" if largura_pontos <= 40 else "0px"
                            if len(numero_exibicao) >= 4 and largura_pontos <= 40: fnt_tela = "8px" 
                        else:
                            numero_exibicao = str(num_cor)
                            fnt_tela = "12px" if largura_pontos <= 40 else "0px"

                        tam_tela = "25px" if largura_pontos <= 40 else "12px"
                        html_grid += f"<div style='background-color: {hex_color}; color: {cor_texto}; width: {tam_tela}; height: {tam_tela}; display: flex; align-items: center; justify-content: center; font-size: {fnt_tela}; font-weight: bold; border-radius: 2px;'>{numero_exibicao}</div>"
                        
                        x0, y0 = (x * tamanho_quadrado) + margem, (y * tamanho_quadrado) + margem
                        draw.rectangle([x0, y0, x0+tamanho_quadrado, y0+tamanho_quadrado], fill=rgb, outline="black")
                        if largura_pontos <= 100: draw.text((x0 + 5, y0 + 10), numero_exibicao, fill=cor_texto)

                    html_grid += "</div>"
                html_grid += "</div>"
                
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
                
                st.write("### Visualização Rápida")
                st.markdown(html_grid, unsafe_allow_html=True)
            except Exception as e: st.error(f"Erro: {e}")
        else:
            st.warning("⚠️ Fornece uma imagem ou configura um padrão primeiro.")

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
        valor_hora = st.number_input("Tua Hora de Trabalho (R$/h)", min_value=0.0, value=25.0, step=1.0)
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
    st.success(f"### Preço de Venda: R$ {preco_final:.2f}")

    # BOTÃO PARA REGISTAR A SAÍDA NO INVENTÁRIO
    if fio_selecionado != "Inserir Manualmente":
        if st.button("✅ Confirmar Produção e Atualizar Inventário", type="primary"):
            if bd["inventario"][fio_selecionado]["metros_restantes"] >= metros_gastos:
                bd["inventario"][fio_selecionado]["metros_restantes"] -= metros_gastos
                bd["lucro_acumulado"] += valor_lucro
                bd["pecas_produzidas"] += 1
                guardar_bd(bd)
                st.success(f"Registo feito! Foram descontados {metros_gastos:.2f}m do stock de '{fio_selecionado}'. Lucro de R$ {valor_lucro:.2f} apurado no sistema.")
            else:
                st.error("⚠️ Atenção: Não tens metros suficientes no stock para produzir esta peça!")

# ==========================================
# SEPARADOR 2: GESTÃO DE INVENTÁRIO (O NOVO ERP)
# ==========================================
with tab_gestao:
    st.header("📦 Gestão de Stock e Finanças")
    
    # 1. Painel de Indicadores de Gestão
    st.write("### 📈 Balanço Geral")
    col_ind1, col_ind2 = st.columns(2)
    col_ind1.metric("Lucro Acumulado Projetado", f"R$ {bd['lucro_acumulado']:.2f}")
    col_ind2.metric("Peças Produzidas", f"{bd['pecas_produzidas']} peças")
    
    st.divider()

    # 2. Registar Novo Ativo (Fio)
    st.write("### ➕ Registar Novo Fio de Crochê")
    with st.form("form_inventario", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: nome_fio = st.text_input("Nome/Cor do Fio (Ex: Amarelo Círculo)")
        with col_f2: preco_fio = st.number_input("Preço de Compra (R$)", min_value=0.01, step=0.50)
        with col_f3: metros_fio = st.number_input("Metragem Total (m)", min_value=1.0, step=10.0)
        
        if st.form_submit_button("Guardar no Inventário"):
            if nome_fio:
                bd["inventario"][nome_fio] = {
                    "preco": preco_fio,
                    "metros_total": metros_fio,
                    "metros_restantes": metros_fio
                }
                guardar_bd(bd)
                st.success(f"Ativo '{nome_fio}' registado com sucesso no livro razão!")
                st.rerun() # Atualiza o ecrã instantaneamente
            else:
                st.error("O nome do fio é obrigatório.")

    # 3. Visualizar Inventário Atual
    st.write("### 📋 O teu Inventário Atual")
    if len(bd["inventario"]) > 0:
        for nome, dados in bd["inventario"].items():
            percentagem = (dados["metros_restantes"] / dados["metros_total"]) * 100
            cor_barra = "green" if percentagem > 20 else "red"
            
            st.write(f"**{nome}** (Custo original: R$ {dados['preco']:.2f})")
            st.progress(int(percentagem), text=f"Restam {dados['metros_restantes']:.2f}m de {dados['metros_total']}m")
            if percentagem <= 20:
                st.warning(f"⚠️ Atenção: O stock do fio '{nome}' está a acabar!")
            st.write("---")
    else:
        st.info("O teu inventário está vazio. Regista a tua primeira compra acima.")
