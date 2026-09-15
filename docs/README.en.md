# Ps2Installer — English

[Main README](../README.md) · [Português (Brasil)](README.pt-BR.md) · [Español](README.es.md)

## What it is

Ps2Installer is a package builder/installer for PlayStation 2 homebrew. Its goal is to reduce the manual work involved in copying ELFs, maintaining configuration files and registering the same application in multiple launchers.

The planned flow is:

```text
Memory Card
└── PS2BBL + configuration
        │
        └── hold R1 → OSDMenu
                           │
Large storage              │
└── APPS/ ◀────────────────┘
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

**PS2BBL stays on the Memory Card.** OSDMenu and the larger homebrew collection live on the storage selected by the user, such as MMCE, MX4SIO, USB or an internal HDD.

Whenever possible, the same `APPS/` library will be shared between launchers. This allows one ELF to be exposed through OSDMenu and OPL without storing duplicate copies.

## Current status

The project is in its first implementation stage. The current version is an **interactive setup planner**: it asks about the user's Memory Card, application storage and desired homebrew, then writes the result to `output/selection.json`.

**It does not download, extract or copy ELF binaries yet.** This is intentional so the early prototype cannot be mistaken for a finished PS2 installer.

## Requirements

- Python 3.10 or newer is recommended;
- Git is only required if you want to clone from a terminal;
- no third-party Python packages are required at this stage.

## PC installation

Clone the repository:

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
```

Alternatively, download the repository ZIP from GitHub and extract it.

Run:

```bash
python main.py
```

On some systems use:

```bash
python3 main.py
```

## Using the current prototype

First choose a language. The program then asks which Memory Card is being used, including options for a standard PS2 Memory Card and MMCE-capable devices such as SD2PSX, MemCard PRO2 and PSxMemCard Gen2.

Next choose where OSDMenu and the homebrew collection should be stored:

- MMCE;
- MX4SIO;
- USB;
- internal HDD using exFAT;
- internal HDD using APA/PFS.

Finally, the installer walks through the homebrew catalog. Required components are included automatically; optional applications are selected with `Y/N` prompts.

Example:

```text
Open PS2 Loader (ask-stable-or-prerelease)
Install Open PS2 Loader? [Y/n]: y

wLaunchELF (development-build)
Install wLaunchELF? [Y/n]: y

SNESticleRevive (auto-detect)
Install SNESticleRevive? [y/N]: n
```

The result is saved to:

```text
output/selection.json
```

Later milestones will consume this plan to resolve versions, download files and generate the final device layout.

## Stable, beta and development builds

Ps2Installer should not label every newest build as “latest stable”. Each catalog entry has a channel policy.

When a project publishes multiple channels, the installer is intended to make the distinction explicit, for example:

```text
Open PS2 Loader

[1] Stable
[2] Beta / prerelease
```

Projects that only provide development builds will be identified as development builds. The detected version can then be included in generated OSDMenu, OPL and other supported launcher entries.

## OPL integration

OPL supports applications stored in individual directories under `APPS/`, with a `title.cfg` next to the ELF. A future Ps2Installer package can therefore use a structure such as:

```text
APPS/
└── SNESticleRevive/
    ├── SNESticle.elf
    └── title.cfg
```

For example:

```ini
title=SNESticleRevive vX.Y.Z
boot=SNESticle.elf
```

The same catalog entry will be used to generate both the OPL metadata and the matching OSDMenu entry, avoiding duplicate manual configuration.

OPL documentation/project: https://github.com/ps2homebrew/Open-PS2-Loader

## Planned output layout

The final generator is intended to create clearly separated destinations, for example:

```text
output/
├── 1_MEMORY_CARD/
│   ├── ... PS2BBL/configuration ...
│   └── README-COPY-TO-MEMORY-CARD.txt
│
└── 2_MX4SIO/
    ├── APPS/
    └── README-COPY-TO-MX4SIO.txt
```

The second directory will change according to the selected storage. Generated instructions should clearly state that the **contents** of each destination directory belong at the root of the corresponding PS2 device.

## PS2BBL and R1

The planned boot flow configures PS2BBL so **holding R1 during startup launches OSDMenu**. Actual configuration generation will be implemented in a later milestone and will depend on the selected Memory Card and application storage.

PS2BBL documentation: https://israpps.github.io/PlayStation2-Basic-BootLoader/

## OSDMenu

OSDMenu is intended to stay on the larger application storage instead of consuming Memory Card space. Its menu entries will be generated from the same selected-homebrew catalog.

Official project: https://github.com/pcm720/OSDMenu

## Safety

Back up important Memory Card contents before testing packages that modify boot or configuration files. During development, inspect generated directory trees before copying them to real hardware.

## Roadmap

1. Resolve releases/tags/builds without mixing stable and prerelease channels.
2. Download and extract release assets.
3. Implement PS2BBL, OSDMenu and OPL generators.
4. Build the final output tree for each storage type.
5. Generate device-specific installation READMEs.
6. Expand the homebrew catalog.
