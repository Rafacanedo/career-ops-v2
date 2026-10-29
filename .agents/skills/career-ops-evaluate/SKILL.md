---
name: career-ops-evaluate
description: Evaluate a Job Description (URL or Text), then generate prep/PDF only for high-fit roles.
---

# Career-Ops Evaluation Workflow

Use this workflow to evaluate a specific job posting against your profile. Generate application prep and a customized PDF resume only when the match is good.

## Pre-flight Check
Before evaluating, run a sync check:
```bash
career-ops sync-check
```
If warnings appear, notify the user before continuing.

## Language Detection
Detect the language of the Job Description:
- **Portuguese (BR):** If JD is in Portuguese → generate the report, CV summary, and all candidate-facing text in **Portuguese (BR)**.
- **English:** Default for any other language.

## Input
Paste the Job Description text or provide the URL of the job posting.

---

## Steps

### 🔍 1. Extract Job Description
**PRIORITY 0 (ABSOLUTE FIRST):** If the input or the pipeline entry contains a reference to a local file (`[jd: local:path/to/jd.md]`), **read this file immediately** and use it as the Job Description. Skip all other extraction steps.

If no local file is provided, use this priority order:
1. **`read_url_content`** — Static fetch (fast, works for simple pages).
2. **`browser_subagent`** — If static fetch returns blank or a login wall, use a browser subagent to navigate to the URL and extract the full JD text.
3. **WebSearch (last resort)** — Search for the job title + company on job board aggregators.

If none work, ask the user to paste the JD text directly.

After extracting, record the exact URL as `**URL:** {url}` — this is required in the report header.

### 📋 2. Load Your Profile
Read all sources of truth in this order:
1. `config/profile.yml` — **Primary Source**. Identity, target roles, and positioning narrative.
2. `content/cv.md` — Your comprehensive experience base.
3. `content/story-bank.md` — Your repository of STAR+R success stories for deep tailoring.
4. `content/article-digest.md` — (Optional) Specific project metrics and proof points.

> **Rule:** Positioning and "Headline" defined in `profile.yml` take precedence over generic descriptions in `cv.md`. Use `story-bank.md` to ground the "Interview Prep" section in real evidence.

### ✨ 3. Detect Archetype
Classify the offer into one of the archetypes defined in `config/profile.yml`. If it doesn't fit perfectly, select the closest match or a hybrid. This choice will dictate the narrative used for the CV and report.

### 🧠 4. Perform Evaluation
Produce the required blocks for the score threshold. Write output in the detected language (EN or PT-BR):

- **A) Role Summary** — Archetype detected, domain, function, seniority, remote policy, team size, TL;DR.
- **B) CV Match** — Table mapping each JD requirement to exact lines in `cv.md`. Then a Gaps section with mitigation for each gap (hard blocker vs nice-to-have, adjacent experience, portfolio coverage, framing phrase).
- **C) Level & Strategy** — Detected level vs candidate's natural level. Use the `headline` and `superpowers` from the detected archetype in `profile.yml` to define the "selling strategy".
- **D) Comp & Market** — Use `search_web` (Glassdoor, Levels.fyi, Blind) for current market data. Table with sources cited. If no data found, say so.
- **E) Personalization Plan** — Top 5 CV changes + Top 5 LinkedIn changes to maximize match. Format as a table.

Threshold policy:
- If score `< 4.0`, generate A-E, score/recommendation, and Extracted Keywords only. Do not generate F/G or a PDF.
- If score `>= 4.0`, also generate F/G and trigger PDF generation.
- If the user explicitly asks to "force F/G", "force prep", "generate application prep anyway", or similar, generate F/G regardless of score. Force prep does not force PDF generation.

### 📊 5. Calculate Score
Weighted score 1-5 across dimensions:
- CV Match, North Star Alignment, Comp, Cultural Signals, Red Flags

| Score | Recommendation |
|---|---|
| 4.5+ | Strong match — recommend applying immediately |
| 4.0–4.4 | Good match — worth applying |
| 3.5–3.9 | Decent — apply only if specific reason |
| < 3.5 | Recommend against applying |

### 📝 6. Generate Sections F/G (if score ≥ 4.0 or force prep requested)
Generate these sections only when the score is `>= 4.0` or the user explicitly requested force prep:

