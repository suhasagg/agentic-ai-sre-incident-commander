# Principal Engineer interview talking points

1. Control plane and action plane are deliberately separated.
2. Read tools and write tools should use different credentials and policies.
3. Agent reasoning is probabilistic; authorization is deterministic.
4. High-risk actions require externally issued, one-time, scoped approval.
5. Every remediation must have verification and rollback.
6. Tool timeout after mutation creates an ambiguous-outcome problem: reconcile state before retrying.
7. Production execution requires idempotency keys and distributed action locks.
8. RAG runbooks provide institutional context but are untrusted input and must not override policy.
9. Historical incident replay is the foundation of offline agent evaluation.
10. SLO recovery—not eloquent LLM output—is the operational success metric.
