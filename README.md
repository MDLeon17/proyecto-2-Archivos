# Agenda de contactos · Laboratorio 2

Aplicación de escritorio en Python y Tkinter para agregar, buscar y editar contactos mediante registros de tamaño fijo. La carpeta incluye ocho contactos ficticios y salidas de ejemplo.

## Ejecutar en Windows

Abre PowerShell en esta carpeta. Usa Python 3.11 o superior con Tkinter.

```powershell
py -m pip install -r requirements.txt
py main.py
```

## Usar la agenda

La agenda abre en pantalla completa. Usa la barra lateral para cambiar entre **Contactos**, **Exportar** y **Herramientas**. Pulsa **Cerrar aplicación** para salir. Al abrirse, la agenda toma el modo claro u oscuro y el color de acento de Windows.

- **Agregar**. Completa ID, nombre, teléfono, correo y ciudad. El ID debe ser un entero único.
- **Buscar y editar**. Escribe el ID y pulsa **Buscar por ID**. Cambia los datos y pulsa **Guardar cambios**. El ID se conserva. La barra inferior muestra el número de registro y la posición obtenida con `tell()`.
- **Exportar**. Elige JSON o reporte PDF. El PDF se genera a partir de un JSON de los contactos actuales.
- **Herramientas**. Verifica el SHA-256, crea un ZIP o consulta el tamaño, la fecha de modificación y los permisos del archivo.

## Archivos del proyecto

| Archivo o carpeta | Contenido |
| --- | --- |
| `main.py` | Interfaz gráfica |
| `agenda.py` | Formato fijo, acceso directo, índice, integridad y respaldos |
| `reporte.py` | Generación del reporte PDF a partir de JSON |
| `datos/` | `contactos.dat`, `indice.json` y `contactos.sha256` |
| `salidas/` | JSON, PDF y ZIP generados con la agenda de ejemplo |
| `informe_laboratorio.pdf` | Formato, implementación, comparación y capturas de las pruebas |

Cada registro ocupa 180 bytes en UTF-8, incluidos los espacios de relleno y un salto de línea LF. Los límites se miden en bytes. Una letra con tilde puede ocupar más de un byte. El PDF muestra los caracteres fuera de su fuente mediante su código Unicode. Los archivos de datos y el JSON conservan los caracteres originales.

Si el índice falta o está dañado y el archivo de contactos coincide con su SHA-256, la agenda reconstruye el índice al iniciar. Si la verificación falla, cierra la aplicación y restaura `contactos.dat`, `indice.json` y `contactos.sha256` juntos desde un respaldo válido. Conserva una copia de los archivos que vas a sustituir si necesitas investigarlos.
