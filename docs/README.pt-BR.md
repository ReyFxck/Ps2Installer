# Ps2Installer — Português (Brasil)

[README principal](../README.md) · [English](README.en.md) · [Español](README.es.md)

## O que é

Ps2Installer é um assistente para montar um pacote de homebrews do PlayStation 2. Ele automatiza download de releases, escolha de versões, organização dos ELFs e geração das configurações usadas pelo PS2BBL, OSDMenu e OPL.

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
    └── ...
```

## Requisitos

- **Python 3.10 ou mais recente**;
- **Git** para clonar pelo terminal;
- conexão com a internet para detectar e baixar releases.

Verifique:

```bash
python --version
git --version
```

Em alguns sistemas use `python3`. No Windows, marque **Add Python to PATH** durante a instalação do Python.

Se preferir baixar o projeto por **Code → Download ZIP**, o Git não é obrigatório.

## Instalação

```bash
git clone https://github.com/ReyFxck/Ps2Installer.git
cd Ps2Installer
python main.py
```

Não é mais necessário instalar `py7zr` manualmente antes da primeira execução. Se algum pacote escolhido estiver em `.7z`, o instalador verifica a dependência antes dos downloads e tenta instalá-la automaticamente usando o mesmo Python que está executando o Ps2Installer.

Se a instalação automática falhar:

```bash
python -m pip install -r requirements.txt
```

## Interface

A interface funciona como um wizard e possui:

- banner ASCII do Ps2Installer;
- cores para títulos, sucessos, avisos e erros;
- limpeza da tela entre as etapas principais;
- explicações curtas antes de cada pergunta;
- Stable, Beta/Prerelease e Development identificados claramente;
- resumo antes de começar os downloads;
- mensagens de progresso mais fáceis de entender.

O fluxo principal pergunta:

1. idioma;
2. pasta de saída;
3. tipo de Memory Card/VMC;
4. armazenamento onde OSDMenu e `APPS/` ficarão;
5. quais homebrews instalar;
6. qual canal usar quando houver mais de um;
7. se deve baixar os arquivos;
8. se deve gerar o pacote final.

## Saída

Por padrão você pode usar:

```text
./output/
```

ou escolher qualquer pasta gravável. Também é possível informar diretamente:

```bash
python main.py --output ~/PS2/Pacote
```

A saída contém:

```text
selection.json

downloads/

Ps2Installer_Package/
├── 1_...MEMORY_CARD.../
├── 2_...STORAGE.../
├── README.txt
└── manifest.json
```

Cada pasta de destino possui um `README-COPY-HERE.txt` explicando onde copiar seu conteúdo.

## PS2BBL e OSDMenu

O PS2BBL fica no Memory Card/VMC. O script escolhe a variante adequada conforme o armazenamento selecionado e gera `PS2BBL.INI` para usar **R1 como atalho para OSDMenu** quando o modo possui suporte compatível.

O OSDMenu e os homebrews maiores ficam no armazenamento escolhido. O `OSDMENU.CNF` é gerado automaticamente com os caminhos e versões exibidas no menu.

Aplicativos compatíveis com a aba APPS do OPL recebem também um `title.cfg` na mesma pasta do ELF, evitando duplicar arquivos.

## Modos úteis

```bash
python main.py --output /caminho/da/saida
python main.py --no-download
python main.py --no-package
python main.py --offline
python main.py --no-color
python main.py --no-clear
python -m unittest discover -s tests -v
```

As cores também são desativadas automaticamente quando a saída não é um terminal interativo ou quando a variável `NO_COLOR` está definida.

## Segurança

O Ps2Installer apenas gera arquivos e pastas; ele não grava diretamente no PS2. Mesmo assim, mantenha backup de Memory Cards importantes e leia os READMEs gerados antes de substituir arquivos de boot.
