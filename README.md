# Ps2Installer

> **Work in progress** — an interactive installer/package builder for PlayStation 2 homebrew.

Ps2Installer aims to automate a setup built around **PS2BBL + OSDMenu + a shared `APPS/` library**, so the same homebrew collection can be exposed to OSDMenu, Open PS2 Loader and, later, other supported launchers without manually rebuilding configuration files.

## 🌐 Documentation

Choose your language:

- 🇧🇷 [Português (Brasil)](docs/README.pt-BR.md)
- 🇺🇸 [English](docs/README.en.md)
- 🇪🇸 [Español](docs/README.es.md)

## What is planned?

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

The installer is being designed to:

- ask what kind of Memory Card is being used;
- ask where OSDMenu and homebrew should live (MMCE, MX4SIO, USB, HDD, etc.);
- prepare PS2BBL so **holding R1 launches OSDMenu**;
- offer homebrew one by one with `Y/N` selection;
- distinguish stable, beta/prerelease and development builds instead of calling everything “latest”;
- keep version information in generated menu entries;
- generate OSDMenu entries and OPL `title.cfg` files from the same catalog;
- create clearly separated output folders and copy instructions for each PS2 device.

## Current status

The repository is at the initial implementation stage. The first CLI is intentionally a **setup planner**: it records the user's Memory Card, storage and homebrew choices while the downloader/package generator is implemented next.

### Run the current prototype

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python main.py
```

Python **3.10+** is recommended. The current prototype uses only the Python standard library.

## Upstream projects

Ps2Installer integrates with existing PS2 homebrew rather than replacing it. Relevant upstream projects include [PS2BBL](https://israpps.github.io/PlayStation2-Basic-BootLoader/), [OSDMenu](https://github.com/pcm720/OSDMenu) and [Open PS2 Loader](https://github.com/ps2homebrew/Open-PS2-Loader).

---

Ps2Installer is an independent community project and is not affiliated with Sony Interactive Entertainment.