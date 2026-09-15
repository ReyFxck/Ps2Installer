# Ps2Installer — Português (Brasil)

[README principal](../README.md) · [English](README.en.md) · [Español](README.es.md)

## O que é

Ps2Installer é um instalador/gerador de pacote para homebrews de PlayStation 2. Ele automatiza a escolha de versões, download dos releases, configuração do PS2BBL/OSDMenu e organização dos ELFs para que a mesma pasta `APPS/` possa ser usada pelo OSDMenu e pelo OPL.

```text
Memory Card / VMC
├── BOOT/BOOT.ELF          <- PS2BBL
└── SYS-CONF/
    ├── PS2BBL.INI         <- segurar R1 -> OSDMenu
    └── OSDMENU.CNF

Armazenamento maior
└── APPS/
    ├── OSDMenu/
    ├── OPL/
    ├── wLaunchELF/
    ├── SNESticleRevive/
    └── ...
```

O **PS2BBL fica no Memory Card/VMC**. O OSDMenu e os homebrews maiores ficam no armazenamento escolhido, como MMCE, MX4SIO, USB ou HDD.

## Requisitos

Antes de clonar e executar o Ps2Installer, instale:

- **Python 3.10 ou mais recente** — obrigatório para executar o instalador: https://www.python.org/downloads/
- **Git** — necessário caso você vá baixar o projeto com `git clone`: https://git-scm.com/downloads
- conexão com a internet — usada para consultar e baixar os releases atuais dos homebrews.

No Windows, durante a instalação do Python, marque a opção **Add Python to PATH**. Depois, confirme que tudo está instalado corretamente:

```bash
python --version
git --version
```

Em alguns sistemas o comando do Python é `python3`:

```bash
python3 --version
```

Se você preferir baixar o repositório pelo botão **Code > Download ZIP** do GitHub, o Git não é obrigatório.

Depois de clonar ou extrair o ZIP, instale as dependências Python:

```bash
python -m pip install -r requirements.txt
```

O `py7zr`, necessário para extrair releases distribuídos em `.7z`, é instalado por esse arquivo de requisitos.

### Instalação pelo Git

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python -m pip install -r requirements.txt
python main.py
```

## Como usar

Ao iniciar, o programa pergunta:

1. idioma;
2. **onde salvar a saída**;
3. qual Memory Card você usa;
4. onde OSDMenu e os homebrews ficarão;
5. quais homebrews opcionais instalar;
6. qual canal usar quando houver stable/beta/development;
7. se deve baixar os arquivos;
8. se deve gerar o pacote final.

### Pasta de saída

Por padrão você pode simplesmente pressionar Enter e usar:

```text
./output/
```

Ou escolher uma pasta personalizada. Caminhos relativos e absolutos são aceitos, `~` e variáveis de ambiente são expandidos e o programa verifica se consegue escrever no local antes de começar os downloads.

Também é possível definir direto pela linha de comando:

```bash
python main.py --output ~/PS2/Pacote
```

Tudo daquele processamento passa a ficar nessa pasta: `selection.json`, downloads e `Ps2Installer_Package/`.

## Versões

O Ps2Installer não chama toda build recente de stable. O catálogo define a política de cada projeto e o programa mostra claramente o canal antes da instalação.

Exemplo:

```text
Open PS2 Loader
Versões disponíveis:
  - Stable: v1.x.x (stable)
  - Beta / prerelease: v1.x.x-Beta-xxxx (prerelease)
