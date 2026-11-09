"""Interfaz de escritorio de la agenda de contactos."""

import tempfile
import tkinter as tk
from functools import partial
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from agenda import Agenda, CAMPOS, ErrorAgenda, TAM_REGISTRO, sesion_exclusiva
from reporte import generar_pdf

PROYECTO = Path(__file__).resolve().parent
ETIQUETAS = {"id": "ID", "nombre": "Nombre", "telefono": "Teléfono",
             "correo": "Correo", "ciudad": "Ciudad"}


class VentanaAgenda:
    def __init__(self, raiz, agenda, salidas):
        self.raiz = raiz
        self.agenda = agenda
        self.salidas = salidas
        self.id_cargado = None
        self.campos = {campo: tk.StringVar() for campo, _ in CAMPOS}
        self.estado = tk.StringVar(value="Lista para agregar un contacto o buscar por ID.")

        raiz.title("Agenda de contactos | Laboratorio 2")
        raiz.configure(bg="#F0F3F8")
        self._estilos()
        self._crear_menu()
        self._crear_formulario()
        raiz.update_idletasks()
        ancho = max(690, raiz.winfo_reqwidth())
        alto = max(530, raiz.winfo_reqheight())
        raiz.minsize(ancho, alto)
        raiz.geometry(f"{ancho}x{alto}")
        self.entrada_id.focus_set()
        self._ejecutar(self._iniciar)

    def _estilos(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#F0F3F8")
        estilo.configure("Card.TFrame", background="#FFFFFF")
        estilo.configure("Card.TLabel", background="#FFFFFF", foreground="#172849",
                         font=("Segoe UI", 10))
        estilo.configure("Heading.TLabel", background="#FFFFFF", foreground="#172849",
                         font=("Segoe UI", 15, "bold"))
        estilo.configure("Hint.TLabel", background="#FFFFFF", foreground="#4D5E78",
                         font=("Segoe UI", 9))
        estilo.configure("TEntry", padding=5, fieldbackground="#FFFFFF")
        estilo.configure("TButton", padding=(11, 6), font=("Segoe UI", 10))
        estilo.configure("Primary.TButton", background="#254D91", foreground="white")
        estilo.map("Primary.TButton",
                   background=[("pressed", "#173869"), ("active", "#3262A8")])
        for nombre, fondo, tinta in (("Normal", "#DDE9F8", "#193E73"),
                                     ("Aviso", "#FFF0CB", "#713C0D")):
            estilo.configure(f"{nombre}.TLabel", background=fondo, foreground=tinta,
                             padding=(12, 9), font=("Segoe UI", 10))

    def _crear_menu(self):
        barra = tk.Menu(self.raiz)
        menus = (
            ("Contactos", (("Agregar contacto", self.agregar), ("Buscar por ID", self.buscar),
                           ("Guardar cambios", self.modificar), ("Limpiar formulario", self.limpiar))),
            ("Exportar", (("Exportar a JSON…", self.exportar_json),
                          ("Generar reporte PDF…", self.exportar_pdf))),
            ("Herramientas", (("Verificar integridad", self.verificar_integridad),
                              ("Crear respaldo ZIP…", self.crear_respaldo),
                              ("Información del archivo", self.informacion))),
            ("Ayuda", (("Acerca de la agenda", self.ayuda),)),
        )
        for titulo, opciones in menus:
            menu = tk.Menu(barra, tearoff=False)
            for texto, operacion in opciones:
                menu.add_command(label=texto, command=partial(self._ejecutar, operacion))
            barra.add_cascade(label=titulo, menu=menu)
        self.raiz.config(menu=barra)

    def _crear_formulario(self):
        encabezado = tk.Frame(self.raiz, bg="#172849", padx=23, pady=16)
        encabezado.pack(fill="x")
        tk.Label(encabezado, text="LABORATORIO 2  /  MANEJO DE ARCHIVOS",
                 bg="#172849", fg="#B6D2FD", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(encabezado, text="Agenda de contactos", bg="#172849", fg="#FFFFFF",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")

        area = ttk.Frame(self.raiz, padding=(21, 15, 21, 15))
        area.pack(fill="both", expand=True)
        tarjeta = ttk.Frame(area, style="Card.TFrame", padding=(18, 14))
        tarjeta.pack(fill="both", expand=True)
        tarjeta.columnconfigure(1, weight=1)
        ttk.Label(tarjeta, text="Ficha de contacto", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(tarjeta, text="Escribe un ID entero para buscar o completa los cinco campos para agregar.",
                  style="Hint.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))

        for fila, (campo, _) in enumerate(CAMPOS, start=2):
            ttk.Label(tarjeta, text=ETIQUETAS[campo], style="Card.TLabel").grid(
                row=fila, column=0, sticky="w", padx=(0, 16), pady=4)
            entrada = ttk.Entry(tarjeta, textvariable=self.campos[campo])
            entrada.grid(row=fila, column=1, columnspan=1 if campo == "id" else 2,
                         sticky="ew", pady=4)
            if campo == "id":
                self.entrada_id = entrada
                entrada.bind("<Return>", lambda _evento: self._ejecutar(self.buscar))
                ttk.Button(tarjeta, text="Buscar por ID", command=partial(self._ejecutar, self.buscar)).grid(
                    row=fila, column=2, sticky="e", padx=(10, 0))

        acciones = ttk.Frame(tarjeta, style="Card.TFrame")
        acciones.grid(row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Button(acciones, text="Agregar contacto", style="Primary.TButton",
                   command=partial(self._ejecutar, self.agregar)).pack(side="left")
        self.boton_guardar = ttk.Button(acciones, text="Guardar cambios", state="disabled",
                                        command=partial(self._ejecutar, self.modificar))
        self.boton_guardar.pack(side="left", padx=9)
        ttk.Button(acciones, text="Limpiar", command=self.limpiar).pack(side="left")

        self.etiqueta_estado = ttk.Label(area, textvariable=self.estado, style="Normal.TLabel",
                                         wraplength=610, justify="left")
        self.etiqueta_estado.pack(fill="x", pady=(12, 0))

    def _iniciar(self):
        aviso = self.agenda.preparar()
        if aviso:
            self._estado(aviso, aviso=True)

    def _estado(self, texto, aviso=False):
        self.estado.set(texto)
        self.etiqueta_estado.configure(style="Aviso.TLabel" if aviso else "Normal.TLabel")

    def _ejecutar(self, operacion):
        try:
            operacion()
        except (ErrorAgenda, OSError, UnicodeError) as error:
            self._estado(str(error), aviso=True)
            messagebox.showerror("Agenda de contactos", str(error), parent=self.raiz)

    def _capturar(self):
        return {campo: valor.get() for campo, valor in self.campos.items()}

    def _mostrar_posicion(self, accion, posicion):
        self._estado(
            f"{accion}   ·   Registro {posicion // TAM_REGISTRO}   ·   tell() = {posicion} bytes"
        )

    def agregar(self):
        contacto = self._capturar()
        posicion = self.agenda.agregar(contacto)
        self.id_cargado = int(contacto["id"])
        self.campos["id"].set(str(self.id_cargado))
        self.boton_guardar.state(["!disabled"])
        self._mostrar_posicion("Contacto agregado", posicion)

    def buscar(self):
        self.id_cargado = None
        self.boton_guardar.state(["disabled"])
        contacto, posicion = self.agenda.buscar(self.campos["id"].get())
        for campo, valor in contacto.items():
            self.campos[campo].set(str(valor))
        self.id_cargado = contacto["id"]
        self.boton_guardar.state(["!disabled"])
        self._mostrar_posicion("Contacto encontrado", posicion)

    def modificar(self):
        if self.id_cargado is None:
            raise ErrorAgenda("Busca primero el contacto por ID.")
        posicion = self.agenda.modificar(self.id_cargado, self._capturar())
        self._mostrar_posicion("Cambios guardados", posicion)

    def limpiar(self):
        for valor in self.campos.values():
            valor.set("")
        self.id_cargado = None
        self.boton_guardar.state(["disabled"])
        self._estado("Formulario limpio. Escribe un ID o agrega un contacto.")
        self.entrada_id.focus_set()

    def _elegir_salida(self, nombre, extension):
        self.salidas.mkdir(parents=True, exist_ok=True)
        ruta = filedialog.asksaveasfilename(
            parent=self.raiz, initialdir=self.salidas, initialfile=f"{nombre}.{extension}",
            defaultextension=f".{extension}", filetypes=[(extension.upper(), f"*.{extension}")],
        )
        return Path(ruta) if ruta else None

    def exportar_json(self):
        destino = self._elegir_salida("contactos", "json")
        if destino:
            cantidad = self.agenda.exportar_json(destino)
            self._estado(f"JSON exportado con {cantidad} contactos · {destino.name}")

    def exportar_pdf(self):
        destino = self._elegir_salida("reporte_contactos", "pdf")
        if destino:
            self.agenda.proteger_destino(destino)
            try:
                with tempfile.TemporaryDirectory() as carpeta:
                    ruta_json = Path(carpeta) / "contactos.json"
                    cantidad = self.agenda.exportar_json(ruta_json)
                    generar_pdf(ruta_json, destino)
            except ModuleNotFoundError as error:
                raise ErrorAgenda("Para generar PDF instala ReportLab con py -m pip install -r requirements.txt.") from error
            self._estado(f"Reporte PDF generado con {cantidad} contactos · {destino.name}")

    def verificar_integridad(self):
        coincide, mensaje = self.agenda.verificar_integridad()
        self._estado(mensaje, aviso=not coincide)

    def crear_respaldo(self):
        destino = self._elegir_salida("respaldo_contactos", "zip")
        if destino:
            original, comprimido = self.agenda.crear_respaldo(destino)
            self._estado(f"Respaldo creado · Original: {original} bytes · ZIP: {comprimido} bytes")
            messagebox.showinfo(
                "Respaldo ZIP",
                f"Archivos originales (datos, índice y hash): {original} bytes\n"
                f"Respaldo ZIP: {comprimido} bytes\n\n{destino}",
                parent=self.raiz,
            )

    def informacion(self):
        datos = self.agenda.informacion()
        lectura = "Sí" if datos["lectura"] else "No"
        escritura = "Sí" if datos["escritura"] else "No"
        messagebox.showinfo(
            "Información del archivo",
            f"{datos['ruta']}\n\nTamaño: {datos['bytes']} bytes\n"
            f"Última modificación: {datos['modificado']}\n"
            f"Permiso de lectura: {lectura}\nPermiso de escritura: {escritura}\n"
            f"Tamaño del registro: {TAM_REGISTRO} bytes",
            parent=self.raiz,
        )

    def ayuda(self):
        messagebox.showinfo("Acerca de la agenda", "Agenda de contactos con acceso aleatorio.\n"
                            "Laboratorio 2 · Manejo de archivos", parent=self.raiz)


def main():
    raiz = tk.Tk()
    carpeta = PROYECTO / "datos"
    try:
        with sesion_exclusiva(carpeta):
            VentanaAgenda(raiz, Agenda(carpeta), PROYECTO / "salidas")
            raiz.mainloop()
    except (ErrorAgenda, OSError) as error:
        raiz.withdraw()
        messagebox.showerror("No se pudo abrir la agenda", str(error), parent=raiz)
        raiz.destroy()


if __name__ == "__main__":
    main()
