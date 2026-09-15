# Ps2Installer

> **Work in progress** — interactive installer/package builder for PlayStation 2 homebrew.

Ps2Installer automates a setup built around **PS2BBL + OSDMenu + a shared `APPS/` library**. It resolves current releases, keeps stable/beta/development channels distinct, downloads the selected binaries and builds device-specific folders that can be copied to the PS2 setup.

## 🌐 Documentation

- 🇧🇷 [Português (Brasil)](docs/README.pt-BR.md)
- 🇺🇸 [English](docs/README.en.md)
- 🇪🇸 [Español](docs/README.es.md)

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

The same `APPS/` copy is used by OSDMenu and, when applicable, OPL through generated `title.cfg` files.

## Current status

The current prototype already:

- asks for language, **output folder**, Memory Card type and application storage;
- lets the user keep output in `./output` or choose any writable custom folder;
- supports `--output PATH` for a non-interactive output location;
- resolves releases directly from GitHub;
- keeps **stable, beta/prerelease and development** builds distinct;
- downloads assets, verifies SHA-256 when available and extracts `.zip` / `.7z` / direct `.ELF` files;
- downloads the official PS2BBL package and selects its `PS2`, `PS2_MMCE`, `PS2_MX4SIO` or `PS2_HDD` variant according to the selected storage;
- generates `PS2BBL.INI` with **R1 -> OSDMenu** and normal boot returning to OSDSYS;
- generates `OSDMENU.CNF` with visible application versions;
- generates OPL `title.cfg` files from the same catalog;
- generates separate Memory Card/VMC and application-storage folders plus copy instructions;
- records the full result in `selection.json` and `Ps2Installer_Package/manifest.json`.

Internal HDD exFAT (`ata:`) is currently packaged for OSDMenu/APPS, but the official upstream PS2BBL common builds do not provide the matching `ata:` launch path. Ps2Installer therefore emits an explicit warning instead of silently producing a broken R1 boot setup for that mode.

## Run

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

Python **3.10+** is recommended.

Useful modes:

```bash
python main.py --output /path/to/package-output
python main.py --no-download
python main.py --no-package
python main.py --offline
python -m unittest discover -s tests -v
```

`py7zr` is used for `.7z` extraction. ZIP and direct ELF handling use the Python standard library.

If the unauthenticated GitHub API rate limit is reached, an optional `GITHUB_TOKEN` environment variable can be supplied.

## Upstream projects

Ps2Installer integrates with existing projects rather than replacing them:

- [PS2BBL](https://israpps.github.io/PlayStation2-Basic-BootLoader/)
- [OSDMenu](https://github.com/pcm720/OSDMenu)
- [Open PS2 Loader](https://github.com/ps2homebrew/Open-PS2-Loader)
- [wLaunchELF](https://github.com/ps2homebrew/wLaunchELF)

---

Ps2Installer is an independent community project and is not affiliated with Sony Interactive Entertainment.