```

Builds de desenvolvimento recebem identificação própria. Essa informação também entra no nome mostrado no OSDMenu e no OPL.

## Pacote gerado

Exemplo para um usuário de MemCard PRO2 + MX4SIO:

```text
Ps2Installer_Package/
├── 1_MEMCARD_PRO2_VMC/
│   ├── BOOT/
│   │   └── BOOT.ELF
│   ├── SYS-CONF/
│   │   ├── PS2BBL.INI
│   │   └── OSDMENU.CNF
│   └── README-COPY-HERE.txt
│
├── 2_MX4SIO/
│   ├── APPS/
│   │   ├── OSDMenu/
│   │   │   ├── osdmenu.elf
│   │   │   └── title.cfg
│   │   ├── OPL/
│   │   │   └── OPNPS2LD.ELF
│   │   └── ...
│   └── README-COPY-HERE.txt
│
├── README.txt
└── manifest.json
```

A pasta `1_...` muda conforme o Memory Card escolhido. A pasta `2_...` muda conforme MMCE, MX4SIO, USB, HDD exFAT ou HDD APA/PFS.

**Copie o conteúdo da pasta de destino, não a pasta externa inteira.** Por exemplo, `BOOT/BOOT.ELF` deve terminar como `mc0:/BOOT/BOOT.ELF` ou `mc1:/BOOT/BOOT.ELF`, e não como `mc0:/1_MEMORY_CARD/BOOT/BOOT.ELF`.

## PS2BBL

O instalador baixa o pacote oficial atual do PS2BBL e escolhe automaticamente a variante necessária para o armazenamento:

- USB: `PS2`;
- MMCE: `PS2_MMCE`;
- MX4SIO: `PS2_MX4SIO`;
- HDD APA/PFS: `PS2_HDD`.

O binário escolhido vira:

```text
BOOT/BOOT.ELF
```

O `SYS-CONF/PS2BBL.INI` gerado mantém o boot normal voltando ao OSDSYS e configura **R1 para abrir OSDMenu** no armazenamento selecionado.

Importante: copiar um ELF de PS2BBL para um Memory Card normal **não instala sozinho um exploit/autoboot**. O console ainda precisa de um ponto de entrada compatível com o seu setup (System Update, OpenTuna, modchip/DEV1 etc.).

### HDD exFAT

O OSDMenu suporta `ata:` para HDD interno exFAT, mas as builds oficiais comuns do PS2BBL usadas pelo projeto não oferecem esse mesmo caminho de lançamento. Nesse modo o Ps2Installer gera a biblioteca `APPS` e os arquivos possíveis, mas deixa um aviso explícito e não cria um `R1` inválido. Suporte a uma build compatível do PS2BBL Extended pode ser adicionado depois.

## OSDMenu

O `OSDMENU.CNF` é gerado em:

```text
SYS-CONF/OSDMENU.CNF
```

As entradas apontam para os ELFs reais no dispositivo escolhido e incluem as versões visíveis, por exemplo:

```ini
name_OSDSYS_ITEM_10 = Open PS2 Loader v1.2.0-Beta-xxxx
path1_OSDSYS_ITEM_10 = mx4sio:/APPS/OPL/OPNPS2LD.ELF
```

## OPL

Aplicativos marcados para aparecer no OPL recebem `title.cfg` na mesma pasta do ELF:

```ini
title=SNESticleRevive v1.0.7
boot=SNESticle.elf
```

Assim o OSDMenu e o OPL reutilizam os mesmos arquivos em `APPS/`.

## Arquivos de trabalho

Na pasta de saída escolhida ficam:

```text
selection.json

downloads/
  <app>/
    download/
    extracted/

Ps2Installer_Package/
```

`selection.json` registra hardware escolhido, versões, canais, assets, downloads e o manifesto final do pacote.

## Modos úteis

```bash
# escolher a saída diretamente
python main.py --output /caminho/da/saida

# resolver versões sem baixar
python main.py --no-download

# baixar mas não montar o pacote final
python main.py --no-package

# não consultar GitHub
python main.py --offline

# testes
python -m unittest discover -s tests -v
```

Se o limite público da API do GitHub for atingido, você pode definir `GITHUB_TOKEN` no ambiente.

## Projetos relacionados

- PS2BBL: https://israpps.github.io/PlayStation2-Basic-BootLoader/
- OSDMenu: https://github.com/pcm720/OSDMenu
- Open PS2 Loader: https://github.com/ps2homebrew/Open-PS2-Loader
- wLaunchELF: https://github.com/ps2homebrew/wLaunchELF

## Segurança

Mantenha backup de Memory Cards importantes. Leia o `README.txt` e os avisos do pacote antes de sobrescrever qualquer configuração de boot em hardware real.
