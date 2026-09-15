# Ps2Installer — Português (Brasil)

[README principal](../README.md) · [English](README.en.md) · [Español](README.es.md)

## O que é

Ps2Installer é um instalador/gerador de pacote para homebrews de PlayStation 2. A ideia é reduzir a instalação manual de ELFs, arquivos de configuração e entradas de menu.

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

O **PS2BBL fica no Memory Card**. O OSDMenu e os homebrews, que ocupam mais espaço, ficam no armazenamento escolhido pelo usuário, como MMCE, MX4SIO, USB ou HDD.

A biblioteca `APPS/` será compartilhada sempre que possível. Assim, o mesmo ELF poderá aparecer no OSDMenu e também na lista de aplicativos do OPL sem manter cópias duplicadas.

## Estado atual

O projeto está no começo. A versão atual é um **planejador interativo**: pergunta o hardware, o armazenamento e quais homebrews o usuário quer, e salva as escolhas em `output/selection.json`.

**Ainda não baixa, extrai nem copia ELFs.** Isso será implementado na próxima etapa. O aviso existe para evitar que alguém trate o protótipo atual como um instalador pronto para uso no console.

## Requisitos

- Python 3.10 ou mais recente recomendado;
- Git, apenas se você quiser clonar o repositório pelo terminal;
- nenhuma biblioteca Python externa é necessária nesta etapa.

## Instalação no PC

Clone o repositório:

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
```

Ou baixe o ZIP do repositório pelo GitHub e extraia-o em qualquer pasta.

Execute:

```bash
python main.py
```

Em alguns sistemas o comando pode ser:

```bash
python3 main.py
```

## Como usar o protótipo

Ao iniciar, escolha o idioma. Em seguida, o programa pergunta qual Memory Card você utiliza, por exemplo:

- Memory Card padrão / MagicGate compatível;
- SD2PSX;
- MemCard PRO2;
- PSxMemCard Gen2;
- outro Memory Card compatível com MMCE.

Depois escolha onde o OSDMenu e os homebrews devem ficar:

- MMCE;
- MX4SIO;
- USB;
- HDD interno exFAT;
- HDD interno APA/PFS.

Por fim, o programa passa pelo catálogo de homebrews. Componentes obrigatórios são incluídos automaticamente; aplicativos opcionais usam perguntas `Y/N`.

Exemplo:

```text
Open PS2 Loader (ask-stable-or-prerelease)
Instalar Open PS2 Loader? [Y/n]: y

wLaunchELF (development-build)
Instalar wLaunchELF? [Y/n]: y

SNESticleRevive (auto-detect)
Instalar SNESticleRevive? [y/N]: n
```

As escolhas são gravadas em:

```text
output/selection.json
```

Esse arquivo será usado pelas próximas etapas do projeto para baixar versões, montar configurações e gerar as pastas finais.

## Stable, beta e builds de desenvolvimento

Ps2Installer não deve simplesmente chamar qualquer build mais recente de “última versão”. O catálogo guarda uma política por projeto.

Quando um projeto oferecer canais diferentes, o instalador deverá deixar isso explícito, por exemplo:

```text
Open PS2 Loader

[1] Stable
[2] Beta / prerelease
```

Projetos que só publicam builds de desenvolvimento serão mostrados como tal. A versão real deverá ser detectada da fonte original e também poderá aparecer no nome gerado para OSDMenu, OPL e outros launchers compatíveis.

## Integração com OPL

O OPL suporta aplicativos organizados em subpastas de `APPS/` com um `title.cfg` ao lado do ELF. Um pacote futuro gerado pelo Ps2Installer poderá ficar assim:

```text
APPS/
└── SNESticleRevive/
    ├── SNESticle.elf
    └── title.cfg
```

Com um arquivo semelhante a:

```ini
title=SNESticleRevive vX.Y.Z
boot=SNESticle.elf
```

O gerador usará o mesmo catálogo para criar tanto o `title.cfg` quanto a entrada correspondente do OSDMenu, evitando cadastro manual duplicado.

Documentação do OPL: https://github.com/ps2homebrew/Open-PS2-Loader

## Saída final planejada

O objetivo é gerar pastas com nomes difíceis de confundir, por exemplo:

```text
output/
├── 1_MEMORY_CARD/
│   ├── ... PS2BBL/configuração ...
│   └── README-COPY-TO-MEMORY-CARD.txt
│
└── 2_MX4SIO/
    ├── APPS/
    └── README-COPY-TO-MX4SIO.txt
```

Se o usuário escolher outro dispositivo, a segunda pasta será adaptada para ele. O README gerado também deverá explicar exatamente **o conteúdo que deve ser copiado para a raiz de cada dispositivo**, para evitar caminhos incorretos como `mc0:/1_MEMORY_CARD/...`.

## PS2BBL e R1

O fluxo planejado configura o PS2BBL para chamar o OSDMenu ao **segurar R1 durante a inicialização**. A geração real do arquivo de configuração ainda será implementada e será adaptada ao tipo de Memory Card e armazenamento escolhidos.

Documentação do PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/

## OSDMenu

O OSDMenu será mantido no armazenamento maior, não no Memory Card, e seu catálogo será gerado a partir dos mesmos homebrews selecionados pelo usuário.

Projeto oficial: https://github.com/pcm720/OSDMenu

## Segurança

Antes de testar pacotes que alterem arquivos de boot ou configuração do Memory Card, mantenha backup do conteúdo importante. Durante o desenvolvimento, revise a árvore gerada antes de copiá-la para um console real.

## Próximas etapas

1. Detectar releases/tags/builds sem misturar stable e prerelease.
2. Baixar e extrair assets de releases.
3. Implementar geradores específicos para PS2BBL, OSDMenu e OPL.
4. Criar a árvore final de saída por dispositivo.
5. Gerar READMEs personalizados para a instalação no PS2.
6. Expandir o catálogo de homebrews.
