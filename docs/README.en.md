# Ps2Installer — English

[Main README](../README.md) · [Português (Brasil)](README.pt-BR.md) · [Español](README.es.md)

## What it is

Ps2Installer is a PlayStation 2 homebrew package builder. It automates release selection, downloads, PS2BBL/OSDMenu configuration and organization of a shared `APPS/` tree for OSDMenu and OPL.

```text
Memory Card / VMC
├── BOOT/BOOT.ELF          <- PS2BBL
└── SYS-CONF/
    ├── PS2BBL.INI         <- hold R1 -> OSDMenu
    └── OSDMENU.CNF

Large storage
└── APPS/
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

## Requirements

Python 3.10 or newer is recommended. `.7z` extraction uses `py7zr`.

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

## Usage

The interactive flow asks for:

1. language;
2. **output folder**;
3. Memory Card type;
4. application storage;
5. optional homebrew;
6. release channel when stable/beta/development choices exist;
7. whether to download;
8. whether to generate the final package.

### Output folder

Press Enter to keep everything in `./output`, or select a custom writable folder. Relative and absolute paths are accepted; `~` and environment variables are expanded.

You can also bypass the question:

```bash
python main.py --output ~/PS2/Package
```

`selection.json`, release downloads and `Ps2Installer_Package/` all use the selected output root.

## Release channels

Ps2Installer does **not** assume the newest build is stable. The catalog defines stable, prerelease/beta and development policies per project, and the selected channel/version is carried into generated menu names.

## Generated package

For a MemCard PRO2 + MX4SIO setup, the output is similar to:

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

Copy the **contents** of each destination folder to the corresponding device root; do not copy the outer `1_...`/`2_...` folder itself.

## PS2BBL

The installer downloads the current official PS2BBL package and selects the required variant automatically:

- USB: `PS2`;
- MMCE: `PS2_MMCE`;
- MX4SIO: `PS2_MX4SIO`;
- APA/PFS HDD: `PS2_HDD`.

The selected binary is copied as `BOOT/BOOT.ELF`. Generated `PS2BBL.INI` uses normal boot -> OSDSYS and **hold R1 -> OSDMenu**.

Copying a PS2BBL ELF to a normal Memory Card does not by itself install an exploit/autoboot. A compatible entry point for the user's setup is still required.

### Internal exFAT HDD

OSDMenu supports `ata:` for an internal exFAT HDD, but the official upstream PS2BBL common builds currently used by Ps2Installer do not expose the matching `ata:` application launch path. In that mode the package generator emits an explicit warning and avoids writing a misleading R1 target.

## OSDMenu and OPL

`SYS-CONF/OSDMENU.CNF` is generated with the real device paths and visible versions. Apps intended for OPL also receive a `title.cfg` beside the same ELF, so no duplicate ELF copy is needed.

Example OPL metadata:

```ini
title=SNESticleRevive v1.0.7
boot=SNESticle.elf
```

## Working files

The selected output root contains:

```text
selection.json

downloads/
  <app>/
    download/
    extracted/

Ps2Installer_Package/
```

## Useful modes

```bash
python main.py --output /path/to/output
python main.py --no-download
python main.py --no-package
python main.py --offline
python -m unittest discover -s tests -v
```

An optional `GITHUB_TOKEN` environment variable can be supplied if the unauthenticated GitHub API rate limit is reached.

## Related projects

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Safety

Keep backups of important Memory Cards and read the generated package warnings before replacing boot-related files on real hardware.
