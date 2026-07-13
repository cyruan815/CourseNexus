# ADR 0005: Simplified Complete-Context Generation POC

## Status

Accepted for the current POC.

## Decision

The five independent generation modules use one complete selected-material context and one structured LLM call per request. Item-level citations, map/reduce, and citation persistence are removed from this POC path. Context overflow fails explicitly before the model call.

Mindmap preprocessing runs in the backend through official `markmap-lib`; the persisted preprocessed tree is rendered by frontend `markmap-view`.

## Consequences

The implementation is smaller and directly validates product feasibility. Very large selections must be reduced by the user. Course QA and future study-plan flows may retain their own retrieval or batching strategies; this ADR governs the five independent generated-content modules only.
