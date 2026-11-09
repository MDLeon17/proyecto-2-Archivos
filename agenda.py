"""Persistencia de la agenda en registros de texto UTF-8 de tamaño fijo."""

import hashlib
import json
import os
import re
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

CAMPOS = (("id", 10), ("nombre", 48), ("telefono", 22), ("correo", 64), ("ciudad", 35))
TAM_REGISTRO = sum(ancho for _, ancho in CAMPOS) + 1


class ErrorAgenda(Exception):
    """Problema que puede mostrarse en la interfaz."""


def normalizar_id(valor):
    texto = str(valor).strip()
    if not re.fullmatch(r"[+-]?[0-9]{1,10}", texto):
        raise ErrorAgenda("El ID debe ser un número entero de hasta 10 bytes.")
    numero = int(texto)
    if len(str(numero)) > CAMPOS[0][1]:
        raise ErrorAgenda("El ID, incluido su signo, debe caber en 10 bytes.")
    return numero


def codificar_contacto(contacto):
    partes = []
    for campo, ancho in CAMPOS:
        texto = str(contacto[campo]).strip()
        if campo == "id":
            texto = str(normalizar_id(texto))
        if not texto or not texto.isprintable():
            raise ErrorAgenda(f"Completa el campo «{campo}» con texto en una sola línea.")
        dato = texto.encode("utf-8")
        if len(dato) > ancho:
            raise ErrorAgenda(f"El campo «{campo}» admite hasta {ancho} bytes en UTF-8.")
        partes.append(dato.ljust(ancho, b" "))
    return b"".join(partes) + b"\n"


def leer_registro(datos, posicion):
    if len(datos) != TAM_REGISTRO or not datos.endswith(b"\n"):
        raise ErrorAgenda(f"Registro incompleto o inválido en el byte {posicion}.")
    contacto = {}
    inicio = 0
    try:
        for campo, ancho in CAMPOS:
            contacto[campo] = datos[inicio:inicio + ancho].decode("utf-8").rstrip(" ")
            inicio += ancho
        contacto["id"] = normalizar_id(contacto["id"])
        if codificar_contacto(contacto) != datos:
            raise ErrorAgenda("El formato del registro no coincide.")
    except (UnicodeError, ErrorAgenda) as error:
        raise ErrorAgenda(f"Registro inválido en el byte {posicion}: {error}") from error
    return contacto


@contextmanager
def destino_atomico(destino):
    """Publica un archivo completo incluso si reemplaza una versión anterior."""
    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as archivo:
        temporal = Path(archivo.name)
    try:
        yield temporal
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)


def escribir_texto(destino, texto):
    with destino_atomico(destino) as temporal:
        temporal.write_text(texto, encoding="utf-8", newline="\n")


