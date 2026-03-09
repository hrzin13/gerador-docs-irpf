import streamlit as st
from PIL import Image, ImageDraw, ImageColor
import io
import json
import os
import csv
from datetime import datetime
import math # Importante para a matemática dos novos padrões!

# ==========================================
# INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA (SESSÃO)
# ==========================================
# Isso garante que o app lembre o número que você digitou
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

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Estúdio de Crochê Pro", layout="centered")

st.title("🧶 Estúdio de Crochê Pro")
st.write("Gere gráficos, controle o inventário e exporte os seus relatórios financeiros.")

# Criação dos Separadores (Tabs)
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
            
            opcao_tamanho = st.radio(
                "Escolha o Nível de Detalhe:",
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
            
            img_processada = img_temp.quantize(colors=num_cores).convert('RGB')
            img_processada = img_processada.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)

    else:
        st.write("#### Configure seu Padrão Gerado")
        
        categoria_padrao = st.selectbox("📁 Escolha a Categoria:", ["Geométricos Clássicos", "Símbolos e Arte"])
        
        if categoria_padrao == "Geométricos Clássicos":
            lista_padroes = [
                "Xadrez 2x2 (Bloquinhos)", "Xadrez 1x1 (Xadrezinho fino)", "Listras Horizontais", 
                "Listras Verticais", "Diagonal (Escadinha)", "Tijolinhos",
                "Ziguezague (Chevron)", "Bolinhas (Poá)", "Cruz Central (Única)",
                "Moldura / Borda", "Losangos"
            ]
        else:
            lista_padroes = ["Folha (Arte Botânica)", "Coração (Pixel Art)"]
            
        padrao_geometrico = st.selectbox("✨ Selecione o desenho:", lista_padroes)
        
        col_tam1, col_tam2 = st.columns(2)
        with col_tam1: largura_pontos = st.number_input("Largura (Pontos)", min_value=10, value=30) 
        with col_tam2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=10, value=30)
        
        st.write("Escolha as 2 cores do seu padrão:")
        col_cor1, col_cor2 = st.columns(2)
        with col_cor1: cor1_hex = st.color_picker("Cor 1 (Fundo)", "#2C2C2C")
        with col_cor2: cor2_hex = st.color_picker("Cor 2 (Desenho)", "#00FF00" if padrao_geometrico == "Folha (Arte Botânica)" else "#FFD700")
        
        img_processada = Image.new('RGB', (largura_pontos, altura_carreiras))
        pixels_geo = img_processada.load()
        rgb1 = ImageColor.getrgb(cor1_hex)
        rgb2 = ImageColor.getrgb(cor2_hex)
        
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
                    cx = largura_pontos / 2
                    cy = altura_carreiras * 0.75 
                    dx = x - cx
                    dy = cy - y 
                    dist = math.hypot(dx, dy)
                    angle = math.atan2(dy, dx) if dx != 0 or dy != 0 else 0
                    
                    if -1 <= dx <= 1 and cy <= y <= cy + (altura_carreiras * 0.2):
                        pixels_geo[x, y] = rgb2
                    elif 0 <= angle <= math.pi:
                        tamanho_max = (altura_carreiras * 0.6) * (1 - 0.3 * abs(math.cos(angle)))
                        limite_raio = tamanho_max * abs(math.sin(7 * angle))
                        if dist <= limite_raio:
                            pixels_geo[x, y] = rgb2
                        else:
                            pixels_geo[x, y] = rgb1
                    else:
                        pixels_geo[x, y] = rgb1
                        
                elif padrao_geometrico == "Coração (Pixel Art)":
                    cx = largura_pontos / 2
                    cy = altura_carreiras / 2
                    escala = min(largura_pontos, altura_carreiras) / 2.5
                    vx = (x - cx) / escala
                    vy = (cy - y) / (escala * 1.1)
                    if (vx**2 + vy**2 - 1)**3 - (vx**2) * (vy**3) <= 0:
                        pixels_geo[x, y] = rgb2
                    else:
                        pixels_geo[x, y] = rgb1

    st.divider()
    st.write("### O que mostrar dentro dos quadradinhos?")
    estilo_texto = st.radio("", ["🔢 Número da Cor (Ex: 1, 2, 1...)", "📈 Sequência Total do Ponto (Ex: 1... 7000)"])

    # NOVO BOTÃO: Ativa a memória da sessão para liberar o gráfico interativo
    if st.button("🎨 Gerar Tabuleiro e Iniciar Foco", type="primary"):
        if img_processada is not None:
            st.session_state.grafico_ativo = True
            st.session_state.ponto_parada = 1
        else:
            st.warning("⚠️ Forneça uma imagem ou configure um padrão primeiro.")

    # ==========================================
    # LÓGICA DO MODO FOCO E RENDERIZAÇÃO
    # ==========================================
    if st.session_state.grafico_ativo and img_processada is not None:
        try:
            st.image(img_processada, caption=f"Prévia ({largura_pontos}x{altura_carreiras})", width=250)
            
            total_pontos = int(largura_pontos * altura_carreiras)
            
            # --- CAIXA DE DIGITAÇÃO DO PONTO EXATO ---
            st.write("---")
            st.write("### 📍 Onde você parou?")
            st.write("Digite o número exato do ponto. O gráfico apagará os pontos futuros e destacará onde a agulha deve ir agora.")
            
            st.session_state.ponto_parada = st.number_input(
                "Ponto de Parada Atual:", 
                min_value=1, 
                max_value=total_pontos, 
                value=st.session_state.ponto_parada,
                step=1
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

            # --- RENDERIZAÇÃO DO TABULEIRO INTERATIVO NA TELA ---
            html_grid = "<div style='display: flex; flex-direction: column; gap: 2px; overflow-x: auto; padding: 10px; background-color: #1E1E1E; border-radius: 10px;'>"
            for y in range(altura_carreiras):
                html_grid += "<div style='display: flex; gap: 1px; min-width: max-content;'>"
                num_carr = altura_carreiras - y
                dir = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                html_grid += f"<div style='width: 50px; text-align: right; font-size: 12px; margin-right: 5px; color: #888; align-self: center;'>C {num_carr} {dir}</div>"
                
                for x in range(largura_pontos):
                    # Calcula o número absoluto do ponto na peça toda
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
                    
                    # O SEGREDO DO MODO FOCO: Cores normais antes, Vermelho no exato momento, Transparente depois
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
            
            # --- RENDERIZAÇÃO DA IMAGEM ESTÁTICA PARA DOWNLOAD ---
            tamanho_quadrado = 40 
            margem = 60 
            largura_img = (largura_pontos * tamanho_quadrado) + (margem * 2)
            altura_img = (altura_carreiras * tamanho_quadrado) + (margem * 2)
            
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
                        else:
                            numero_dl = str(num_cor)
                            
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
                    "Data": data_atual,
                    "Fio Usado": fio_selecionado,
                    "Total de Pontos": total_pontos,
                    "Metros Gastos": round(metros_gastos, 2),
                    "Custo de Producao (R$)": round(custo_producao, 2),
                    "Lucro (R$)": round(valor_lucro, 2),
                    "Preco de Venda (R$)": round(preco_final, 2)
                }
                bd["historico_vendas"].append(novo_registro)
                
                guardar_bd(bd)
                st.success(f"Orçamento arquivado! Foram descontados {metros_gastos:.2f}m do estoque de '{fio_selecionado}'. Lucro de R$ {valor_lucro:.2f} apurado no sistema.")
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
        
        st.download_button(
            label="📉 Baixar Relatório Completo (Planilha CSV)", 
            data=csv_buffer.getvalue(), 
            file_name="relatorio_orcamentos_croche.csv", 
            mime="text/csv",
            type="primary"
        )
        st.caption("*O arquivo baixado pode ser aberto diretamente no Excel ou importado para o Google Sheets.*")

    st.divider()

    st.write("### ➕ Registrar Novo Fio no Estoque")
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
                st.success(f"Fio '{nome_fio}' registrado com sucesso no estoque!")
                st.rerun() 
            else:
                st.error("O nome do fio é obrigatório.")

    st.write("### 📋 Seu Estoque Atual")
    if len(bd["inventario"]) > 0:
        for nome, dados in bd["inventario"].items():
            percentagem = (dados["metros_restantes"] / dados["metros_total"]) * 100
            
            st.write(f"**{nome}** (Custo original: R$ {dados['preco']:.2f})")
            st.progress(int(percentagem), text=f"Restam {dados['metros_restantes']:.2f}m de {dados['metros_total']}m")
            if percentagem <= 20:
                st.warning(f"⚠️ Atenção: O estoque do fio '{nome}' está no fim!")
            st.write("---")
    else:
        st.info("Seu inventário está vazio. Registre sua primeira compra acima.")

