# Ps2Installer — English

[Main README](../README.md) · [Português (Brasil)](README.pt-BR.md) · [Español](README.es.md)

## What it is

Ps2Installer is a guided PlayStation 2 homebrew package builder. It automates release downloads, version selection, ELF organization and configuration generation for PS2BBL, OSDMenu and OPL.

## Requirements

- **Python 3.10+**;
- **Git** when cloning from a terminal;
- internet access for release detection and downloads.

Check your installation:

```bash
python --version
git --version
```

Use `python3` on systems where that is the Python command. On Windows, enable **Add Python to PATH** in the Python installer.

Git is optional if you use GitHub's **Code → Download ZIP** option.

## Install

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python main.py
```

You no longer need to pre-install `py7zr`. If a selected release uses `.7z`, Ps2Installer checks the dependency before downloading and automatically installs it with the same Python interpreter when necessary.

Manual fallback:

```bash
python -m pip install -r requirements.txt
```

## Interface

The terminal wizard includes:

- an ASCII Ps2Installer banner;
- colored titles, success messages, warnings and errors;
- screen clearing between major stages;
- short explanations before each setup choice;
- clear Stable, Beta/Prerelease and Development labels;
- a review screen before downloading;
- readable download/package progress.

The normal flow asks for language, output path, Memory Card/VMC type, application storage, optional homebrew, release channels, downloads and final package generation.

## Output

Press Enter to use `./output` or choose another writable folder. You can also specify it directly:

```bash
python main.py --output ~/PS2/Package
```

The selected output root contains `selection.json`, temporary downloads and `Ps2Installer_Package/`. The package separates the Memory Card/VMC contents from the application-storage contents and generates `README-COPY-HERE.txt` instructions for both.

## Boot/menu integration

PS2BBL stays on the Memory Card/VMC. When supported by the selected storage mode, generated `PS2BBL.INI` maps **hold R1 → OSDMenu**.

OSDMenu and larger homebrew live on the selected application storage. `OSDMENU.CNF` is generated with actual paths and visible versions. Apps intended for OPL also receive a `title.cfg` next to the same ELF so the file does not need to be duplicated.

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

Colors are also disabled automatically when output is not an interactive terminal or when the `NO_COLOR` environment variable is set.

## Safety

Ps2Installer only generates files and folders; it does not write directly to a PS2. Keep backups of important Memory Cards and read the generated instructions before replacing boot files.
