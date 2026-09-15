# Ps2Installer — English

[Main README](../README.md) · [Português (Brasil)](README.pt-BR.md) · [Español](README.es.md)

## What it is

Ps2Installer is a package builder/installer for PlayStation 2 homebrew. It is intended to automate version selection, downloads, configuration generation and organization of the same applications for multiple launchers.

Planned layout:

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

**PS2BBL stays on the Memory Card.** OSDMenu and larger homebrew files are intended to live on MMCE, MX4SIO, USB or HDD storage.

Whenever possible, Ps2Installer will share one `APPS/` library between launchers so the same ELF can be exposed through OSDMenu and OPL without duplicate copies.

## Current status

The prototype can already:

- ask for language, Memory Card type and application storage;
- query current releases directly from GitHub;
- keep **stable**, **beta/prerelease** and **development** builds separate;
- display the detected version before installation;
- offer optional homebrew through `Y/N` prompts;
- download the selected release asset;
- verify SHA-256 when GitHub publishes a digest;
- extract `.zip` and `.7z` packages and handle direct `.ELF` assets;
- find ELF candidates after extraction;
- save all resolved metadata to `output/selection.json`.

The final PS2 package generator is not implemented yet. PS2BBL configuration, `OSDMENU.CNF`, OPL `title.cfg`, device-specific output folders and generated copy instructions are the next stage.

## Requirements and installation

Python 3.10 or newer is recommended.

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

`py7zr` is used to extract `.7z` packages. ZIP and direct ELF handling use the Python standard library.

## How to use it

When `python main.py` starts, it asks:

1. which language to use;
2. which Memory Card type you have;
3. where OSDMenu and homebrew should be stored;
4. which optional homebrew you want;
5. which release channel to use when a project has more than one;
6. whether the selected assets should be downloaded immediately.

A multi-channel project can look like this:

```text
Open PS2 Loader
Available versions:
  - Stable: v1.x.x (stable)
  - Beta / prerelease: v1.x.x-Beta-xxxx (prerelease)

Install Open PS2 Loader? [Y/n]: y

Choose a channel for Open PS2 Loader
  [1] Stable: ...
  [2] Beta / prerelease: ... *
> 
```

The `*` marks the catalog's recommended channel; the user is still free to choose another one.

## Stable, beta and development builds

Ps2Installer does **not** assume that the newest build is stable.

Release rules live in `catalog/homebrews.json`. The initial catalog treats the projects roughly as follows:

- OSDMenu: stable release;
- Open PS2 Loader: stable and prerelease are separate choices;
- wLaunchELF: development build published through the `latest` release;
- SNESticleRevive: stable release.

If a project only publishes a generic tag such as `latest` and no useful version number is available, Ps2Installer uses a dated build identifier rather than pretending it is a stable semantic version.

## Downloads

Assets are currently stored under:

```text
output/downloads/
├── osdmenu/
├── opl/
├── wlaunchelf/
└── snesticlerevive/
```

Each application may contain:

```text
download/   original release asset
extracted/  extracted files or prepared ELF
```

Detected `.ELF` files are recorded so the future package generator can automatically place the correct binary under `APPS/<Application>/`.

## `selection.json`

`output/selection.json` records the installation plan, including:

- Memory Card and storage choices;
- selected applications;
- release channel and version;
- source tag/release;
- asset name and URL;
- download/extraction result;
- detected ELF candidates.

## Useful modes

Resolve versions but do not download files:

```bash
python main.py --no-download
```

Build a local plan without contacting GitHub:

```bash
python main.py --offline
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

If GitHub's unauthenticated API rate limit is reached, an optional `GITHUB_TOKEN` environment variable can be supplied.

## Planned PS2 output

A future generated package should look approximately like:

```text
output/
├── 1_MEMORY_CARD/
│   ├── PS2BBL / configuration
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

The second destination will be adapted automatically for MMCE, MX4SIO, USB, HDD exFAT or HDD APA/PFS.

The same catalog data will later generate OSDMenu entries and OPL `title.cfg` files, including the installed version in the visible title. PS2BBL will use **R1 as the OSDMenu shortcut**, while OSDMenu itself stays on the larger storage device.

## Related projects

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Safety

Until the final Memory Card package generator is finished, keep backups of important cards and inspect generated files before testing boot-related changes on real hardware.
