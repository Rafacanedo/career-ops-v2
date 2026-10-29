---
name: career-ops-archetypes
description: Generate 5 strategic archetypes from your CV to optimize your positioning.
---

# Career-Ops Archetype Discovery

Use this workflow to analyze your professional history and generate 5 distinct "personas" (Archetypes). This is an interactive process: we will brainstorm together, refine the copy, and only then update your profile.

---

## Steps

### 🗣️ 1. Consultation (User Input)
Before analyzing the files, ask the user:
- "Are there any specific career pivots or 'dream roles' you are targeting right now?"
- "Is there a 'hidden strength' or specific achievement not fully detailed in your CV that we should emphasize?"
- "What is the 'vibe' you want to project? (e.g., highly technical/low-level, strategic leadership, business-growth focused, automation wizard)."

### 🔍 2. Analyze Trajectory
Read these source files:
1. `content/cv.md` — Full experience and skills.
2. `config/profile.yml` — Current baseline and identity.

Extract core pillars, quantifiable wins, and differentiators, incorporating the user's input from Step 1.

### 🧠 3. Propose 5 Angles
Define 5 distinct professional archetypes. They must be grounded in actual experience but optimized for different hiring filters.
**Present these to the user in a table for feedback.**

### ✍️ 4. Refine & Iterate
Ask the user for feedback on the proposed archetypes:
- "Which of these feels most like 'you'?"
- "Are any of the headlines or superpowers off-target?"
- "Do you want to merge two archetypes or create a more aggressive version of one?"

**Iterate on the names, headlines, and superpowers until the user is satisfied.**

### 💾 5. Generate Final YAML
Only after the user approves the archetypes, output a single YAML block ready to be pasted into the `target_roles` section of `config/profile.yml`.

---

## Final Output
Present the 5 archetypes in a table, explaining the strategy for each. Then provide the final YAML block.

**Strategy for each archetype:**
| Archetype | Core Selling Point | Best For |
|---|---|---|
| {Name} | {Value} | {Company Type} |

**Final YAML:**
```yaml
target_roles:
  archetypes:
    - name: "{Archetype Name}"
      headline: "{Strategic Headline}"
      superpowers:
        - "{Superpower 1}"
        - "{Superpower 2}"
        - "{Superpower 3}"
      level: "{Senior/Mid/Lead}"
      fit: "primary"
    # ... (repeat for all 5)
```
