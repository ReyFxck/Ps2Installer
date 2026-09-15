# Ps2Installer — Español

[README principal](../README.md) · [Português (Brasil)](README.pt-BR.md) · [English](README.en.md)

## Qué es

Ps2Installer es un asistente para crear paquetes de homebrew de PlayStation 2. Automatiza descargas de releases, selección de versiones, organización de ELFs y generación de configuraciones para PS2BBL, OSDMenu y OPL.

## Requisitos

- **Python 3.10+**;
- **Git** si clonas desde terminal;
- conexión a internet para consultar y descargar releases.

Comprueba la instalación:

```bash
python --version
git --version
```

En algunos sistemas utiliza `python3`. En Windows activa **Add Python to PATH** durante la instalación de Python.

Git no es obligatorio si utilizas **Code → Download ZIP** en GitHub.

## Instalación

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python main.py
```

Ya no es necesario instalar `py7zr` manualmente antes de ejecutar el programa. Si algún release seleccionado utiliza `.7z`, Ps2Installer verifica la dependencia antes de descargar y la instala automáticamente con el mismo intérprete de Python cuando sea necesario.

Alternativa manual:

```bash
python -m pip install -r requirements.txt
```

## Interfaz

El asistente de terminal incluye:

- banner ASCII de Ps2Installer;
- colores para títulos, éxitos, avisos y errores;
- limpieza de pantalla entre las etapas principales;
- explicaciones breves antes de cada elección;
- etiquetas claras para Stable, Beta/Prerelease y Development;
- pantalla de revisión antes de descargar;
- progreso legible durante descargas y generación del paquete.

El flujo normal pregunta idioma, carpeta de salida, tipo de Memory Card/VMC, almacenamiento de aplicaciones, homebrews opcionales, canal de release, descarga y generación final.

## Salida

Pulsa Enter para utilizar `./output` o elige otra carpeta con permiso de escritura. También puedes indicarla directamente:

```bash
python main.py --output ~/PS2/Paquete
```

La salida contiene `selection.json`, descargas temporales y `Ps2Installer_Package/`. El paquete separa el contenido de Memory Card/VMC del almacenamiento de aplicaciones e incluye instrucciones `README-COPY-HERE.txt` para ambos destinos.

## Integración de arranque y menús

PS2BBL permanece en la Memory Card/VMC. Cuando el modo de almacenamiento seleccionado es compatible, `PS2BBL.INI` configura **mantener R1 → OSDMenu**.

OSDMenu y los homebrews grandes se guardan en el almacenamiento de aplicaciones. `OSDMENU.CNF` se genera con rutas reales y versiones visibles. Las aplicaciones destinadas a OPL reciben también un `title.cfg` junto al mismo ELF para evitar duplicados.

## Modos útiles

```bash
python main.py --output /ruta/de/salida
python main.py --no-download
python main.py --no-package
python main.py --offline
python main.py --no-color
python main.py --no-clear
python -m unittest discover -s tests -v
```

Los colores también se desactivan automáticamente cuando la salida no es un terminal interactivo o cuando está definida la variable `NO_COLOR`.

## Seguridad

Ps2Installer solo genera archivos y carpetas; no escribe directamente en la PS2. Mantén copias de seguridad de Memory Cards importantes y lee las instrucciones generadas antes de reemplazar archivos de arranque.