@contextmanager
def sesion_exclusiva(carpeta):
    """Impide que dos instancias de la agenda escriban en la misma carpeta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    with (carpeta / ".agenda.lock").open("a+b") as bloqueo:
        try:
            if os.name == "nt":
                import msvcrt

                bloqueo.seek(0)
                msvcrt.locking(bloqueo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ErrorAgenda("La agenda ya está abierta en otra instancia.") from error
        yield


class Agenda:
    def __init__(self, carpeta):
        self.datos = carpeta / "contactos.dat"
        self.ruta_indice = carpeta / "indice.json"
        self.hash = carpeta / "contactos.sha256"
        self.indice = None
        self._version = None

    def preparar(self):
        """Abre la agenda y recupera el índice a partir de datos verificados."""
        self.indice = None
        self._version = None
        if not any(ruta.exists() for ruta in (self.datos, self.ruta_indice, self.hash)):
            self.datos.touch(exist_ok=False)
            self._escribir_indice({})
            escribir_texto(self.hash, hashlib.sha256(b"").hexdigest() + "\n")

        try:
            self.indice = self._leer_indice()
        except (ErrorAgenda, OSError):
            pass

        coincide, mensaje = self.verificar_integridad()
        if not coincide:
            return mensaje + "\nLos cambios quedan bloqueados hasta recuperar los archivos."

        esperado = {}
        for numero, contacto in enumerate(self._recorrer()):
            identificador = str(contacto["id"])
            if identificador in esperado:
                raise ErrorAgenda(f"El archivo contiene un ID repetido: {identificador}.")
            esperado[identificador] = numero
        if self.indice != esperado:
            self._escribir_indice(esperado)
            self.indice = esperado
            mensaje = "Se reconstruyó indice.json a partir de los registros verificados."
        else:
            mensaje = None
        self._version = self._version_archivos()
        return mensaje

    def _leer_indice(self):
        try:
            indice = json.loads(self.ruta_indice.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ErrorAgenda("El índice JSON está dañado.") from error
        if not isinstance(indice, dict) or any(
            type(numero) is not int or numero < 0 for numero in indice.values()
        ):
            raise ErrorAgenda("El índice contiene posiciones inválidas.")
        return indice

    def _escribir_indice(self, indice):
        escribir_texto(self.ruta_indice, json.dumps(indice, indent=2) + "\n")

    def _version_archivos(self):
        estadisticas = (ruta.stat() for ruta in (self.datos, self.ruta_indice, self.hash))
        return tuple(
            (info.st_ino, info.st_size, info.st_mtime_ns) for info in estadisticas
        )

    def _comprobar_escritura(self):
        if self._version is None or self._version_archivos() != self._version:
            raise ErrorAgenda(
                "Los archivos requieren revisión. Verifica la integridad y vuelve a abrir la agenda."
            )

    def verificar_integridad(self):
        try:
            with self.datos.open("rb") as archivo:
                actual = hashlib.file_digest(archivo, "sha256").hexdigest()
        except FileNotFoundError:
            return False, "Falta contactos.dat. Puedes recuperarlo desde un respaldo."
        try:
            esperado = self.hash.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return False, "Falta contactos.sha256. No se puede comprobar la integridad."
        except UnicodeError:
            return False, "contactos.sha256 no contiene texto UTF-8 válido."
        if not re.fullmatch(r"[a-f0-9]{64}", esperado):
            return False, "contactos.sha256 no contiene un hash SHA-256 válido."
        if actual != esperado:
            return False, "El SHA-256 no coincide. contactos.dat fue alterado fuera de la agenda."
        return True, "El SHA-256 coincide. El archivo de contactos está íntegro."

    def _posicion(self, identificador):
        if self.indice is None:
            raise ErrorAgenda("El índice de contactos no está disponible.")
        try:
            return self.indice[str(identificador)] * TAM_REGISTRO
        except KeyError:
            raise ErrorAgenda(f"No se encontró un contacto con ID {identificador}.") from None

    def _leer_en(self, archivo, identificador, desplazamiento):
        archivo.seek(desplazamiento)
        posicion = archivo.tell()
        datos = archivo.read(TAM_REGISTRO)
        if leer_registro(datos, posicion)["id"] != identificador:
            raise ErrorAgenda("El registro indicado no coincide con el índice.")
        return datos, posicion

    def buscar(self, valor_id):
        identificador = normalizar_id(valor_id)
        desplazamiento = self._posicion(identificador)
        with self.datos.open("rb") as archivo:
            datos, posicion = self._leer_en(archivo, identificador, desplazamiento)
        return leer_registro(datos, posicion), posicion

    def agregar(self, contacto):
        self._comprobar_escritura()
        identificador = str(normalizar_id(contacto["id"]))
        if identificador in self.indice:
            raise ErrorAgenda(f"Ya existe un contacto con ID {identificador}.")
        datos = codificar_contacto(contacto)
        with self.datos.open("r+b") as archivo:
            archivo.seek(0, os.SEEK_END)
            posicion = archivo.tell()
            nuevo_indice = {**self.indice, identificador: posicion // TAM_REGISTRO}
            self._guardar(archivo, posicion, datos, anterior=b"", indice=nuevo_indice)
        return posicion

    def modificar(self, valor_id, contacto):
        self._comprobar_escritura()
        identificador = normalizar_id(valor_id)
        if normalizar_id(contacto["id"]) != identificador:
            raise ErrorAgenda("El ID de un contacto existente se conserva al editarlo.")
        datos = codificar_contacto(contacto)
        with self.datos.open("r+b") as archivo:
            anterior, posicion = self._leer_en(archivo, identificador, self._posicion(identificador))
            self._guardar(archivo, posicion, datos, anterior)
        return posicion

    def _guardar(self, archivo, posicion, datos, anterior, indice=None):
        indice_publicado = False
        try:
            archivo.seek(posicion)
            archivo.write(datos)
            archivo.flush()
            os.fsync(archivo.fileno())
            archivo.seek(0)
            firma = hashlib.file_digest(archivo, "sha256").hexdigest()
            if indice is not None:
                self._escribir_indice(indice)
                indice_publicado = True
            escribir_texto(self.hash, firma + "\n")
        except OSError:
            self._version = None
            try:
                archivo.seek(posicion)
                if anterior:
                    archivo.write(anterior)
                else:
                    archivo.truncate(posicion)
                archivo.flush()
                os.fsync(archivo.fileno())
                if indice_publicado:
                    self._escribir_indice(self.indice)
                self._version = self._version_archivos()
            except OSError as error:
                raise ErrorAgenda(
                    "Se interrumpió la escritura. Revisa la integridad antes de volver a guardar."
                ) from error
            raise
        if indice is not None:
            self.indice = indice
        self._version = self._version_archivos()

    def _recorrer(self):
        with self.datos.open("rb") as archivo:
            while datos := archivo.read(TAM_REGISTRO):
                yield leer_registro(datos, archivo.tell() - len(datos))

    def proteger_destino(self, destino):
        protegidos = (self.datos, self.ruta_indice, self.hash, self.datos.parent / ".agenda.lock")
        if destino.resolve() in {ruta.resolve() for ruta in protegidos}:
            raise ErrorAgenda("Elige una ruta de salida distinta de los archivos de la agenda.")

    def exportar_json(self, destino):
        self.proteger_destino(destino)
        contactos = list(self._recorrer())
        escribir_texto(destino, json.dumps(contactos, ensure_ascii=False, indent=2) + "\n")
        return len(contactos)

    def crear_respaldo(self, destino):
        self.proteger_destino(destino)
        self._comprobar_escritura()
        fuentes = (self.datos, self.ruta_indice, self.hash)
        with destino_atomico(destino) as temporal:
            with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as respaldo:
                for fuente in fuentes:
                    respaldo.write(fuente, arcname=fuente.name)
            original = sum(fuente.stat().st_size for fuente in fuentes)
            comprimido = temporal.stat().st_size
        return original, comprimido

    def informacion(self):
        info = self.datos.stat()
        return {
            "ruta": self.datos,
            "bytes": info.st_size,
            "modificado": datetime.fromtimestamp(info.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            "lectura": os.access(self.datos, os.R_OK),
            "escritura": os.access(self.datos, os.W_OK),
        }
