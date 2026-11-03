---
name: career-ops-interview-prep
description: Prepare for recruiter or interview conversations using a completed evaluation report.
---

# Career-Ops Interview Prep Workflow

Use this workflow only when explicitly invoked. It prepares likely recruiter/interview questions and grounded answers for a role that already has an evaluation report.

## Language Detection
Match the language of the evaluation report or Job Description:
- **Portuguese (BR):** If the report/JD is in Portuguese, generate questions and answers in Portuguese (BR).
- **English:** Default for any other language.

## Input
Accept any of:
- Report ID, e.g. `123`
- Company and role
- Job URL or pasted Job Description
- Path to a local report or JD

---

## Steps

### 1. Identify the Offer
1. Resolve the matching report in `output/reports/`.
2. Prefer exact report ID match when provided.
3. Otherwise search by company, role, URL, and report header.
4. If no matching report exists, ask the user to run `/career-ops-evaluate` first or paste the full JD.

### 2. Load Context
Read:
1. The full matching evaluation report, especially Sections A-E and Sections F/G when present.
2. `config/profile.yml`
3. `content/cv.md`
4. `content/story-bank.md`
5. `content/article-digest.md` if it exists.

If the report is missing Section F or G, read the numeric score before deciding what to do:
- If score `< 4.0`, state that F/G were intentionally skipped by the threshold policy and continue because invoking this workflow is an intentional threshold bypass.
- If score `>= 4.0`, warn that the high-fit report is incomplete and recommend completing `/career-ops-evaluate`, but still continue if enough JD/report context exists to produce grounded answers.
- If the score is missing or not numeric, warn that threshold status cannot be verified and continue only if enough JD/report context exists.

### 3. Analyze Interview Risk
Use the JD, report, CV match table, gaps, level strategy, red flags, and Section F stories when present to identify:
- The recruiter's likely screening priorities.
- The strongest proof points to repeat.
- The gaps or objections likely to appear.
- The company-specific motivation signals from Section G when present.

### 4. Generate Nine Probable Questions
Create exactly 9 likely recruiter/interview questions.

**Mandatory Questions to Always Include (The "Big Three"):**
1. "Tell me about a time you put a number in front of a stakeholder and it was wrong."
   - Focus the answer on: Owning the mistake vs blaming upstream, how it was caught, and process changes made afterwards.
2. "Show me a piece of SQL you wrote that you're proud of, and walk me through it."
   - Focus the answer on: Explaining choices, CTE vs subquery knowledge, and mentioning performance, readability, or edge cases.
3. "How are you using AI in your work right now?"
   - Focus the answer on: Specifics, what it's NOT used for, and a genuine opinion.

**Plus exactly 6 tailored questions covering:**
- Role motivation.
- Relevant technical or domain experience.
- A gap, risk, or objection from the evaluation.
- One behavioral/story question.
- One company or product motivation question.
- One logistics, compensation, seniority, or availability question when relevant.

### 5. Generate Answers
For each question, provide:
- A concise answer in the candidate's voice.
- The evidence used, referencing report sections, CV facts, or story-bank entries.
- A fallback note if the answer relies on adjacent experience rather than exact experience.

Rules:
- Do not invent experience, metrics, employers, tools, certifications, or personal history.
- Use Section F and `content/story-bank.md` for stories whenever possible.
- Use Section G for role/company motivation when present; otherwise derive motivation from A-E and the JD.
- Keep answers interview-ready, not essay-length.
- Avoid corporate filler and unsupported claims.

### 6. Story Bank Update
If a newly formed answer contains a reusable STAR+R story grounded in real candidate evidence:
1. Append it to `content/story-bank.md`.
2. Include the source evidence or report ID.
3. Do not add speculative or JD-only stories.

### 7. Format Output
```markdown
## Interview Prep: {Company} — {Role}

Based on: Report #{NNN} | Score: {X.X}/5 | Archetype: {type}

---

### 1. {Likely question}
**Answer:** {interview-ready answer}
**Evidence:** {report/CV/story-bank references}
**Fallback:** {only if needed}

...

---

## Focus Before the Call
- {Top point to repeat}
- {Likely objection to prepare for}
- {One question to ask the recruiter}
```

---
## Final Output
1. Automatically save the generated interview prep content to a new Markdown file in the `output/reports/` directory. Name the file using the format `{ID}-{company}-interview-prep.md` (e.g., `051-tractian-interview-prep.md`).
2. Show the nine questions and answers to the user, list any story-bank additions made, confirm that the interview prep document was saved, and confirm that tracker status was not changed.
