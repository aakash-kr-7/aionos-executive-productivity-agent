# Evaluation Plan

A reviewer can evaluate the prototype on five dimensions:

| Dimension | Observable behavior |
|---|---|
| Commitment extraction | Five canonical commitment/action objects are recovered from messy multi-source inputs |
| Deduplication | Vendor list appears once despite repeated meeting/email/voice mentions |
| Ownership | Mumbai lease is explicitly unresolved rather than assigned by guess |
| Temporal reasoning | Vendor-list slippage and Thursday deck review are represented using the supplied week |
| Grounding | Q&A answers expose evidence excerpts and an audit ID |

## Suggested automated metrics for a larger version

- commitment precision / recall
- deadline exact-match accuracy
- owner exact-match accuracy
- duplicate-collapse ratio
- evidence coverage (% of answer claims with evidence)
- unsupported-claim rate
- ambiguous-case preservation rate
