"""Tema claro u oscuro y botones redondeados para la agenda."""

import os
from tkinter import ttk

from PIL import Image, ImageColor, ImageDraw, ImageTk


def _colores_del_sistema():
    oscuro = False
    acento = "#0078D4"
    if os.name == "nt":
        import winreg

        try:
            ruta = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta) as clave:
                oscuro = winreg.QueryValueEx(clave, "AppsUseLightTheme")[0] == 0
        except OSError:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as clave:
                color, tipo = winreg.QueryValueEx(clave, "AccentColor")
            if tipo == winreg.REG_DWORD:
                # Windows guarda el DWORD en formato AABBGGRR.
                acento = "#" + "".join(f"{(color >> bits) & 0xFF:02X}" for bits in (0, 8, 16))
        except OSError:
            pass
    return oscuro, acento


def _mezclar(color, otro, peso):
    inicial = ImageColor.getrgb(color)
    final = ImageColor.getrgb(otro)
    canales = (round(a + (b - a) * peso) for a, b in zip(inicial, final))
    return "#" + "".join(f"{canal:02X}" for canal in canales)


def _contraste(color):
    canales = (componente / 255 for componente in ImageColor.getrgb(color))
    lineales = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    luminancia = sum(c * peso for c, peso in zip(lineales, (0.2126, 0.7152, 0.0722)))
    return "#000000" if luminancia > 0.179 else "#FFFFFF"


def _imagen_boton(raiz, radio, fondo, borde):
    escala = 4
    lado = 2 * radio + 3
    lado_grande = lado * escala
    imagen = Image.new("RGBA", (lado_grande, lado_grande))
    ImageDraw.Draw(imagen).rounded_rectangle(
        (0, 0, lado_grande - 1, lado_grande - 1),
        radius=radio * escala, fill=fondo, outline=borde, width=escala,
    )
    imagen = imagen.resize((lado, lado), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(imagen, master=raiz)


def _estilo_boton(estilo, raiz, nombre, radio, base, estados):
    normal = _imagen_boton(raiz, radio, *base)
    variantes = [
        (*estado, _imagen_boton(raiz, radio, fondo, borde))
        for estado, fondo, borde in estados
    ]
    elemento = f"Agenda.{nombre}.borde"
    estilo.element_create(elemento, "image", normal, *variantes,
                          border=radio + 1, padding=2, sticky="nsew")
    _, diseno = estilo.layout(nombre)[0]
    diseno.pop("border", None)
    estilo.layout(nombre, [(elemento, diseno)])
    # Tk mantiene el nombre de cada imagen. Python conserva sus referencias.
    return [normal, *(variante[-1] for variante in variantes)]


def configurar_tema(raiz):
    oscuro, acento = _colores_del_sistema()
    if oscuro:
        fondo, lateral, tarjeta = "#202020", "#191919", "#282828"
        tinta, secundario = "#F5F5F5", "#C2C2C2"
        boton, borde = "#343434", "#505050"
        fondo_aviso, tinta_aviso = "#4B3517", "#FFE2A6"
    else:
        fondo, lateral, tarjeta = "#F3F3F3", "#EAEAEA", "#FFFFFF"
        tinta, secundario = "#202020", "#555555"
        boton, borde = "#FBFBFB", "#C4C4C4"
        fondo_aviso, tinta_aviso = "#FFF1D1", "#663C0B"

    tinta_acento = _contraste(acento)
    opuesto = _contraste(tinta_acento)
    acento_activo = _mezclar(acento, opuesto, 0.12)
    acento_presionado = _mezclar(acento, opuesto, 0.23)
    inactivo = _mezclar(boton, tarjeta, 0.50)
    tinta_inactiva = _mezclar(tinta, tarjeta, 0.55)
    campo = fondo if oscuro else tarjeta

    raiz.configure(bg=fondo)
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    estilo.configure("TFrame", background=fondo)
    estilo.configure("Card.TFrame", background=tarjeta)
    estilo.configure("Sidebar.TFrame", background=lateral)
    estilo.configure("Page.TLabel", background=fondo, foreground=tinta,
                     font=("Segoe UI", 24, "bold"))
    estilo.configure("Sidebar.TLabel", background=lateral, foreground=tinta,
                     font=("Segoe UI", 13, "bold"))
    estilo.configure("SidebarCaption.TLabel", background=lateral, foreground=secundario,
                     font=("Segoe UI", 9, "bold"))
    estilo.configure("Card.TLabel", background=tarjeta, foreground=tinta, font=("Segoe UI", 10))
    estilo.configure("Heading.TLabel", background=tarjeta, foreground=tinta,
                     font=("Segoe UI", 15, "bold"))
    estilo.configure("Hint.TLabel", background=tarjeta, foreground=secundario, font=("Segoe UI", 9))
    estilo.configure("TEntry", padding=5, background=tarjeta, fieldbackground=campo, foreground=tinta,
                     bordercolor=borde, lightcolor=campo, darkcolor=campo, insertcolor=tinta,
                     selectbackground=acento, selectforeground=tinta_acento)
    estilo.map("TEntry", bordercolor=[("focus", acento)])
    estilo.configure("Normal.TLabel", background=_mezclar(fondo, acento, 0.16), foreground=tinta,
                     padding=(12, 9), font=("Segoe UI", 10))
    estilo.configure("Aviso.TLabel", background=fondo_aviso, foreground=tinta_aviso,
                     padding=(12, 9), font=("Segoe UI", 10))

    estilo.configure("TButton", padding=(11, 7), font=("Segoe UI", 10), foreground=tinta,
                     background=tarjeta, focuscolor=tinta)
    estilo.map("TButton", background=[("", tarjeta)], foreground=[("disabled", tinta_inactiva)])
    estilo.map("Sidebar.TButton", background=[("", lateral)])
    estilo.configure("Primary.TButton", foreground=tinta_acento, focuscolor=tinta_acento)
    estilo.map("Primary.TButton", foreground=[("disabled", tinta_inactiva)])
    estilo.configure("Nav.Toolbutton", anchor="w", padding=(12, 10), foreground=tinta,
                     focuscolor=tinta, font=("Segoe UI", 11))
    estilo.map("Nav.Toolbutton", background=[("", lateral)], foreground=[("selected", tinta_acento)],
               focuscolor=[("selected", tinta_acento)])

    radio = max(4, round(raiz.winfo_fpixels("5p")))
    desactivado = (("disabled",), inactivo, _mezclar(borde, tarjeta, 0.50))
    raiz.imagenes_botones = _estilo_boton(estilo, raiz, "TButton", radio, (boton, borde), (
        desactivado,
        (("pressed",), _mezclar(boton, tinta, 0.16), borde),
        (("active",), _mezclar(boton, tinta, 0.08), borde),
    ))
    raiz.imagenes_botones += _estilo_boton(estilo, raiz, "Primary.TButton", radio, (acento, acento), (
        desactivado,
        (("pressed",), acento_presionado, acento_presionado),
        (("active",), acento_activo, acento_activo),
    ))
    lateral_activo = _mezclar(lateral, tinta, 0.10)
    lateral_presionado = _mezclar(lateral, tinta, 0.17)
    raiz.imagenes_botones += _estilo_boton(estilo, raiz, "Nav.Toolbutton", radio, (lateral, lateral), (
        (("selected", "pressed"), acento_presionado, acento_presionado),
        (("selected", "active"), acento_activo, acento_activo),
        (("selected",), acento, acento),
        (("pressed",), lateral_presionado, lateral_presionado),
        (("active",), lateral_activo, lateral_activo),
    ))

