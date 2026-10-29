---
name: career-ops-cv
description: Generate an ATS-optimized PDF resume tailored to a specific job description.
---

# Career-Ops CV Generation Workflow

> [!IMPORTANT]
> **Constraint Precedence:** Before starting, you **MUST** read and apply all rules in [GEMINI.md](file:///c:/Users/Rafael.Canedo/Projects/career-ops-python/GEMINI.md). The rules in `GEMINI.md` take absolute precedence over this workflow in case of conflict.

Use this workflow to create a custom PDF version of your resume that is keyword-optimized for a specific job posting.

## Language Detection
- If the JD is in **Portuguese (BR)** → generate CV in Portuguese. Section headers: "Resumo Profissional", "Experiência Profissional", "Educação", "Projetos", "Habilidades".
- If in **English** (default) → keep English headers: "Professional Summary", "Work Experience", "Education", "Projects", "Skills".

---

## Steps

### 📋 1. Load Sources of Truth
1. Read `content/cv.md` — canonical resume content.
2. Read `content/article-digest.md` — detailed proof points (if exists). Metrics from here take precedence over `content/cv.md`.
3. Read `config/profile.yml` — name, email, LinkedIn, portfolio URL, location.

### 🎯 2. Analyze the Job Description
1. Detect language of the JD (EN or PT-BR).
2. Detect company location to choose paper format:
   - **US / Canada** → `letter`
   - **Rest of world (including Brazil)** → `a4`
3. Detect the role archetype and adjust the Professional Summary framing.
4. Extract **15-20 ATS keywords** from the JD.

### ✍️ 3. Build Personalized Content
Keyword injection rules — **only reformulate real experience, never invent**:
- Use exact vocabulary from the JD when describing existing experience.
- Example: JD says "RAG pipelines" + CV says "LLM workflows with retrieval" → write "RAG pipeline design and LLM orchestration workflows".

Build each section:
- **Work Experience** — Re-order bullets by relevance to this JD. Most relevant bullets first:
  - Most recent role (Construtora Atrium): **Minimum 8 bullets** (target 8–9 bullets to maximize density on the 1-page layout).
  - Next 2 subsequent roles: **Minimum 4 bullets each** (or concise entry for gap year).
- **Skills** — Add JD-specific terms where truthful.
- **Education & Certifications** — Unchanged.

### 🖼️ 4. Generate HTML
1. Load `assets/templates/cv-template.html`.
2. Replace ALL `{{PLACEHOLDERS}}` with personalized content:

| Placeholder | Content |
|---|---|
| `{{LANG}}` | `en` or `pt-BR` |
| `{{PAGE_WIDTH}}` | `8.5in` (letter) or `210mm` (a4) |
| `{{NAME}}` | from `profile.yml` |
| `{{EMAIL}}` | from `profile.yml` |
| `{{LINKEDIN_URL}}` | from `profile.yml` |
| `{{PORTFOLIO_URL}}` | from `profile.yml` |
| `{{LOCATION}}` | from `profile.yml` |
| `{{SECTION_EXPERIENCE}}` | "Work Experience" or "Experiência Profissional" |
| `{{EXPERIENCE}}` | HTML for each role with re-ordered bullets |
| `{{SECTION_SKILLS}}` | "Skills" or "Habilidades" |
| `{{SKILLS}}` | HTML for skills |
| `{{SECTION_EDUCATION}}` | "Education" or "Educação" |
| `{{EDUCATION}}` | HTML for education |

3. Fix font paths: replace `./fonts/` with the absolute `file://` path (resolving from `assets/fonts/`).
4. Save HTML to a temp file: `workspace/output/{ID}-CV-Rafael-Albuquerque-{company-slug}.temp.html`

### 🖨️ 5. Print to PDF
Run via `run_command`:
```bash
career-ops cv workspace/output/{ID}-CV-Rafael-Albuquerque-{company-slug}.temp.html workspace/output/{ID}-CV-Rafael-Albuquerque-{company-name}-{role}.pdf --format={a4|letter}
```

### 📊 6. Update Tracker
If this job already has an entry in `workspace/applications.md`, update the PDF column from ❌ to ✅.

---
## Final Output
Report:
- ✅ PDF path: `workspace/output/{ID}-CV-Rafael-Albuquerque-{company-name}-{role}.pdf`
- 📊 Page count and file size.
- 🔑 Keywords injected count.
- ⚠️ Any ATS warnings.
