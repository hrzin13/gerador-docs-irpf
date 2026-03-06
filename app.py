import flet as ft
from PIL import Image
import io
import base64

def main(page: ft.Page):
    page.title = "Fio & Arte - Gerador de Gráfico Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 1. Configurando o Fundo Aconchegante (Novelos de Lã)
    # IMPORTANTE: Você precisa ter uma imagem de fundo ('fundo_artesanato.jpg') na mesma pasta do script
    # Se não tiver a imagem, ele vai usar um fundo cinza claro.
    try:
        page.bgcolor = ft.colors.TRANSPARENT
        page.decoration = ft.BoxDecoration(
            image=ft.DecorationImage(
                src="fundo_artesanato.jpg", # Nome do seu arquivo de imagem
                fit=ft.ImageFit.COVER,
                opacity=0.3 # Deixa a imagem suave para não poluir
            )
        )
    except:
        page.bgcolor = ft.colors.GREY_50
        st.warning("A imagem 'fundo_artesanato.jpg' não foi encontrada. Usando fundo padrão.")

    # 2. Configurando o Visual Profissional
    visual_theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.colors.BROWN_600, # Cor "Artística" para botões
            secondary=ft.colors.PINK_300
        ),
        visual_density=ft.VisualDensity.COMFORTABLE
    )
    page.theme = visual_theme

    # Variáveis para armazenar o estado
    imagem_carregada_b64 = None
    largura_pontos = 20
    altura_carreiras = 20
    num_cores = 3

    # Elementos de Interface
    img_preview = ft.Image(src="", visible=False, border_radius=10, width=150)
    txt_proporcao = ft.Text("", weight="bold")
    
    # --- FUNÇÃO: PEGAR A IMAGEM ---
    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal imagem_carregada_b64, largura_pontos, altura_carreiras
        if e.files:
            file_path = e.files[0].path
            try:
                # Abre para prévia e cálculo de proporção (Igual ao Streamlit)
                img_temp = Image.open(file_path)
                largura_orig, altura_orig = img_temp.size
                proporcao = altura_orig / largura_orig
                
                # Atualiza a interface (Flet é reativo)
                txt_proporcao.value = f"📐 Resolução original: {largura_orig}x{altura_orig}. Proporção ideal!"
                
                # Lógica de Preset Inteligente (Simplificada para o teste)
                max_dim = 60 # Preset Médio padrão
                if largura_orig > altura_orig:
                    largura_pontos = max_dim
                    altura_carreiras = max(5, int(max_dim * proporcao))
                else:
                    altura_carreiras = max_dim
                    largura_pontos = max(5, int(max_dim / proporcao))
                
                # Converte para base64 para mostrar a prévia no Flet
                with open(file_path, "rb") as image_file:
                    imagem_carregada_b64 = base64.b64encode(image_file.read()).decode('utf-8')
                
                img_preview.src_base64 = imagem_carregada_b64
                img_preview.visible = True
                
                slider_largura.value = largura_pontos
                slider_altura.value = altura_carreiras
                
                page.update() # Importante atualizar a página no Flet
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"))
                page.snack_bar.open = True
                page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # Sliders Profissionais (Flet desenha eles muito mais lisos que HTML)
    slider_largura = ft.Slider(min=5, max=100, value=largura_pontos, label="{value} Pontos", active_color=visual_theme.color_scheme.primary)
    slider_altura = ft.Slider(min=5, max=100, value=altura_carreiras, label="{value} Carreiras", active_color=visual_theme.color_scheme.primary)
    slider_cores = ft.Slider(min=2, max=20, value=num_cores, label="{value} Cores", active_color=visual_theme.color_scheme.primary)

    # Layout Principal (Muito mais organizado que Streamlit)
    interface_container = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("🏁 Visual do App", size=24, weight="bold")
            ], alignment="center"),
            
            ft.Divider(height=10),
            
            # Seção de Upload
            ft.Row([
                ft.ElevatedButton("Anexar Imagem", icon=ft.icons.ATTACH_FILE, on_click=lambda _: file_picker.pick_files()),
                txt_proporcao
            ], spacing=10),
            
            # Prévia
            ft.Row([img_preview], alignment="center"),
            
            # Controles
            ft.Text("Ajustes de Resolução", weight="bold"),
            slider_largura,
            slider_altura,
            
            ft.Text("Simplificar Cores", weight="bold"),
            slider_cores,
            
            # Botão Gerar
            ft.Row([
                ft.ElevatedButton("Gerar Gráfico", icon=ft.icons.BRUSH, style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=visual_theme.color_scheme.primary))
            ], alignment="center")
            
        ], spacing=15),
        padding=20,
        bgcolor=ft.colors.WHITE,
        border_radius=15,
        border=ft.border.all(1, ft.colors.GREY_300),
        width=page.width * 0.9 if page.width < 500 else 450, # Responsivo
        shadow=ft.BoxShadow(blur_radius=10, color=ft.colors.with_opacity(0.1, ft.colors.BLACK)) # Sombra professional
    )

    page.add(
        ft.Row([interface_container], alignment="center")
    )

ft.app(target=main)
