---
name: career-ops-gupy
description: Generate an optimized professional summary and select matching skills for a Gupy profile.
---

# Career-Ops Gupy Profile Workflow

> [!IMPORTANT]
> **Constraint Precedence:** Before starting, you **MUST** read and apply all rules in [GEMINI.md](file:///c:/Users/Rafael.Canedo/Projects/career-ops-python/GEMINI.md). The rules in `GEMINI.md` take absolute precedence over this workflow in case of conflict.

Use this workflow to extract insights from a job report and generate customized text to update your Gupy profile for maximum match probability.

## Steps

### 📥 1. Receive Inputs
1. Receive the **Job ID** (e.g., `087`).
2. Receive an **image** containing the list of available skills on the Gupy platform.

### 📋 2. Read the Job Report
1. Locate the corresponding report file in `workspace/reports/` matching the Job ID (e.g., `workspace/reports/087-*.md`).
2. Read the report to understand the role requirements, core competencies, and the target archetype.

### ✍️ 3. Generate Professional Summary
1. Write a compelling **Professional Summary** ("Resumo Profissional") tailored to the role.
2. **Length Constraint**: The summary must be **1450 characters** long. Make it robust, comprehensive, and well-articulated.
3. Ensure it incorporates common keywords and core competencies from the job report to maximize match rates on the Gupy platform.

### 🎯 4. Select Matching Skills
1. Analyze the provided image of the Gupy skills list.
2. Cross-reference the skills in the image with the requirements and ideal profile detailed in the job report.
3. Select exactly **3 skills** from the image that have the highest alignment with the job vacancy.

---
## Final Output
Present the following in your response:
1. **Professional Summary (Resumo Profissional)**: The generated text (indicate the exact character count to verify the 1450-character target).
2. **Top 3 Skills (Habilidades)**: The 3 selected skills extracted from the provided image.
