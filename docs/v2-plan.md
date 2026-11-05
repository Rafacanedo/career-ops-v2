# Career-Ops v2 — MVP open source, local, guiado por assistente de IA

## Princípios

1. **Local-first**: roda na máquina do usuário, sem servidor e sem conta.
2. **Agnóstico de assistente**: funciona com Antigravity, Gemini CLI, Claude Code, Codex etc. A IA vem do assistente que o usuário já tem, então o projeto **não precisa de chave de API**.
3. **Divisão clara**: **o que é determinístico vira comando da CLI Python** (fetch, filtro, tracker, PDF). **O que precisa de julgamento vira skill** (avaliar, adaptar CV, preparar entrevista). As skills chamam a CLI.
4. **Código separado dos dados do usuário**: o CV, o perfil e as candidaturas **nunca** ficam no repositório.
5. **Fonte de vagas = registry curado** de empresas + APIs públicas de ATS (Greenhouse, Lever, Ashby, Recruitee, Workable, SmartRecruiters). Sem scraping de navegador e sem APIs pagas no core.

---

## ⚠️ Estratégia de repositório

> [!CAUTION]
> O repo atual versiona `content/cv.md`, `config/profile.yml`, `workspace/applications.md`, relatórios, CVs gerados etc. **Um branch normal a partir do `main` carrega todo esse histórico.** Se ele for publicado, seus dados pessoais vão junto.

Opções:

| Opção | Como | Prós / contras |
| :--- | :--- | :--- |
| **A. Repo novo `career-ops` (recomendado)** | Repo público novo, código copiado de forma seletiva | Histórico limpo. O repo atual continua privado como a **sua instância de dados** |
| B. Branch órfão | `git checkout --orphan v2` no repo atual | Histórico limpo, mas fica no mesmo repo (hoje é público?). Risco de alguém dar push do `main` por engano |
| C. Branch normal | `git checkout -b v2` | ❌ Vaza o histórico. Só serve se o repo continuar privado para sempre |

Na v2, seu uso pessoal vira simplesmente **"o primeiro usuário"**: você aponta a v2 para uma pasta de dados (ex.: o repo privado atual ou `~/career-ops-data`).

---

## Estrutura proposta

```text
career-ops/                      # repo público
├── AGENTS.md                    # instruções universais para qualquer assistente
├── GEMINI.md / CLAUDE.md        # ponteiros finos -> AGENTS.md
├── .agents/skills/              # skills (Antigravity); espelhadas em .claude/skills via script
│   ├── setup/                   # W1 onboarding
│   ├── recommend/               # W2 triagem do feed
│   ├── evaluate/                # W3 avaliação A–G
│   ├── tailor-cv/               # W3 CV
│   ├── apply-assist/            # W3 respostas do formulário
│   ├── interview-prep/          # W4
│   └── story-bank/              # W4 entrevista guiada de histórias STAR+R
├── registry/
│   ├── companies.yml            # empresa, ats, token, país, tags  <- PRs da comunidade
│   └── schema.json
├── src/career_ops/
│   ├── cli.py
│   ├── paths.py                 # resolve o DATA_DIR
│   ├── db.py                    # SQLite (jobs, applications)
│   ├── fetch/                   # connectors + orchestrator (reuso)
│   ├── filter.py                # filtros duros + score por keywords
│   ├── tracker.py               # status das candidaturas
│   ├── render/                  # CV JSON/MD -> HTML -> PDF
│   └── schemas/                 # Pydantic: profile, evaluation, cv
├── templates/
│   ├── cv/                      # templates HTML/CSS
│   └── data-dir/                # esqueleto copiado no `init`
├── examples/                    # perfil + CV fictícios para teste/demo
└── tests/

~/career-ops-data/               # DATA_DIR do usuário (fora do repo, ou ./data no .gitignore)
├── profile.yml                  # identidade, preferências, arquétipos, regras de layout do CV
├── cv.md
├── story-bank.md
├── career-ops.db                # vagas + candidaturas (SQLite)
├── reports/{id}-{empresa}.md
└── output/{id}-CV-....pdf
```

> [!NOTE]
> As regras que hoje estão no `GEMINI.md` específicas suas (nome do arquivo do CV, 8 bullets na empresa atual, idiomas) passam para o **`profile.yml` do usuário**, em uma seção `cv_rules`. As skills leem dali. Assim o `AGENTS.md` fica genérico.

---

## Por que SQLite em vez de MD/CSV

Com um registry de algumas centenas de empresas, o fetch traz **milhares de vagas**. `pipeline.md`, `job-tracker.csv` e `applications.md` não aguentam esse volume e exigem scripts de merge e sync (`merge_tracker`, `sync_check`, `scan_csv`). Com SQLite:

