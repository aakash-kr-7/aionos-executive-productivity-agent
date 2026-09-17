# AI Tools Used

The project is designed so the reviewer can run it without external AI credentials.

## AI-assisted development

AI coding assistance may be used to accelerate scaffolding, UI implementation, testing and documentation. The final runtime does not depend on a hosted model.

## Runtime agent boundary

`app/agent.py` is the language-agent boundary. It currently uses transparent intent rules so every answer can be audited. In a production version, an LLM would perform intent classification and natural-language response generation with a strict structured-output schema, while `app/engine.py` would remain the source-of-truth reconciliation and safety layer.

## Why this split

A model should help interpret language; it should not silently invent an owner, deadline or commitment. The source/evidence graph is therefore deterministic and inspectable.
