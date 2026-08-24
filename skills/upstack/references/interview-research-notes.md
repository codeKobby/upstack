# Interview-preparation research notes

## Source framing

The learner supplied a transcript from [this video](https://youtu.be/SNYRibAVwqo). The transcript argues that software-engineering interviews are not disappearing, but that evaluation is moving upward from typing syntax toward implementation judgment, system design, debugging, code reading, communication, trade-offs, and defending decisions. It describes coding challenges, system-design conversations, scratch-pad or whiteboard work, company-specific domain questions, multi-file codebases, and follow-up questions. It also emphasizes that AI-use rules differ by employer.

The transcript’s numeric claims and anecdotes are retained as source context, not universal market facts. Upstack must not claim that a specific question is guaranteed to appear or that a social-video statistic predicts a learner’s interview.

## External evidence

| Source | What it supports | Reliability use |
| --- | --- | --- |
| [Anthropic candidate AI guidance](https://www.anthropic.com/candidate-ai-guidance) | AI may be used for interview preparation; live interviews are no-AI unless indicated otherwise; authentic experience and transparent use matter. | Official employer policy for Anthropic; never generalize to another employer. |
| [Canva engineering interview redesign](https://www.canva.dev/blog/engineering/yes-you-can-use-ai-in-our-interviews/) | Some employers explicitly expect AI-assisted technical interviews; realistic ambiguity, requirement clarification, review, debugging, and judgment can be assessed with AI. | Official employer engineering article; an example of one process, not a universal rule. |
| [Amazon SDE II interview preparation](https://www.amazon.jobs/content/en/how-we-hire/sde-ii-interview-prep) | One employer’s published format includes technical questions, system design, work-style/behavioral evaluation, syntactically correct code, tests, edge cases, scalability, and STAR-style behavioral preparation. | Official employer preparation page; use only when the target is Amazon/SDE II or as an explicitly labelled example. |
| [Pragmatic Engineer interview preparation](https://blog.pragmaticengineer.com/preparing-for-the-systems-design-and-coding-interviews/) | Coding preparation is broadly relevant; system-design expectations vary with seniority; mock interviews and hands-on practice help. | Reputable practitioner guidance; general preparation context, not a company forecast. |
| [Wiz software-engineer question guide](https://www.wiz.io/academy/cloud-careers/software-engineer-interview-questions) | Useful rubric dimensions: correctness, complexity, edge cases, security, reliability, debugging, testing, code review, collaboration, and behavior. | Employer academy/preparation content; use for rubric design, not as evidence of a target company’s upcoming questions. |
| [Intuit engineering interview questions](https://www.intuit.com/blog/innovative-thinking/60-engineering-interview-questions-to-expect-and-12-to-ask-during-your-job-search/) | Common categories include background, technical, soft-skill, and questions for the interviewer. | Employer career content; broad question examples, not a leak or guarantee. |
| [Tech Interview Handbook final questions](https://www.techinterviewhandbook.org/final-questions/) | Candidates should prepare questions about team problems, technical decisions, success measures, role expectations, and growth. | Practitioner/interviewer guidance; use for the candidate-question stage. |

## Evidence hierarchy for Upstack

1. **Verified requirement:** the user-provided job description, recruiter packet, official company careers/interview page, or explicit recruiter statement.
2. **Company-specific official signal:** employer-authored guidance that describes a process, competency, policy, or role expectation.
3. **High-confidence public pattern:** repeated, recent, attributable candidate reports or reputable interview research that matches the target role and level.
4. **Plausible practice question:** a question derived from job requirements and established role patterns but not reported as asked.
5. **Practice-only analogue:** an original question created to train the same competency.

Never label levels 3–5 as the exact question that will be asked. Preserve source URL, source type, publication/retrieval date, role/level, company, evidence excerpt or reason, and confidence. Contradictory sources remain visible and lower confidence rather than being silently reconciled.

## Product requirements derived from the research

The interview route should first collect the target job description or requirements, company, role, level, interview date or horizon, location/process information, candidate experience, target technologies, and known AI-use policy. It should then extract competencies and build a question plan across coding/algorithms, system design, debugging and code reading, practical implementation or pair programming, role/domain knowledge, behavioral/project deep dive, and candidate questions. The categories must be selected from the actual requirements rather than always shown in full.

Before practice, the learner chooses a mode: coached learning, mock interview, or assessment. Coached learning may explain what the question probes before the attempt. Mock and assessment modes should preserve the attempt before revealing a full solution. After every attempt, Upstack should state the verdict, rubric dimensions, evidence, first incorrect assumption or step, why it matters, a hint or smaller correction, acceptable approaches, trade-offs, a stronger answer or patch only at the requested reveal level, and one nearby follow-up that tests transfer.

Support inline feedback and Markdown output. Markdown should preserve the prompt, evidence basis, question classification, learner answer, code or response block, rubric, correction, improved answer, follow-up, and progress. Never rewrite an answer as though the learner authored the correction. Use no-AI mock mode when the target policy requires it and permitted-AI practice when the target policy explicitly allows it.

Recommended local state:

```text
.upstack/interview/
├── JOB_REQUIREMENTS.md
├── EVIDENCE_MAP.md
├── INTERVIEW_BLUEPRINT.md
├── QUESTION_BANK.md
├── MOCK_LOG.md
├── FEEDBACK.md
└── progress.json
```