- Um arquivo só, zero infraestrutura e embutido no Python.
- Dedup por `(ats, external_id)`, além de `first_seen` e `closed_at` para saber o que é novo ou foi encerrado.
- O assistente consulta pela CLI (`career-ops jobs list --new --json`), sem ler arquivos enormes.
- **Relatórios e CVs continuam em Markdown/PDF**, legíveis por humanos.
- `career-ops export` gera CSV/XLSX/dashboard HTML (reuso de `export.py`/`dashboard.py`).

---

## CLI (determinística)

| Comando | Função |
| :--- | :--- |
| `career-ops init [--data-dir]` | Cria o DATA_DIR a partir do template |
| `career-ops doctor` | Valida o ambiente, o perfil e o registry |
| `career-ops registry validate` / `add` | Testa se os tokens respondem; adiciona empresa |
| `career-ops fetch [--ats] [--company]` | Puxa as vagas do registry para o SQLite |
| `career-ops jobs list --new --match --json` | Feed filtrado (local, remoto, idioma, senioridade, keywords do perfil) |
| `career-ops jobs show <id>` | JD completa (o assistente lê daqui) |
| `career-ops app set <id> --status` | Atualiza o tracker |
| `career-ops render-cv <cv.json> --out` | Renderiza o PDF de forma determinística |
| `career-ops export` / `dashboard` | Gera CSV, XLSX e HTML |

## Skills (IA, executadas pelo assistente)

| Skill | Workflow | Usa da CLI |
| :--- | :--- | :--- |
| `setup` | Lê o CV → preenche `profile.yml`, arquétipos e seed do story bank | `init`, `doctor` |
| `recommend` | Roda o fetch + list, faz o re-rank do top N e o usuário escolhe | `fetch`, `jobs list` |
| `evaluate` | Avaliação A–G + score → relatório | `jobs show`, `app set` |
| `tailor-cv` | Gera o CV em JSON seguindo `cv_rules` → PDF | `render-cv` |
| `apply-assist` | Respostas do formulário + link de candidatura | `app set` |
| `interview-prep` | Perguntas específicas e gerais + histórias mapeadas | — |
| `story-bank` | Entrevista guiada para criar e melhorar histórias STAR+R | — |

---

## Mapa de migração do código atual

| Atual | v2 |
| :--- | :--- |
| `fetcher/*` | `fetch/*` (+ Workable, SmartRecruiters; Google/SearchAPI fica como plugin opcional) |
| `empresas.csv` (52 empresas) | `registry/companies.yml` com o token resolvido |
| `cv.py`, `generate-pdf.mjs` | `render/` (de preferência só Python, ex.: Playwright-python ou WeasyPrint, para eliminar a dependência de Node) |
| `normalize.py`, `dedup.py` | Dedup no `db.py` por id externo; o dedup semântico fica com o assistente |
| `export.py`, `dashboard.py` | Mantidos, lendo do SQLite |
| `scan_csv`, `merge_tracker`, `pipeline_clean`, `sync_check`, `parser.py` | Removidos (substituídos pelo SQLite) |
| `.agents/skills/career-ops-*` | Reescritas como skills genéricas (sem "Rafael", sem regras pessoais) |
| `career-ops-gupy` | Fora do core (sem API aberta); talvez plugin depois |
| `scratch/`, `workspace/`, `content/`, `config/profile.yml` | **Não vão** para o repo público |

---

## Roadmap

| Fase | Entregável |
| :--- | :--- |
| **1. Esqueleto** | Repo novo, `paths.py` + `init` + `doctor`, SQLite, schemas Pydantic, `examples/` fictício |
| **2. Vagas** | Conectores portados e testados, `registry/companies.yml` com as 52 empresas e tokens validados, `fetch` + `jobs list` |
| **3. Skills core** | `setup`, `recommend`, `evaluate`, `tailor-cv` + `render-cv` |
| **4. Entrevistas** | `interview-prep`, `story-bank`, `apply-assist` |
| **5. Open source** | README com quickstart, CONTRIBUTING (como adicionar empresa), CI (pytest + workflow semanal que valida o registry), release |
| **Depois** | Migrar seus dados atuais para um DATA_DIR v2 (script `import-v1`) |

---

## Decisões em aberto

1. **Repo**: A (repo novo público) ou B (branch órfão)? O repo atual é público hoje?
2. **Storage**: SQLite para vagas e tracker (recomendado) ou manter tudo em Markdown/CSV?
3. **Assistentes suportados**: Antigravity + Gemini CLI + Claude Code desde o início, ou só Antigravity no MVP?
4. **PDF**: tudo bem trocar o `generate-pdf.mjs` (Node) por uma solução só em Python?
5. **Idioma do projeto**: README e skills em inglês (alcance maior) com suporte a PT-BR nas saídas?
