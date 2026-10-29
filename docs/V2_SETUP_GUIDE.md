# Career-Ops v2 — Guia de Execução no PC de Casa

Este guia descreve os passos exatos para você executar no seu PC de casa. Ao final deste processo:
1. O repositório privado atual (`career-ops-python`) estará sincronizado e limpo de conflitos.
2. Seus dados pessoais estarão seguros em um diretório de dados dedicado (`CAREER_OPS_DATA_DIR`) com backup.
3. O novo repositório público **Career-Ops v2** (open-source) estará criado e funcional.
4. O Antigravity **Remote Control** estará ativo para você controlar o agente de qualquer lugar (celular, tablet, notebook do trabalho).

---

## Índice
1. [Passo A: Sincronizar o PC de Casa com o `main`](#passo-a-sincronizar-o-pc-de-casa-com-o-main)
2. [Passo B: Isolar a Pasta de Dados do Usuário](#passo-b-isolar-a-pasta-de-dados-do-usuário)
3. [Passo C: Criar o Novo Repositório Público (GitHub)](#passo-c-criar-o-novo-repositório-público-github)
4. [Passo D: Inicializar o Código do v2](#passo-d-inicializar-o-código-do-v2)
5. [Passo E: Importação dos Dados Legados para SQLite](#passo-e-importação-dos-dados-legados-para-sqlite)
6. [Passo F: Ativar o Antigravity Remote Control](#passo-f-ativar-o-antigravity-remote-control)

---

## Passo A: Sincronizar o PC de Casa com o `main`

No PC do trabalho, o branch `main` foi atualizado:
- Os artefatos de agentes multi-agentes (`.agents/worker_*`, etc.) foram deletados.
- O `.gitignore` foi configurado para ignorar `workspace/`, `content/`, `config/profile.yml` e `*.pdf`.
- Os arquivos foram desrastreados do git com `git rm --cached` (não foram apagados do disco).

### No PC de casa, abra o terminal no diretório do projeto e execute:

```powershell
# 1. Garanta que está no main
git checkout main

# 2. Faça um backup rápido por segurança dos seus arquivos locais de casa
Copy-Item -Recurse workspace "$HOME\backup-career-ops-workspace"
Copy-Item -Recurse content "$HOME\backup-career-ops-content"
Copy-Item config\profile.yml "$HOME\backup-career-ops-profile.yml"

# 3. Puxe as atualizações do origin
git pull origin main
```

> [!NOTE]
> Se o `git pull` reclamar de arquivos locais modificados em `workspace/` ou `content/`, você pode rodar:
> ```powershell
> git add -A
> git stash
> git pull origin main
> git stash pop
> ```
> Como o novo `.gitignore` já ignora `workspace/` e `content/`, a partir de agora o git nunca mais tentará versionar seus dados locais.

---

## Passo B: Isolar a Pasta de Dados do Usuário

Para o v2, a regra de ouro é: **código no repositório, dados em uma pasta externa**.

1. Crie a pasta de dados definitiva (ex: no seu usuário ou pasta sincronizada no Google Drive / OneDrive):
   ```powershell
   New-Item -ItemType Directory -Path "$HOME\career-ops-data" -Force
   New-Item -ItemType Directory -Path "$HOME\career-ops-data\reports" -Force
   New-Item -ItemType Directory -Path "$HOME\career-ops-data\output" -Force
   New-Item -ItemType Directory -Path "$HOME\career-ops-data\jds" -Force
   ```

2. Copie seus arquivos mestres para lá:
   ```powershell
   Copy-Item content\cv.md "$HOME\career-ops-data\cv.md"
   Copy-Item content\story-bank.md "$HOME\career-ops-data\story-bank.md"
   Copy-Item config\profile.yml "$HOME\career-ops-data\profile.yml"
   ```

3. Configure a variável de ambiente no seu sistema (PowerShell):
   ```powershell
   [System.Environment]::SetEnvironmentVariable('CAREER_OPS_DATA_DIR', "$HOME\career-ops-data", 'User')
   ```

---

## Passo C: Criar o Novo Repositório Público (GitHub)

1. Crie um repositório público vazio no GitHub com o nome:
   `career-ops` (ou `career-ops-ai`)
   - **Visibilidade:** Public
   - **Não** inicialize com README, `.gitignore` ou licença (vamos subir do zero).

2. No terminal do PC de casa (fora da pasta antiga):
   ```powershell
   cd $HOME\Projects  # ou onde você guarda seus repositórios
   mkdir career-ops
   cd career-ops
   git init -b main
   git remote add origin https://github.com/Rafacanedo/career-ops.git
   ```

---

## Passo D: Inicializar o Código do v2

Copie apenas os arquivos limpos do repositório antigo para o novo.

### 1. Copiar código fonte e configurações limpas
A partir da pasta do novo repositório `career-ops`:
```powershell
$OLD_REPO = "C:\caminho\para\career-ops-python"

# Copia código fonte
Copy-Item -Recurse "$OLD_REPO\src" .
Copy-Item -Recurse "$OLD_REPO\tests" .

# Copia configurações universais (apenas templates, sem dados pessoais)
New-Item -ItemType Directory config -Force
Copy-Item "$OLD_REPO\config\portals.yml" config\
Copy-Item "$OLD_REPO\config\states.yml" config\
Copy-Item "$OLD_REPO\config\profile.example.yml" config\

# Copia assets e configs de empacotamento
Copy-Item -Recurse "$OLD_REPO\assets" .
Copy-Item "$OLD_REPO\LICENSE" .
Copy-Item "$OLD_REPO\.python-version" .
Copy-Item "$OLD_REPO\pyproject.toml" .
```

### 2. Copiar as Skills migradas do branch snapshot
No PC de casa, as skills modernas com a sintaxe oficial do Antigravity (`SKILL.md`) estão salvas no branch `snapshot/work-pc-2026-10-29`:
```powershell
# Extraia a pasta de skills do snapshot
git --git-dir="$OLD_REPO\.git" archive snapshot/work-pc-2026-10-29 .agents/skills/ | tar -x -C .
```

### 3. Criar o `.gitignore` oficial do v2
Crie o arquivo `.gitignore`:
```gitignore
# Python
__pycache__/
*.py[oc]
build/
dist/
wheels/
*.egg-info
.pytest_cache/
.venv/
.env
*.log

# SQLite
*.db
*.db-journal
*.db-wal

# User local data
data/
output/
reports/
*.pdf

# System & IDE
.gemini/
.claude/
.DS_Store
Thumbs.db
```

### 4. Substituição do Gerador de PDF (Node -> Python puro)
No `pyproject.toml`, adicione o `weasyprint` ou `playwright`:
```toml
dependencies = [
    "click>=8.1",
    "openpyxl>=3.1.5",
    "python-dotenv>=1.2.2",
    "pyyaml>=6.0",
    "requests>=2.34.2",
    "weasyprint>=62.0",
    "pydantic>=2.0",
]
```
Isso elimina para sempre a pasta `node_modules` e a dependência do `generate-pdf.mjs`.

---

## Passo E: Importação dos Dados Legados para SQLite

Para unificar as vagas do trabalho e de casa sem colisão de IDs:

1. No novo repositório, o banco de dados `career-ops.db` terá a tabela:
   ```sql
   CREATE TABLE jobs (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       url TEXT UNIQUE,
       company TEXT,
       role TEXT,
       description TEXT,
       ats_type TEXT,
       external_id TEXT,
       first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       closed_at TIMESTAMP
   );

   CREATE TABLE applications (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       job_id INTEGER REFERENCES jobs(id),
       status TEXT, -- pending, evaluated, applied, interviewing, rejected, offer
       match_score REAL,
       archetype TEXT,
       report_path TEXT,
       cv_path TEXT,
       applied_at TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. Um script simples `career-ops import-legacy` lerá os arquivos `.tsv`, `job-tracker.csv` e `applications.md` dos dois computadores:
   - Usa a **URL da vaga** como chave única (`INSERT OR IGNORE` ou `ON CONFLICT(url) DO UPDATE`).
   - Atribui novos IDs sequenciais únicos e limpos, eliminando de vez as colisões (ex: a colisão 197-213).

---

## Passo F: Ativar o Antigravity Remote Control

O Remote Control permite que você controle a sessão do Antigravity rodando no PC de casa a partir do celular ou de qualquer outro computador.

### Como ativar:
1. Abra o **Google Antigravity** no PC de casa.
2. Abra as Configurações:
   - Pressione `Ctrl + ,` (ou clique na engrenagem no canto inferior esquerdo).
   - Na barra de pesquisa de configurações, digite `Remote Control`.
3. Marque a opção: **Enable Remote Control**.
4. O Antigravity gerará uma URL segura e um código de autenticação (ou autenticação via conta Google).
5. No PC do trabalho ou no celular:
   - Acesse a URL gerada pelo navegador.
   - Você poderá enviar mensagens para o agente, pedir avaliações de vagas, inspecionar planos e ver relatórios em tempo real sem precisar abrir portas no roteador nem configurar VPN.

---

## Resumo dos Comandos para o primeiro commit no v2

Quando terminar de copiar os arquivos para a pasta `career-ops`:
```powershell
cd $HOME\Projects\career-ops
git add .
git commit -m "feat: initial commit for career-ops v2 open-source"
git push -u origin main
```

Agora seu ambiente está estruturado, seus dados pessoais estão protegidos e o projeto está pronto para a comunidade!
