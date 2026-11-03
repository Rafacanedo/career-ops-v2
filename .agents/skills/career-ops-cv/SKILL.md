---
name: career-ops-cv
description: Generate an ATS-optimized PDF resume tailored to a specific job description.
---

# Career-Ops CV Generation Workflow

Use this workflow to create a custom, ATS-parseable single-page PDF version of your resume tailored to a specific job posting.

## Language & Format Detection
- If the JD is in **Portuguese (BR)** → `lang = "pt-br"`.
- If in **English** (default) → `lang = "en"`.
- Location check for paper format:
  - **US / Canada** → `letter`
  - **Rest of world (including Brazil)** → `a4`

---

## Steps

### 📋 1. Load Sources of Truth
1. Read `content/cv.md` — canonical resume experience.
2. Read `content/article-digest.md` — detailed metrics and proof points (if exists).
3. Read `config/profile.yml` — candidate contact, headline, and target narrative.
4. If a `vaga_id` or sequence number (e.g. `62`, `#062`, or `vaga_...`) is provided, retrieve the job description and metadata via:
   ```bash
   career-ops show <vaga_id_or_seq> --full
   ```

### 🎯 2. Analyze the Job Description
1. Detect language (EN vs PT-BR) and paper format (`a4` vs `letter`).
2. Identify the role archetype and select the relevant framing from `profile.yml`.
3. Extract **15–20 ATS keywords** from the JD.

### ✍️ 3. Build Personalized Content
Keyword injection rules — **only reformulate real experience, never invent**:
- Use exact vocabulary from the JD when describing existing experience.
- Experience bounds:
  - Primary role: maximum 8 bullets (concise, high-impact metrics).
  - Prior roles: maximum 4 bullets each.
  - Character limit: maximum 200 characters per bullet point.
  - Summary: maximum 600 characters.

### 💾 4. Stage Structured CV Payload
Format and write the structured JSON payload to `workspace/staging/cv_<vaga_id>.json`:

```json
{
  "format": "a4",
  "lang": "en",
  "name": "Candidate Name",
  "headline": "Staff Distributed Systems Engineer",
  "contact": {
    "email": "candidate@example.com",
    "phone": "+55 11 99999-9999",
    "location": "São Paulo, Brazil",
    "linkedin_url": "https://linkedin.com/in/candidate",
    "portfolio_url": "https://github.com/candidate"
  },
  "summary": "...",
  "experience": [
    {
      "company": "Company A",
      "role": "Principal Architect",
      "location": "São Paulo, Brazil",
      "start_date": "2022",
      "end_date": "Present",
      "bullets": [
        "Architected real-time streaming data platform using Kafka..."
      ]
    }
  ],
  "skills": {
    "languages": ["Python", "TypeScript", "SQL"],
    "technologies": ["Docker", "Kubernetes", "Kafka", "PostgreSQL"],
    "practices": ["Distributed Systems", "Domain-Driven Design"]
  },
  "education": [
    {
      "institution": "University Name",
      "degree": "B.S. in Computer Science",
      "year": "2015"
    }
  ],
  "projects": []
}
```

### 🖨️ 5. Compile PDF & Enforce Single-Page Budget
Run the deterministic compiler via `run_command` (the output PDF path is automatically derived as `output/cv/{index:03d}-rafael-{role}-{company}.pdf` when `--vaga-id` is supplied):
```bash
career-ops cv render --payload workspace/staging/cv_<vaga_id>.json --vaga-id <vaga_id> --format <a4|letter>
```

#### Handling Overflow (Exit Code 2):
If the compiler returns exit code `2`, it outputs structured overflow telemetry:
```json
{
  "status": "overflow",
  "overflow_px": 38,
  "estimated_line_excess": 2,
  "section_heights": {"header": 110, "summary": 125, "experience": 750, ...}
}
```
When this occurs:
1. Identify the largest section from `section_heights` (typically `experience` or `summary`).
2. Trim or merge the estimated number of excess lines (e.g. prune 1 bullet from the oldest role or condense summary).
3. Re-save `workspace/staging/cv_<vaga_id>.json` and re-run compilation until exit code `0` is achieved.

---
## Final Output
Report:
- ✅ PDF path: `output/cv/{index:03d}-rafael-{role}-{company}.pdf`
- 📄 Page count: 1 page (guaranteed)
- 🔑 Top ATS keywords injected
- 📊 SQLite tracker status updated
