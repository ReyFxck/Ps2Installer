# Ps2Installer

> **Work in progress** — interactive installer/package builder for PlayStation 2 homebrew.

Ps2Installer automates a setup built around **PS2BBL + OSDMenu + a shared `APPS/` library**. It resolves current releases, keeps stable/beta/development channels distinct, downloads the selected binaries and builds device-specific folders ready to copy to a PS2 setup.

## 🌐 Documentation

- 🇧🇷 [Português (Brasil)](docs/README.pt-BR.md)
- 🇺🇸 [English](docs/README.en.md)
- 🇪🇸 [Español](docs/README.es.md)

## Requirements

- **Python 3.10+**;
- **Git** when cloning the repository from a terminal;
- internet access for release detection/downloads.

Check your installation:

```bash
python --version
git --version
```

On some systems use `python3` instead of `python`. On Windows, enable **Add Python to PATH** in the Python installer.

Git is not required if you use GitHub's **Code → Download ZIP** option.

## Install and run

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python main.py
```

The interactive wizard now provides:

- an ASCII Ps2Installer banner;
- ANSI colors for titles, success, warnings and errors;
- clean screens between major setup stages;
- short explanations before each choice;
- automatic detection and installation of `py7zr` when a selected release needs `.7z` extraction;
- clear Stable / Beta-Prerelease / Development labels;
- configurable output location;
- generated PS2 copy instructions.

If automatic dependency installation is unavailable on your system, the manual fallback is:

```bash
python -m pip install -r requirements.txt
```

## Layout

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

The same `APPS/` copy is reused by OSDMenu and, when applicable, OPL through generated `title.cfg` files.

## Output

The wizard asks whether to keep everything under `./output` or use a custom path. You can also specify it directly:

```bash
python main.py --output /path/to/output
```

The selected root contains:

```text
selection.json
downloads/
Ps2Installer_Package/
```

The generated package separates the Memory Card/VMC contents from the chosen application storage and includes README files explaining exactly what should be copied to each device root.

## Useful modes

```bash
python main.py --output /path/to/output
python main.py --no-download
python main.py --no-package
python main.py --offline
python main.py --no-color
python main.py --no-clear
python -m unittest discover -s tests -v
```

Colors are automatically disabled when the terminal is not interactive or when the `NO_COLOR` environment variable is set.

## Upstream projects

Ps2Installer integrates with existing projects rather than replacing them:

- [PS2BBL](https://israpps.github.io/PlayStation2-Basic-BootLoader/)
- [OSDMenu](https://github.com/pcm720/OSDMenu)
- [Open PS2 Loader](https://github.com/ps2homebrew/Open-PS2-Loader)
- [wLaunchELF](https://github.com/ps2homebrew/wLaunchELF)

---

Ps2Installer is an independent community project and is not affiliated with Sony Interactive Entertainment.
