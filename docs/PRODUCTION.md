# Production hardening

## Replace simulator adapters
- Metrics -> Prometheus HTTP API / Azure Monitor
- Logs -> Loki, Elasticsearch or Application Insights
- Kubernetes -> official Kubernetes Java client
- Incidents -> PagerDuty / ServiceNow
- Runbooks -> Azure AI Search or governed vector store

## Security
- Put OAuth/OIDC in front of MCP HTTP.
- Use Entra ID / workload identity.
- Never expose cluster-admin credentials to an LLM.
- Separate read-only telemetry identity from remediation identity.
- Enforce approval in deterministic code, not prompts.
- Bind approval to incident + exact action + target + parameters + TTL.
- Record approver identity and immutable audit events.
- Validate tool arguments and service allowlists.
- Protect against prompt injection in logs/runbooks.

## Reliability
- Durable workflow engine for long incidents
- Idempotency keys for mutations
- action leases / distributed locks
- retry budgets and circuit breakers
- reconciliation after ambiguous tool timeout
- dead-letter queues
- explicit incident state machine

## Evaluation
Evaluate:
- correct tool selection
- evidence grounding
- false root-cause rate
- unsafe-action rate
- approval bypass rate (must be zero)
- mean tool calls / incident
- time to diagnosis
- time to mitigation
- token cost
- recovery verification accuracy

## Principal-level discussion
Be prepared to explain:
- why MCP is a trust boundary, not a security boundary
- why the model cannot self-approve
- how to handle a timeout after a Kubernetes mutation
- how to avoid two agents remediating simultaneously
- how to bound blast radius
- how to replay/audit decisions
- how to evaluate incident agents against historical incidents
