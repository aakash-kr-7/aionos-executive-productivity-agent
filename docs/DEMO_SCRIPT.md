# 15-Minute Demo & Defence

## 0:00–1:00 — Problem
“Executives do not have a data shortage. They have fragmented commitments. The same action can appear in a meeting, an email and a voice memo, while ownership and deadlines drift.”

## 1:00–3:00 — Architecture
Show the source → evidence → extraction → reconciliation → ownership gate → deadline engine → brief flow.

## 3:00–6:00 — Daily brief
Open the dashboard. Point out:
- updated vendor list: Arjun action, stale/open
- July expense variance review: Arjun action, report delivered
- Mumbai lease: unclear ownership, Friday deadline
- Meridian call: completed
- campaign deck: dependency on Neha with a fixed Thursday 9:30 review

## 6:00–9:00 — Grounded Q&A
Ask:
1. “What did I promise Raghav?”
2. “What needs action today?”
3. “What about the Mumbai lease?”

Open evidence on each answer.

## 9:00–11:00 — Deduplication
Show the vendor list. Explain that four separate source mentions become one canonical action, not four tasks.

## 11:00–13:00 — Safety / ambiguity
Explain why the lease owner is blank. The data pack says the item is unassigned; Divya only says she believes it typically sits with Facilities; Arjun says not to assume. The agent preserves uncertainty.

## 13:00–15:00 — Defence
### Why not let an LLM decide everything?
Because the highest-risk mistakes are invented ownership and silently changed deadlines. Deterministic reconciliation provides a verifiable backbone; an LLM can sit on top for language understanding and summarization.

### What makes this agentic?
It does more than retrieve text: it decomposes inputs into evidence, extracts candidate commitments, reconciles them, applies ownership/deadline gates, produces a brief, and answers follow-up questions against the resulting state.

### What would you build next?
Connector adapters for real Gmail/Calendar/Slack/voice systems, a persistent event store, LLM-assisted extraction with structured outputs, human approval for outbound actions, and evaluation sets for extraction precision/recall and grounding.
