import streamlit as st
from PIL import Image, ImageDraw, ImageColor, ImageFont
import io
import json
import os
import csv
from datetime import datetime
import math 

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BLINDAGEM DO CELULAR
# ==========================================
st.set_page_config(page_title="Estúdio de Crochê Pro", layout="wide")

st.markdown("""
<style>
    /* BLOQUEAR O PULL-TO-REFRESH NO CELULAR */
    html, body, .stApp {
        overscroll-behavior-y: contain; 
        overflow-y: auto;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

if 'ponto_parada' not in st.session_state: st.session_state.ponto_parada = 1
if 'grafico_ativo' not in st.session_state: st.session_state.grafico_ativo = False

# ==========================================
# MOTOR DE BASE DE DADOS (JSON) COM HISTÓRICO
# ==========================================
FICHEIRO_BD = "contabilidade_croche.json"

def carregar_bd():
    if not os.path.exists(FICHEIRO_BD): 
        return {"inventario": {}, "lucro_acumulado": 0.0, "pecas_produzidas": 0, "historico_vendas": []}
    with open(FICHEIRO_BD, "r", encoding="utf-8") as f:
        dados = json.load(f)
        if "historico_vendas" not in dados: dados["historico_vendas"] = []
        return dados

def guardar_bd(dados):
    with open(FICHEIRO_BD, "w", encoding="utf-8") as f: 
        json.dump(dados, f, indent=4)

bd = carregar_bd()

st.title("🧶 Estúdio de Crochê Pro - Motor Avançado")

tab_gerador, tab_gestao = st.tabs(["🎨 Gerador de Gráfico", "📊 Gestão, Inventário e Relatórios"])

# ==========================================
# SEPARADOR 1: GERADOR DE GRÁFICO
# ==========================================
with tab_gerador:
    st.header("1️⃣ Configuração da Peça")

    col_peca1, col_peca2 = st.columns(2)
    with col_peca1:
        tipo_peca = st.radio("Como você vai tecer essa peça?", 
                             ["Circular (Tubo - Ex: Gorro, Amigurumi)", 
                              "Plana (Ida e Volta - Ex: Tapete)",
                              "Circular Plana (Centro p/ Bordas - Ex: Porta-copo) 🚀"])
        is_radial = "Centro" in tipo_peca
    
    with col_peca2:
        tipo_ponto_base = st.selectbox("Qual o ponto base da peça?", [
            "Ponto Baixo (PB)", 
            "Ponto Alto (PA)", 
            "Meio Ponto Alto (MPA)", 
            "Ponto Baixíssimo (PBX)", 
            "Apenas Cores"
        ])

    st.write("### Como deseja criar o desenho?")
    # NOVIDADE AQUI: A OPÇÃO DE ESCREVER NOME!
    modo_entrada = st.radio("", ["📸 Subir Imagem / Buscar", "🔤 Escrever Nome (Letreiro)", "📐 Gerar Padrão (Formas Perfeitas)"])

    largura_pontos = 20
    altura_carreiras = 20
    num_carreiras_radial = 15
    pontos_anel_magico = 6
    img_base = None

    if is_radial:
        st.warning("⚠️ **Modo Radial Ativado:** A matemática aqui é pesada. Ele mapeia do centro para fora!")
        col_rad1, col_rad2 = st.columns(2)
        with col_rad1: num_carreiras_radial = st.number_input("Número Total de Carreiras (Raio)", min_value=3, max_value=60, value=15)
        with col_rad2: pontos_anel_magico = st.number_input("Pontos no Anel Mágico (Aumentos por Carr)", min_value=4, max_value=12, value=6)
        largura_pontos = 200
        altura_carreiras = 200

    if modo_entrada == "📸 Subir Imagem / Buscar":
        st.write("### 🔍 Busca Inteligente")
        termo_busca = st.text_input("Ex: Escudo do Palmeiras, Super Mario")
        if termo_busca:
            termo_otimizado = f"{termo_busca} pixel art OR ponto cruz OR perler beads"
            link_google = f"https://www.google.com/search?tbm=isch&q={termo_otimizado.replace(' ', '+')}"
            link_pinterest = f"https://br.pinterest.com/search/pins/?q={termo_otimizado.replace(' ', '%20')}"
            st.markdown(f"<div style='display:flex;gap:10px;'><a href='{link_google}' target='_blank' style='background:#4285F4;color:white;padding:10px;border-radius:5px;text-decoration:none;width:100%;text-align:center;'>🔍 Google Imagens</a><a href='{link_pinterest}' target='_blank' style='background:#E60023;color:white;padding:10px;border-radius:5px;text-decoration:none;width:100%;text-align:center;'>📌 Pinterest</a></div>", unsafe_allow_html=True)

        imagem_carregada = st.file_uploader("📥 Anexe a imagem aqui", type=["png", "jpg", "jpeg"])
        if imagem_carregada is not None:
            img_temp = Image.open(imagem_carregada).convert('RGB')
            if not is_radial:
                largura_original, altura_original = img_temp.size
                proporcao = altura_original / largura_original 
                col1, col2 = st.columns(2)
                with col1: largura_pontos = st.number_input("Largura (Pontos)", min_value=5, value=30)
                with col2: altura_carreiras = st.number_input("Altura (Carreiras)", min_value=5, value=max(5, int(largura_pontos * proporcao)))
            else:
                img_temp = img_temp.resize((200, 200), Image.Resampling.LANCZOS)
                
            num_cores = st.slider("Quantas cores usar?", min_value=2, max_value=20, value=4)
            img_base = img_temp.quantize(colors=num_cores).convert('RGB')
            if not is_radial:
                img_base = img_base.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)

    # --- NOVO MOTOR DE LETREIROS / NOMES ---
    elif modo_entrada == "🔤 Escrever Nome (Letreiro)":
        st.write("### 🔤 Gerador de Nomes em Pixel Art")
        st.info("Digite um nome. O aplicativo criará o gráfico perfeitamente alinhado para os seus pontos de crochê!")
        
        texto_usuario = st.text_input("Digite o nome ou palavra:", "PABLO").upper()
        escala_texto = st.slider("Espessura / Tamanho da Letra", min_value=1, max_value=5, value=2)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1: cor_fundo_txt = st.color_picker("Cor do Fundo", "#2C2C2C")
        with col_c2: cor_letra_txt = st.color_picker("Cor da Letra", "#F59E0B")
        
        if texto_usuario:
            # A fonte bitmap padrão do Python tem aprox 6x11 pixels por letra
            largura_base = (len(texto_usuario) * 6) + 4
            altura_base = 13
            
            # Cria a imagem pequenininha baseada nos pixels
            img_txt = Image.new('RGB', (largura_base, altura_base), color=cor_fundo_txt)
            draw_txt = ImageDraw.Draw(img_txt)
            draw_txt.text((2, 1), texto_usuario, fill=cor_letra_txt)
            
            # Amplia a imagem mantendo os quadrados perfeitos (Sem embaçar)
            largura_pontos = largura_base * escala_texto
            altura_carreiras = altura_base * escala_texto
            
            img_base = img_txt.resize((largura_pontos, altura_carreiras), Image.Resampling.NEAREST)
            st.success(f"**Tamanho ideal gerado automaticamente:** {largura_pontos} pontos x {altura_carreiras} carreiras.")

    # --- FORMAS MATEMÁTICAS PERFEITAS (LIMPO E EFICIENTE) ---
    else:
        st.write("### 📐 Padrões Geométricos Perfeitos")
        st.write("Estas formas foram desenhadas na matemática exata para nunca ficarem tortas na sua agulha.")
        
        padrao_geometrico = st.selectbox("✨ Selecione o desenho:", [
            "Xadrez 2x2 (Bloquinhos)", 
            "Xadrez 1x1 (Fino)", 
            "Listras Horizontais", 
            "Listras Verticais", 
            "Diagonal (Escadinha)", 
            "Ziguezague (Chevron)", 
            "Moldura / Borda", 
            "Coração (Pixel Art Perfeito)"
        ])
        
        if not is_radial:
            col_tam1, col_tam2 = st.columns(2)
            with col_tam1: largura_pontos = st.number_input("Largura (Pts)", min_value=10, value=30) 
            with col_tam2: altura_carreiras = st.number_input("Altura (Carr)", min_value=10, value=30)
            
        cor_f1 = "#2C2C2C"
        cor_d1 = "#FF0000" if "Coração" in padrao_geometrico else "#FFD700"
        
        col_c1, col_c2 = st.columns(2)
        with col_c1: cor1_hex = st.color_picker("Cor 1 (Fundo)", cor_f1)
        with col_c2: cor2_hex = st.color_picker("Cor 2 (Desenho)", cor_d1)
        
        img_base = Image.new('RGB', (largura_pontos, altura_carreiras))
        px = img_base.load()
        rgb1, rgb2 = ImageColor.getrgb(cor1_hex), ImageColor.getrgb(cor2_hex)
        
        for y in range(altura_carreiras):
            for x in range(largura_pontos):
                cx, cy = largura_pontos / 2, altura_carreiras / 2
                
                if padrao_geometrico == "Xadrez 2x2 (Bloquinhos)": px[x, y] = rgb1 if (x // 2 + y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Xadrez 1x1 (Fino)": px[x, y] = rgb1 if (x + y) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Horizontais": px[x, y] = rgb1 if (y // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Listras Verticais": px[x, y] = rgb1 if (x // 2) % 2 == 0 else rgb2
                elif padrao_geometrico == "Diagonal (Escadinha)": px[x, y] = rgb1 if (x + y) % 3 == 0 else rgb2
                elif padrao_geometrico == "Ziguezague (Chevron)": px[x, y] = rgb2 if (x + y) % 4 == 0 or (x - y) % 4 == 0 else rgb1
                elif padrao_geometrico == "Moldura / Borda": px[x, y] = rgb2 if x < 2 or x > largura_pontos - 3 or y < 2 or y > altura_carreiras - 3 else rgb1
                elif padrao_geometrico == "Coração (Pixel Art Perfeito)":
                    escala = min(largura_pontos, altura_carreiras) / 2.5
                    vx, vy = (x - cx) / escala, (cy - y) / (escala * 1.1)
                    px[x, y] = rgb2 if (vx**2 + vy**2 - 1)**3 - (vx**2) * (vy**3) <= 0 else rgb1

    # --- O MOTOR RADIAL DE COORDENADAS POLARES ---
    radial_map = {}
    if is_radial and img_base is not None:
        total_pontos = 0
        img_preview = Image.new('RGB', (400, 400), '#1E293B')
        draw_prev = ImageDraw.Draw(img_preview)
        
        for r_idx in range(1, num_carreiras_radial + 1):
            n_pontos = r_idx * pontos_anel_magico
            radial_map[r_idx] = []
            total_pontos += n_pontos
            for s in range(n_pontos):
                theta = (s / n_pontos) * 2 * math.pi - (math.pi / 2)
                dist_pct = r_idx / num_carreiras_radial
                x = int(100 + (dist_pct * 100) * math.cos(theta))
                y = int(100 + (dist_pct * 100) * math.sin(theta))
                x, y = max(0, min(199, x)), max(0, min(199, y))
                radial_map[r_idx].append(img_base.getpixel((x, y)))

        for r_idx in range(num_carreiras_radial, 0, -1):
            n_pontos = r_idx * pontos_anel_magico
            r_out = (r_idx / num_carreiras_radial) * 190
            for s in range(n_pontos):
                a1 = (s / n_pontos) * 360 - 90
                a2 = ((s+1) / n_pontos) * 360 - 90
                draw_prev.pieslice([200-r_out, 200-r_out, 200+r_out, 200+r_out], a1, a2, fill=radial_map[r_idx][s], outline="#333333")
                
        img_processada = img_preview
    else:
        img_processada = img_base
        total_pontos = int(largura_pontos * altura_carreiras) if img_base else 0

    st.divider()
    estilo_texto = st.radio("", ["🔢 Número da Cor", "📈 Sequência Total do Ponto"])

    if st.button("🚀 GERAR MOTOR MATEMÁTICO E FOCO", type="primary", use_container_width=True):
        if img_base is not None:
            st.session_state.grafico_ativo = True
            st.session_state.ponto_parada = 1
        else: st.warning("Configure o padrão primeiro.")

    if st.session_state.grafico_ativo and img_base is not None:
        try:
            st.write("---")
            st.image(img_processada, caption=f"Visão Final ({total_pontos} pontos calculados)", width=350)
            
            st.write("### 📍 Onde você parou?")
            st.session_state.ponto_parada = st.number_input("Ponto de Parada Atual:", min_value=1, max_value=total_pontos, value=st.session_state.ponto_parada, step=1)
            st.progress(st.session_state.ponto_parada / total_pontos)
            
            cores_encontradas = {}
            contador_cores = 1
            if is_radial:
                for r_idx in range(1, num_carreiras_radial + 1):
                    for rgb in radial_map[r_idx]:
                        if rgb not in cores_encontradas:
                            cores_encontradas[rgb] = contador_cores; contador_cores += 1
            else:
                pixels = img_base.load()
                for y in range(altura_carreiras):
                    for x in range(largura_pontos):
                        rgb = pixels[x, y]
                        if rgb not in cores_encontradas:
                            cores_encontradas[rgb] = contador_cores; contador_cores += 1

            html_grid = "<div style='display:flex; flex-direction:column; gap:4px; padding:15px; background:#111; border-radius:10px; align-items:center; width:100%; max-height: 600px; overflow-y: auto;'>"
            
            if is_radial:
                for r_idx in range(num_carreiras_radial, 0, -1):
                    n_pontos = r_idx * pontos_anel_magico
                    start_abs = (r_idx - 1) * r_idx // 2 * pontos_anel_magico
                    
                    html_grid += "<div style='display:flex; gap:2px; justify-content:center; flex-wrap:wrap; margin-bottom:4px;'>"
                    html_grid += f"<div style='width: 50px; text-align:right; font-size:11px; margin-right:5px; color:#888; align-self:center;'>C {r_idx}</div>"
                    
                    for s in range(n_pontos):
                        ponto_absoluto = start_abs + s + 1
                        rgb = radial_map[r_idx][s]
                        num_cor = cores_encontradas[rgb]
                        hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                        brilho = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
                        cor_texto = "black" if brilho > 128 else "white"
                        num_exibicao = str(ponto_absoluto) if "Sequência" in estilo_texto else str(num_cor)
                        
                        estilo = f"opacity:1; transform:scale(1.4); z-index:50; border:2px solid #00FF00; box-shadow:0 0 10px #00FF00;" if ponto_absoluto == st.session_state.ponto_parada else ("opacity:0.9;" if ponto_absoluto < st.session_state.ponto_parada else "opacity:0.15;")
                        html_grid += f"<div style='background:{hex_color}; color:{cor_texto}; width:16px; height:16px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:8px; font-weight:bold; {estilo}'>{num_exibicao}</div>"
                    html_grid += "</div>"
            else:
                for y in range(altura_carreiras):
                    html_grid += "<div style='display:flex; gap:1px; min-width:max-content;'>"
                    num_carr = altura_carreiras - y
                    dir_seta = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                    html_grid += f"<div style='width: 40px; text-align:right; font-size:11px; margin-right:5px; color:#888; align-self:center;'>C {num_carr} {dir_seta}</div>"
                    
                    for x in range(largura_pontos):
                        p_carr = x + 1 if "Plana" in tipo_peca and num_carr % 2 == 0 else largura_pontos - x 
                        ponto_absoluto = ((num_carr - 1) * largura_pontos) + p_carr
                        rgb = pixels[x, y]
                        num_cor = cores_encontradas[rgb]
                        hex_color = '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])
                        brilho = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114)/1000
                        cor_texto = "black" if brilho > 128 else "white"
                        num_exibicao = str(ponto_absoluto) if "Sequência" in estilo_texto else str(num_cor)
                        
                        estilo = f"opacity:1; transform:scale(1.4); z-index:50; border:2px solid red;" if ponto_absoluto == st.session_state.ponto_parada else ("opacity:0.9;" if ponto_absoluto < st.session_state.ponto_parada else "opacity:0.15;")
                        html_grid += f"<div style='background:{hex_color}; color:{cor_texto}; width:18px; height:18px; display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:bold; {estilo}'>{num_exibicao}</div>"
                    html_grid += "</div>"
            
            html_grid += "</div>"
            st.markdown(html_grid, unsafe_allow_html=True)

            with st.expander("📝 Ver Receita Escrita (Passo a Passo)"):
                sigla_pt = " PB"
                if "Baixo" in tipo_ponto_base: sigla_pt = " PB"
                elif "Meio" in tipo_ponto_base: sigla_pt = " MPA"
                elif "Alto" in tipo_ponto_base: sigla_pt = " PA"
                elif "Baixíssimo" in tipo_ponto_base: sigla_pt = " PBX"
                elif "Cores" in tipo_ponto_base: sigla_pt = ""
                
                txt_rec = f"RECEITA DE CROCHÊ\nTipo: {tipo_peca}\nPonto Base: {tipo_ponto_base}\nTotal: {total_pontos} pontos\n" + "-"*30 + "\n\n"
                
                if is_radial:
                    st.info(f"💡 Dica Radial: Cada carreira tem os pontos totais marcados. Distribua {pontos_anel_magico} aumentos uniformemente em cada volta!")
                    for r_idx in range(1, num_carreiras_radial + 1):
                        seq, cor_atual, cont = [], None, 0
                        n_pontos = r_idx * pontos_anel_magico
                        for s in range(n_pontos):
                            rgb = radial_map[r_idx][s]
                            num_cor = cores_encontradas[rgb]
                            if cor_atual is None: cor_atual = num_cor; cont = 1
                            elif cor_atual == num_cor: cont += 1
                            else: seq.append(f"{cont}x{sigla_pt} Cor {cor_atual}"); cor_atual = num_cor; cont = 1
                        if cont > 0: seq.append(f"{cont}x{sigla_pt} Cor {cor_atual}")
                        
                        linha = f"**Carr {r_idx}** ({n_pontos} pts): " + ", ".join(seq)
                        st.markdown(linha)
                        txt_rec += f"Carr {r_idx} ({n_pontos} pts): " + ", ".join(seq) + "\n"
                else:
                    for y in range(altura_carreiras - 1, -1, -1):
                        num_carr = altura_carreiras - y
                        dir_seta = "⬅️" if "Plana" in tipo_peca and num_carr % 2 == 0 else "➔"
                        range_x = range(largura_pontos) if "Plana" in tipo_peca and num_carr % 2 == 0 else range(largura_pontos - 1, -1, -1) 
                        
                        seq, cor_atual, cont = [], None, 0
                        for x in range_x:
                            rgb = pixels[x, y]
                            num_cor = cores_encontradas[rgb]
                            if cor_atual is None: cor_atual = num_cor; cont = 1
                            elif cor_atual == num_cor: cont += 1
                            else: seq.append(f"{cont}x{sigla_pt} Cor {cor_atual}"); cor_atual = num_cor; cont = 1
                        if cont > 0: seq.append(f"{cont}x{sigla_pt} Cor {cor_atual}")
                        
                        linha = f"**Carr {num_carr} {dir_seta}:** " + ", ".join(seq)
                        st.markdown(linha)
                        txt_rec += f"Carr {num_carr} {dir_seta}: " + ", ".join(seq) + "\n"

                st.download_button("💾 Baixar Receita em Texto", data=txt_rec, file_name="minha_receita.txt")

            if not is_radial:
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
                st.download_button("📥 Baixar Tabuleiro Estático (PNG)", data=buf.getvalue(), file_name="grafico_regua.png", mime="image/png", type="secondary")

        except Exception as e: st.error(f"Erro no processamento: {e}")

    st.divider()

    # ==========================================
    # INTEGRAÇÃO FINANCEIRA COM INVENTÁRIO
    # ==========================================
    st.header("💰 Parte 2: Orçamento Integrado")
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

