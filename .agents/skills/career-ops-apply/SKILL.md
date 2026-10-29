---
name: career-ops-apply
description: Apply to a job by generating personalized responses to application form questions.
---

# Career-Ops Application Assistant

Use this workflow to generate personalized answers for a specific job application form.

## Language Detection
Match the language of the application form:
- **Portuguese (BR)** forms → respond in Portuguese (BR).
- **English** forms → respond in English (default).

## Input
Paste the questions from the job application form, or share a screenshot, or provide the URL to the form.

---

## Steps

### 🔍 1. Identify the Offer
1. From the input, extract the company name and role title.
2. Search `workspace/reports/` (case-insensitive) for a matching evaluation report.
3. If a report exists, load it fully — especially **Section G** (draft answers) and **Section F** (STAR stories).
4. If the report is missing Section F or Section G, read the numeric score before deciding what to do:
   - If score `< 4.0`, warn that F/G were intentionally skipped because the role is below the apply-prep threshold. Stop unless the user explicitly asks to force prep.
   - If score `>= 4.0`, route back to [career-ops-evaluate](/career-ops-evaluate) because the high-fit report is incomplete.
   - If the user explicitly asks to force F/G, force prep, or generate application prep anyway, generate or request F/G first, then continue.
5. If no report exists, warn the user and offer to run a quick `/career-ops-evaluate` first.

### 🔄 2. Check for Role Changes
If the role on the form differs from the one in the report:
- Alert the user: "The role has changed from [X] to [Y]. Should I adapt the answers or re-evaluate?"
- If adapt → adjust answers to the new title without full re-evaluation.
- If re-evaluate → trigger the [career-ops-evaluate](/career-ops-evaluate) workflow.

### 📋 3. Extract All Form Questions
Identify ALL visible question types:
- Free text (cover letter, why this role, relevant project)
- Dropdowns (how did you hear, authorization status)
- Yes/No (relocation, visa sponsorship)
- Salary fields
- Upload prompts (resume, cover letter)

If the form has more questions below the visible area, ask the user to scroll and share additional screenshots or paste remaining questions.

### ✍️ 4. Generate Answers
For each question, refine the existing **Section G** draft answers using the **Grounded Confident Fit** tone framework. If Section G was force-generated for a score `< 4.0`, preserve a note that this is threshold override prep:

| Question Type | Framework |
|---|---|
| Why this role? | The role responsibilities map to Rafael's real SQL, Python, dbt, analytics, automation, or business-partner work. |
| Why this company? | Strong company, interesting market, practical growth opportunity, product/category relevance, or credible culture fit. |
| Relevant experience? | One quantified proof point, then why it transfers to the role. |
| Good fit? | Skillset plus working style: ownership, complexity, high standards, remote execution. |
| Culture fit? | Direct communication, ownership, pace, and high performance; no exaggerated values language. |
| How did you hear? | Honest. "Found via [source], evaluated against my criteria, it scored highest." |

**Grounded Confident Fit tone rules:**
- Start from practical fit: role, stack, company quality, market, growth, complexity.
- Sound confident but not arrogant, interested but not worshipful.
- Prefer concrete phrases like "this role is close to the work I already do well" and "I do well in complex, high-performing environments."
- Avoid "mission," "meaningful work," "deeply aligned," "passionate," "inspired," "proven track record," and generic corporate language.
- Keep answers short: usually 2-3 paragraphs or 3-5 direct sentences depending on the form field.
- Every answer references something real from the JD and something real from the candidate's background.

Section G is the base. Do not generate application answers from scratch unless `/career-ops-evaluate` has completed Section G or the user explicitly requested force prep.

### 📝 5. Format Output
```
## Application Answers: {Company} — {Role}

Based on: Report #{NNN} | Score: {X.X}/5 | Archetype: {type}

---

### 1. {Question exactly as written}
> {Answer ready for copy-paste}

### 2. {Next question}
> {Answer}

...

---
Notes:
- {Any observations about the form or the role}
- {Suggestions the candidate should review before submitting}
```

### 🚀 6. Post-Apply Update (if user confirms they submitted)
If the user confirms they submitted the application:
1. Update `workspace/applications.md` — change status from `Evaluated` to `Applied`.
2. Save final form-specific answers to the report under a clearly named `### Final Application Answers` subsection within Section G.
3. Suggest next step: LinkedIn outreach (`/career-ops-contacto`).

---
## Final Output
Present all answers in the format above with a reminder: **ALWAYS review before submitting. Never submit without reading.**
