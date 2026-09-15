# Ps2Installer

> **Work in progress** — interactive installer/package builder for PlayStation 2 homebrew.

Ps2Installer is being built around **PS2BBL + OSDMenu + a shared `APPS/` library**. The goal is to automate release selection, downloading, configuration and installation so the same homebrew collection can later be exposed to OSDMenu, Open PS2 Loader and other compatible launchers.

## 🌐 Documentation

- 🇧🇷 [Português (Brasil)](docs/README.pt-BR.md)
- 🇺🇸 [English](docs/README.en.md)
- 🇪🇸 [Español](docs/README.es.md)

## Planned PS2 layout

```text
Memory Card
└── PS2BBL + configuration
        │
        └── Hold R1 → OSDMenu
                         │
Large storage            │
└── APPS/ ◀──────────────┘
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

**PS2BBL belongs on the Memory Card.** OSDMenu and larger homebrew files are intended to live on MMCE, MX4SIO, USB or HDD storage.

## Current status

The current prototype already:

- asks for language, Memory Card type and application storage;
- resolves current releases directly from GitHub;
- keeps **stable, prerelease/beta and development** builds distinct;
- displays the detected version before installation;
- offers optional homebrew with `Y/N` prompts;
- downloads selected release assets;
- verifies SHA-256 when GitHub publishes a digest;
- extracts `.zip`, direct `.ELF` and `.7z` assets;
- records resolved versions, channels, assets and ELF candidates in `output/selection.json`.

Still to be implemented: final PS2 package generation, PS2BBL configuration, OSDMenu `OSDMENU.CNF`, OPL `title.cfg`, device-specific output folders and generated installation instructions.

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
python main.py --no-download
python main.py --offline
python -m unittest discover -s tests -v
```

`py7zr` is used for `.7z` extraction (for example, some OPL stable packages). ZIP and direct ELF handling use the Python standard library.

If the unauthenticated GitHub API rate limit is reached, an optional `GITHUB_TOKEN` environment variable can be supplied.

## Upstream projects

Ps2Installer integrates with existing projects rather than replacing them:

- [PS2BBL](https://israpps.github.io/PlayStation2-Basic-BootLoader/)
- [OSDMenu](https://github.com/pcm720/OSDMenu)
- [Open PS2 Loader](https://github.com/ps2homebrew/Open-PS2-Loader)
- [wLaunchELF](https://github.com/ps2homebrew/wLaunchELF)

---

Ps2Installer is an independent community project and is not affiliated with Sony Interactive Entertainment.
