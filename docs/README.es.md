# Ps2Installer — Español

[README principal](../README.md) · [Português (Brasil)](README.pt-BR.md) · [English](README.en.md)

## Qué es

Ps2Installer es un generador de paquetes para homebrew de PlayStation 2. Automatiza la selección de releases, las descargas, la configuración de PS2BBL/OSDMenu y una biblioteca `APPS/` compartida por OSDMenu y OPL.

```text
Memory Card / VMC
├── BOOT/BOOT.ELF          <- PS2BBL
└── SYS-CONF/
    ├── PS2BBL.INI         <- mantener R1 -> OSDMenu
    └── OSDMENU.CNF

Almacenamiento grande
└── APPS/
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

## Requisitos

Antes de clonar y ejecutar Ps2Installer, instala:

- **Python 3.10 o posterior** — obligatorio para ejecutar el instalador: https://www.python.org/downloads/
- **Git** — necesario si vas a instalar el proyecto mediante `git clone`: https://git-scm.com/downloads
- conexión a Internet — utilizada para consultar y descargar los releases actuales de los homebrews.

En Windows, activa **Add Python to PATH** durante la instalación de Python. Después, verifica las herramientas con:

```bash
python --version
git --version
```

En sistemas donde Python se ejecuta como `python3`, usa:

```bash
python3 --version
```

Git no es obligatorio si descargas el repositorio mediante **Code > Download ZIP** en GitHub en lugar de clonarlo.

Después de clonar o extraer el ZIP, instala las dependencias Python:

```bash
python -m pip install -r requirements.txt
```

`py7zr`, utilizado para extraer releases `.7z`, se instala mediante este archivo de requisitos.

### Instalación con Git

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

## Uso

El flujo interactivo pregunta:

1. idioma;
2. **carpeta de salida**;
3. tipo de Memory Card;
4. almacenamiento de aplicaciones;
5. homebrews opcionales;
6. canal cuando existan stable/beta/development;
7. si debe descargar;
8. si debe generar el paquete final.

### Carpeta de salida

Pulsa Enter para usar `./output` o selecciona otra carpeta con permiso de escritura. Se aceptan rutas relativas y absolutas, y se expanden `~` y variables de entorno.

También puede indicarse directamente:

```bash
python main.py --output ~/PS2/Paquete
```

`selection.json`, las descargas y `Ps2Installer_Package/` se guardan bajo esa salida.

## Canales de versión

Ps2Installer **no supone que la build más nueva sea stable**. El catálogo define las reglas de stable, prerelease/beta y development, y el canal/versión seleccionado se incluye en los nombres visibles de los menús.

## Paquete generado

Para MemCard PRO2 + MX4SIO, por ejemplo:

```text
Ps2Installer_Package/
├── 1_MEMCARD_PRO2_VMC/
│   ├── BOOT/BOOT.ELF
│   ├── SYS-CONF/
│   │   ├── PS2BBL.INI
│   │   └── OSDMENU.CNF
│   └── README-COPY-HERE.txt
├── 2_MX4SIO/
│   ├── APPS/
│   │   ├── OSDMenu/
│   │   ├── OPL/
│   │   ├── wLaunchELF/
│   │   └── ...
│   └── README-COPY-HERE.txt
├── README.txt
└── manifest.json
```

Copia el **contenido** de cada carpeta de destino a la raíz correspondiente; no copies la carpeta externa `1_...`/`2_...` dentro del dispositivo.

## PS2BBL

El instalador descarga el paquete oficial actual de PS2BBL y elige automáticamente la variante necesaria:

- USB: `PS2`;
- MMCE: `PS2_MMCE`;
- MX4SIO: `PS2_MX4SIO`;
- HDD APA/PFS: `PS2_HDD`.

El binario elegido se copia como `BOOT/BOOT.ELF`. El `PS2BBL.INI` generado usa arranque normal -> OSDSYS y **mantener R1 -> OSDMenu**.

Copiar el ELF de PS2BBL a una Memory Card normal no instala por sí solo un exploit/autoboot; todavía se necesita un punto de entrada compatible con el setup del usuario.

### HDD interno exFAT

OSDMenu soporta `ata:` para HDD interno exFAT, pero las builds oficiales comunes de PS2BBL usadas actualmente no exponen el mismo camino de lanzamiento `ata:`. En ese modo Ps2Installer muestra una advertencia explícita y evita generar un destino R1 engañoso.

## OSDMenu y OPL

Se genera `SYS-CONF/OSDMENU.CNF` con las rutas reales y versiones visibles. Los apps que deben aparecer en OPL reciben además `title.cfg` junto al mismo ELF, evitando copias duplicadas.

```ini
title=SNESticleRevive v1.0.7
boot=SNESticle.elf
```

## Archivos de trabajo

La salida elegida contiene:

```text
selection.json

downloads/
  <app>/
    download/
    extracted/

Ps2Installer_Package/
```

## Modos útiles

```bash
python main.py --output /ruta/de/salida
python main.py --no-download
python main.py --no-package
python main.py --offline
python -m unittest discover -s tests -v
```

Puede usarse opcionalmente `GITHUB_TOKEN` si se alcanza el límite público de la API de GitHub.

## Proyectos relacionados

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Seguridad

Conserva copias de seguridad de Memory Cards importantes y lee las advertencias generadas antes de reemplazar archivos de arranque en hardware real.
