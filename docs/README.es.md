# Ps2Installer — Español

[README principal](../README.md) · [Português (Brasil)](README.pt-BR.md) · [English](README.en.md)

## Qué es

Ps2Installer es un instalador/generador de paquetes para homebrew de PlayStation 2. Su objetivo es automatizar la selección de versiones, descargas, configuración y organización de las mismas aplicaciones para diferentes launchers.

Flujo previsto:

```text
Memory Card
└── PS2BBL + configuración
        │
        └── mantener R1 → OSDMenu
                                │
Almacenamiento grande           │
└── APPS/ ◀─────────────────────┘
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

**PS2BBL permanece en la Memory Card.** OSDMenu y los homebrews más grandes están pensados para MMCE, MX4SIO, USB o HDD.

Siempre que sea posible, Ps2Installer compartirá una sola biblioteca `APPS/` entre launchers para que el mismo ELF pueda aparecer en OSDMenu y OPL sin copias duplicadas.

## Estado actual

El prototipo ya puede:

- preguntar idioma, tipo de Memory Card y almacenamiento de aplicaciones;
- consultar releases actuales directamente desde GitHub;
- separar correctamente **stable**, **beta/prerelease** y **development**;
- mostrar la versión detectada antes de instalar;
- preguntar `Y/N` por cada homebrew opcional;
- descargar el asset seleccionado;
- verificar SHA-256 cuando GitHub publica el digest;
- extraer `.zip` y `.7z` y manejar assets `.ELF` directos;
- localizar candidatos ELF después de la extracción;
- guardar todos los datos resueltos en `output/selection.json`.

Todavía falta el generador final para PS2: configuración de PS2BBL, `OSDMENU.CNF`, `title.cfg` de OPL, carpetas finales por dispositivo e instrucciones automáticas de copia.

## Requisitos e instalación

Se recomienda Python 3.10 o posterior.

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

`py7zr` se utiliza para extraer paquetes `.7z`. ZIP y ELF directos se manejan con la biblioteca estándar de Python.

## Cómo usarlo

Al ejecutar `python main.py`, el programa pregunta:

1. idioma;
2. tipo de Memory Card;
3. dónde guardar OSDMenu y los homebrews;
4. qué homebrews opcionales instalar;
5. qué canal usar cuando un proyecto tenga varias opciones;
6. si debe descargar ahora los archivos seleccionados.

Un proyecto con varios canales puede verse así:

```text
Open PS2 Loader
Versiones disponibles:
  - Stable: v1.x.x (stable)
  - Beta / prerelease: v1.x.x-Beta-xxxx (prerelease)

¿Instalar Open PS2 Loader? [Y/n]: y

Elige un canal para Open PS2 Loader
  [1] Stable: ...
  [2] Beta / prerelease: ... *
> 
```

El `*` indica el canal recomendado por el catálogo, pero el usuario puede elegir otro.

## Stable, beta y development

Ps2Installer **no supone que la build más nueva sea estable**.

Las reglas están en `catalog/homebrews.json`. El catálogo inicial trata los proyectos de esta forma:

- OSDMenu: release stable;
- Open PS2 Loader: stable y prerelease como opciones separadas;
- wLaunchELF: build de desarrollo publicada mediante `latest`;
- SNESticleRevive: release stable.

Si un proyecto solo publica una etiqueta genérica como `latest` y no ofrece un número de versión útil, Ps2Installer usa un identificador de build basado en la fecha en lugar de inventar una versión estable.

## Descargas

Los assets se almacenan actualmente en:

```text
output/downloads/
├── osdmenu/
├── opl/
├── wlaunchelf/
└── snesticlerevive/
```

Cada aplicación puede contener:

```text
download/   asset original del release
extracted/  archivos extraídos o ELF preparado
```

Los `.ELF` encontrados quedan registrados para que el futuro generador pueda colocarlos automáticamente en `APPS/<Aplicación>/`.

## `selection.json`

`output/selection.json` guarda el plan de instalación:

- Memory Card y almacenamiento elegidos;
- aplicaciones seleccionadas;
- canal y versión;
- tag/release de origen;
- nombre y URL del asset;
- resultado de descarga/extracción;
- candidatos ELF detectados.

## Modos útiles

Resolver versiones sin descargar:

```bash
python main.py --no-download
```

Crear un plan local sin consultar GitHub:

```bash
python main.py --offline
```

Ejecutar pruebas:

```bash
python -m unittest discover -s tests -v
```

Si se alcanza el límite de la API pública de GitHub, puede configurarse opcionalmente la variable de entorno `GITHUB_TOKEN`.

## Salida PS2 planificada

El paquete final debería tener una estructura similar a:

```text
output/
├── 1_MEMORY_CARD/
│   ├── PS2BBL / configuración
│   ├── SYS-CONF/
│   └── README-COPY-TO-MEMORY-CARD.txt
│
└── 2_MX4SIO/
    ├── APPS/
    │   ├── OSDMenu/
    │   ├── OPL/
    │   ├── wLaunchELF/
    │   └── ...
    └── README-COPY-TO-MX4SIO.txt
```

El segundo destino se adaptará automáticamente a MMCE, MX4SIO, USB, HDD exFAT o HDD APA/PFS.

Los mismos datos del catálogo generarán más adelante las entradas de OSDMenu y los `title.cfg` de OPL, incluyendo la versión instalada en el nombre visible. PS2BBL utilizará **R1 como acceso directo a OSDMenu**, mientras OSDMenu permanece en el almacenamiento grande.

## Proyectos relacionados

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Seguridad

Hasta que el generador final para Memory Card esté terminado, conserva copias de seguridad de tarjetas importantes y revisa los archivos generados antes de probar cambios de arranque en hardware real.
