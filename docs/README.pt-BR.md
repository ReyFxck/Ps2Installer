# Ps2Installer — Português (Brasil)

[README principal](../README.md) · [English](README.en.md) · [Español](README.es.md)

## O que é

Ps2Installer é um instalador/gerador de pacote para homebrews de PlayStation 2. A proposta é automatizar o trabalho de escolher versões, baixar ELFs, montar configurações e organizar os mesmos aplicativos para diferentes launchers.

O fluxo planejado é:

```text
Memory Card
└── PS2BBL + configurações
        │
        └── segurar R1 → OSDMenu
                              │
Armazenamento maior           │
└── APPS/ ◀───────────────────┘
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

O **PS2BBL fica no Memory Card**. O OSDMenu e os homebrews maiores devem ficar no armazenamento escolhido pelo usuário, como MMCE, MX4SIO, USB ou HDD.

A meta é compartilhar uma única biblioteca `APPS/` sempre que possível. Assim, o mesmo ELF poderá aparecer no OSDMenu e no menu de APPS do OPL sem manter cópias duplicadas.

## Estado atual

O protótipo já consegue:

- perguntar idioma, tipo de Memory Card e armazenamento dos aplicativos;
- consultar os releases atuais diretamente no GitHub;
- separar corretamente **stable**, **beta/prerelease** e **development**;
- mostrar a versão encontrada antes da instalação;
- perguntar `Y/N` para cada homebrew opcional;
- baixar o asset correto do release escolhido;
- verificar SHA-256 quando o GitHub fornece o digest;
- extrair `.zip`, `.7z` e trabalhar com `.ELF` direto;
- procurar ELFs dentro dos pacotes extraídos;
- registrar tudo em `output/selection.json`.

Ainda falta gerar o pacote final para o PS2: configuração do PS2BBL, `OSDMENU.CNF`, `title.cfg`, árvores separadas para cada dispositivo e READMEs finais de cópia.

## Requisitos

- Python 3.10 ou mais recente recomendado;
- conexão com a internet para detectar e baixar releases;
- `py7zr` para extrair pacotes `.7z`.

Instale a dependência com:

```bash
python -m pip install -r requirements.txt
```

ZIPs e ELFs diretos são tratados pela biblioteca padrão do Python. O `py7zr` é necessário principalmente para projetos que distribuem certas versões apenas em `.7z`, como o OPL stable atual.

## Instalação no PC

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

Em alguns sistemas o executável pode ser `python3`.

## Como usar

Ao executar `python main.py`, o instalador primeiro pergunta o idioma e depois:

1. qual tipo de Memory Card você usa;
2. onde OSDMenu e os homebrews devem ficar;
3. quais homebrews você quer instalar;
4. quando existir mais de um canal, qual versão/canal deve ser usado;
5. se os arquivos selecionados devem ser baixados agora.

Exemplo do comportamento esperado para um projeto com mais de um canal:

```text
Open PS2 Loader
Versões disponíveis:
  - Stable: v1.x.x (stable)
  - Beta / prerelease: v1.x.x-Beta-xxxx (prerelease)

Instalar Open PS2 Loader? [Y/n]: y

Escolha o canal para Open PS2 Loader
  [1] Stable: ...
  [2] Beta / prerelease: ... *
> 
```

O `*` indica o canal recomendado pelo catálogo, mas o usuário continua podendo escolher o outro.

## Stable, beta e development

O Ps2Installer **não considera automaticamente a build mais nova como stable**.

Cada projeto possui regras no `catalog/homebrews.json`. Por exemplo:

- OSDMenu: release stable;
- OPL: oferece stable e prerelease separadamente;
- wLaunchELF: build de desenvolvimento publicada como `latest`;
- SNESticleRevive: release stable.

Quando um projeto usa uma tag genérica como `latest` e não publica um número de versão útil, o instalador usa uma identificação de build baseada na data, em vez de inventar uma versão estável.

## Downloads

Os downloads ficam temporariamente organizados em:

```text
output/downloads/
├── osdmenu/
├── opl/
├── wlaunchelf/
└── snesticlerevive/
```

Cada aplicativo pode conter:

```text
download/   arquivo original do release
extracted/  conteúdo extraído ou ELF preparado
```

O instalador também registra os candidatos `.ELF` encontrados. Essa informação será usada na próxima etapa para montar automaticamente `APPS/<Aplicativo>/`.

## Arquivo `selection.json`

O arquivo:

```text
output/selection.json
```

registra:

- Memory Card escolhido;
- armazenamento escolhido;
- aplicativos selecionados;
- canal de cada aplicativo;
- versão detectada;
- tag/release de origem;
- nome e URL do asset;
- resultado do download;
- ELFs encontrados após a extração.

Ele funciona como o plano de instalação para as próximas etapas do gerador.

## Modos úteis

Resolver as versões e criar o plano, mas não baixar:

```bash
python main.py --no-download
```

Criar apenas um plano local sem consultar GitHub:

```bash
python main.py --offline
```

Executar os testes:

```bash
python -m unittest discover -s tests -v
```

Se o limite da API pública do GitHub for atingido, você pode definir opcionalmente a variável de ambiente `GITHUB_TOKEN` antes de executar o instalador.

## O que será gerado no PS2

A meta da próxima fase é produzir algo semelhante a:

```text
output/
├── 1_MEMORY_CARD/
│   ├── PS2BBL / configuração
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

A segunda pasta será adaptada automaticamente para MMCE, MX4SIO, USB, HDD exFAT ou HDD APA/PFS.

## Integração planejada com OSDMenu e OPL

Do mesmo item do catálogo deverão sair as duas configurações.

Exemplo para OPL:

```ini
title=SNESticleRevive vX.Y.Z
boot=SNESticle.elf
```

E a versão correspondente será usada no nome da entrada do OSDMenu. Dessa forma, o usuário poderá enxergar a versão instalada diretamente no menu.

O PS2BBL será configurado para usar **R1 como atalho para o OSDMenu**, mantendo o PS2BBL no Memory Card e o OSDMenu no armazenamento maior.

## Projetos relacionados

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Segurança

Enquanto o gerador final de Memory Card ainda estiver em desenvolvimento, não copie arquivos de boot experimentalmente sobre um cartão importante sem backup. Revise a árvore gerada antes de testar no hardware real.