- **F) Interview Prep** — 6-10 STAR+R stories mapped to JD requirements. Check `content/story-bank.md` for existing stories; append any new ones.
- **G) Draft Application Answers** — Draft reusable application answers grounded in the JD and candidate evidence.

For Section G, draft application form answers using the **Grounded Confident Fit** tone:
- **Why this role?** → The role responsibilities map to Rafael's real SQL, Python, dbt, analytics, automation, or business-partner work.
- **Why this company?** → Strong company, interesting market, practical growth opportunity, product/category relevance, or credible culture fit.
- **Relevant experience?** → One quantified proof point, then why it transfers to the role.
- **Good fit?** → Skillset plus working style: ownership, complexity, high standards, remote execution.
- **Culture fit?** → Direct communication, ownership, pace, and high performance; no exaggerated values language.
- **How did you hear?** → Honest answer.

**Grounded Confident Fit tone rules:**
- Start from practical fit: role, stack, company quality, market, growth, complexity.
- Sound confident but not arrogant, interested but not worshipful.
- Prefer concrete phrases like "this role is close to the work I already do well" and "I do well in complex, high-performing environments."
- Avoid "mission," "meaningful work," "deeply aligned," "passionate," "inspired," "proven track record," and generic corporate language.
- Keep answers short: usually 2-3 paragraphs or 3-5 direct sentences depending on the form field.
- Every answer references something real from the JD and something real from the candidate's background.
- If F/G are force-generated below 4.0, explicitly label them as threshold override prep.

### ✅ 7. Conditional Completion Gate
Before saving, generating the PDF, updating the tracker, or showing final output, verify the report contains every section required by the threshold and that each required section has usable substance.

Always required:

- `## A) Role Summary`
- `## B) CV Match`
- `## C) Level & Strategy`
- `## D) Comp & Market`
- `## E) Personalization Plan`
- score/recommendation in the report header or score section
- `## Extracted Keywords`

Required only when score `>= 4.0` or force prep was requested:
- `## F) Interview Prep`
- `## G) Draft Application Answers`

Gate rules:
- Do not save or report completion while any required section is missing.
- Do not leave placeholder text such as `...`, `TBD`, `pending`, or "to be filled" in any required section.
- Section B must include JD requirement mapping and gaps/mitigations.
- Section F must include 6-10 STAR+R stories mapped to JD requirements when required.
- Section G must include draft answers for the standard application questions when required.
- Extracted Keywords must include 15-20 ATS keywords from the JD.
- If any section is missing or thin, complete that section first, then re-run this gate.

### 💾 8. Save Evaluation Report
1. List all files in `workspace/reports/` to determine the next sequential number (max + 1, zero-padded to 3 digits).
2. Save at `workspace/reports/{###}-{company-slug}-{YYYY-MM-DD}.md` using this exact format:

```markdown
# Evaluation: {Company} — {Role}

**Date:** {YYYY-MM-DD}
**Archetype:** {detected}
**Score:** {X.X/5}
**URL:** {job url}
**PDF:** {path or pending}

---

## A) Role Summary
...

## B) CV Match
...

## C) Level & Strategy
...

## D) Comp & Market
...

## E) Personalization Plan
...

<!-- Include only if score >= 4.0 or force prep was requested. -->
## F) Interview Prep
...

<!-- Include only if score >= 4.0 or force prep was requested. -->
## G) Draft Application Answers
...

---

## Extracted Keywords
(15-20 ATS keywords from the JD)
```

After composing the report, run the conditional completion gate again against the final report text before writing it to disk.

### 🖨️ 9. Generate Tailored PDF
If score `>= 4.0`, trigger the [career-ops-cv](/career-ops-cv) workflow immediately. If score `< 4.0`, do not generate a PDF unless the user explicitly requests a PDF; force prep alone does not force PDF generation.

### 📊 10. Update Tracker
1. Write a single TSV line to `workspace/tracker-additions/{num}-{company-slug}.tsv`:
   ```
   {num}\t{date}\t{company}\t{role}\t{status}\t{score}/5\t{pdf_emoji}\t[{num}](workspace/reports/{num}-{slug}-{date}.md)\t{note}
   ```
2. Run `career-ops merge` to merge into `workspace/applications.md`.

**NEVER edit `workspace/applications.md` directly to add new entries.**

---
## Final Output
Show the user:
1. A summary card (Company, Role, Score, Archetype, Recommendation).
2. Links to the saved report and PDF if generated.
3. Top 3 recommended actions.
