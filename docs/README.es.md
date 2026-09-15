# Ps2Installer — Español

[README principal](../README.md) · [Português (Brasil)](README.pt-BR.md) · [English](README.en.md)

## Qué es

Ps2Installer es un generador de paquetes/instalador para homebrew de PlayStation 2. Su objetivo es reducir el trabajo manual de copiar ELFs, mantener archivos de configuración y registrar la misma aplicación en distintos launchers.

El flujo previsto es:

```text
Memory Card
└── PS2BBL + configuración
        │
        └── mantener R1 → OSDMenu
                               │
Almacenamiento grande          │
└── APPS/ ◀────────────────────┘
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

**PS2BBL permanece en la Memory Card.** OSDMenu y la colección de homebrews más grande se guardan en el dispositivo elegido por el usuario, por ejemplo MMCE, MX4SIO, USB o HDD interno.

Siempre que sea posible, la misma biblioteca `APPS/` será compartida entre launchers. Así un mismo ELF podrá aparecer en OSDMenu y OPL sin mantener copias duplicadas.

## Estado actual

El proyecto se encuentra en su primera etapa de implementación. La versión actual es un **planificador interactivo**: pregunta qué Memory Card utiliza el usuario, dónde quiere guardar las aplicaciones y qué homebrews desea, y guarda el resultado en `output/selection.json`.

**Todavía no descarga, extrae ni copia archivos ELF.** Esto es intencional para evitar que el prototipo inicial se confunda con un instalador terminado.

## Requisitos

- Python 3.10 o más reciente recomendado;
- Git solamente si deseas clonar el repositorio desde una terminal;
- en esta etapa no se necesitan paquetes externos de Python.

## Instalación en PC

Clona el repositorio:

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
```

También puedes descargar el ZIP desde GitHub y extraerlo.

Ejecuta:

```bash
python main.py
```

En algunos sistemas:

```bash
python3 main.py
```

## Cómo usar el prototipo

Primero elige un idioma. Después el programa pregunta qué Memory Card utilizas, con opciones para una Memory Card estándar de PS2 y dispositivos compatibles con MMCE como SD2PSX, MemCard PRO2 y PSxMemCard Gen2.

Luego elige dónde deben almacenarse OSDMenu y los homebrews:

- MMCE;
- MX4SIO;
- USB;
- HDD interno exFAT;
- HDD interno APA/PFS.

Por último, el programa recorre el catálogo de homebrews. Los componentes obligatorios se incluyen automáticamente y las aplicaciones opcionales se seleccionan con preguntas `Y/N`.

Ejemplo:

```text
Open PS2 Loader (ask-stable-or-prerelease)
¿Instalar Open PS2 Loader? [Y/n]: y

wLaunchELF (development-build)
¿Instalar wLaunchELF? [Y/n]: y

SNESticleRevive (auto-detect)
¿Instalar SNESticleRevive? [y/N]: n
```

El resultado se guarda en:

```text
output/selection.json
```

Las siguientes etapas utilizarán ese plan para resolver versiones, descargar archivos y generar la estructura final para cada dispositivo.

## Versiones stable, beta y de desarrollo

Ps2Installer no debe llamar “última versión estable” a cualquier build reciente. Cada proyecto tendrá una política de canal en el catálogo.

Cuando existan distintos canales, el instalador deberá mostrar claramente la diferencia, por ejemplo:

```text
Open PS2 Loader

[1] Stable
[2] Beta / prerelease
```

Los proyectos que solo publiquen builds de desarrollo se mostrarán como tales. La versión detectada podrá aparecer también en las entradas generadas para OSDMenu, OPL y otros launchers compatibles.

## Integración con OPL

OPL permite organizar aplicaciones en subcarpetas dentro de `APPS/`, usando un archivo `title.cfg` junto al ELF. Por eso un paquete futuro generado por Ps2Installer podrá tener una estructura como:

```text
APPS/
└── SNESticleRevive/
    ├── SNESticle.elf
    └── title.cfg
```

Por ejemplo:

```ini
title=SNESticleRevive vX.Y.Z
boot=SNESticle.elf
```

La misma entrada del catálogo servirá para generar los metadatos de OPL y la entrada equivalente de OSDMenu, evitando configuración manual duplicada.

Proyecto/documentación de OPL: https://github.com/ps2homebrew/Open-PS2-Loader

## Estructura de salida prevista

El objetivo final es generar destinos claramente separados, por ejemplo:

```text
output/
├── 1_MEMORY_CARD/
│   ├── ... PS2BBL/configuración ...
│   └── README-COPY-TO-MEMORY-CARD.txt
│
└── 2_MX4SIO/
    ├── APPS/
    └── README-COPY-TO-MX4SIO.txt
```

La segunda carpeta cambiará según el almacenamiento seleccionado. Las instrucciones generadas deberán indicar claramente que se copia el **contenido** de cada carpeta de destino a la raíz del dispositivo correspondiente.

## PS2BBL y R1

El flujo previsto configurará PS2BBL para que **mantener R1 durante el arranque inicie OSDMenu**. La generación real de esa configuración se implementará más adelante y dependerá del tipo de Memory Card y del almacenamiento elegido.

Documentación de PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/

## OSDMenu

OSDMenu se mantendrá en el almacenamiento grande, evitando ocupar espacio innecesario en la Memory Card. Sus entradas se generarán a partir del mismo catálogo seleccionado por el usuario.

Proyecto oficial: https://github.com/pcm720/OSDMenu

## Seguridad

Haz una copia de seguridad del contenido importante de la Memory Card antes de probar paquetes que modifiquen archivos de arranque o configuración. Durante el desarrollo, revisa las carpetas generadas antes de copiarlas a hardware real.

## Próximas etapas

1. Detectar releases/tags/builds sin mezclar stable y prerelease.
2. Descargar y extraer assets de releases.
3. Implementar generadores para PS2BBL, OSDMenu y OPL.
4. Crear la estructura final según el almacenamiento elegido.
5. Generar READMEs específicos para cada dispositivo.
6. Ampliar el catálogo de homebrews.
