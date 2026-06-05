# GenAI Quality Engineering — Course Scaffold

A practical, step-by-step course that takes you from **risk-storming** through
**rapid prototyping** in Vertex AI Studio, **scripted prompts in Python**, all
the way to a **production-grade GenAI application** built with quality
engineering best practices.

---

## Course at a Glance

| Module | Title | Duration |
|--------|-------|----------|
| 00 | [Course Overview & Prerequisites](modules/00-overview/README.md) | 15 min |
| 01 | [Risk-Storming for GenAI](modules/01-risk-storming/README.md) | 45 min |
| 01b | [Test Data Management](modules/01b-test-data-management/README.md) | 45 min |
| 02 | [Rapid Prototyping in Vertex AI Studio](modules/02-vertex-ai-studio/README.md) | 60 min |
| 03 | [Reading & Understanding the Codebase](modules/03-python-scripting/README.md) | 60 min |
| 04 | [Prompt Engineering Best Practices](modules/04-prompt-engineering/README.md) | 45 min |
| 05 | [Evaluation & Testing GenAI Outputs](modules/05-evaluation-testing/README.md) | 90 min |
| 06 | [Observability & Monitoring](modules/06-observability/README.md) | 45 min |
| 07 | [Building a Production App](modules/07-production-app/README.md) | 90 min |
| 08 | [CI/CD for GenAI Pipelines](modules/08-cicd/README.md) | 45 min |
| 09 | [Responsible AI & Governance](modules/09-responsible-ai/README.md) | 30 min |

---

## Learning Journey

```
Risk-Storm → Manage Test Data → Prototype → Understand Code → Engineer → Test → Ship
```

Each module is **self-contained** with:
- A clear learning outcome (including a QE-specific perspective)
- Step-by-step instructions
- Concrete examples you can run
- A short exercise to consolidate learning

---

## Prerequisites

- A Google Cloud project with the Vertex AI API enabled
- Python 3.10+
- Ability to read Python code; writing experience helpful but not required
- No prior GenAI experience required

---

## How to Use This Course

1. Work through modules **in order** — each builds on the last.
2. Run every code example yourself; learning by doing is the point.
3. Complete the exercise at the end of each module before moving on.
4. The `examples/` folder inside each module contains working, runnable code.

---

## Repository Layout

```
.
├── README.md                  ← you are here
├── modules/
│   ├── 00-overview/
│   ├── 01-risk-storming/
│   ├── 01b-test-data-management/  ← new
│   ├── 02-vertex-ai-studio/
│   ├── 03-python-scripting/
│   ├── 04-prompt-engineering/
│   ├── 05-evaluation-testing/
│   ├── 06-observability/
│   ├── 07-production-app/
│   ├── 08-cicd/
│   └── 09-responsible-ai/
└── shared/
    ├── requirements.txt
    └── utils/
```
