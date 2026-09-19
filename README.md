# Agentic AI SRE / Autonomous Incident Commander

Production-style Python + Java reference implementation for an AI-assisted SRE incident response platform.

## Features

- Multi-agent incident command:
  - Triage Agent
  - Investigator Agent
  - Root Cause Agent
  - Remediation Planner
  - Execution Agent
  - Verification Agent
  - Incident Commander / Supervisor
- OpenAI Agents SDK
- MCP Streamable HTTP integration
- Java 21 + Spring Boot + Spring AI 2.x MCP action plane
- Prometheus-style metrics/log/event investigation tools
- Kubernetes-style read and remediation tools
- Runbook RAG using PostgreSQL + pgvector
- Human approval tokens for high-risk remediation
- Idempotent action execution
- Incident state machine + durable audit trail
- Redis
- Prometheus metrics
- Docker Compose
- Offline evaluation harness
- Unit tests

## Architecture

```text
Alerts / API
    |
    v
Python FastAPI Incident Control Plane :8000
    |
    +--> Incident Commander
          |
          +--> Triage Agent
          +--> Investigator Agent -----> Runbook RAG / pgvector
          +--> Root Cause Agent
          +--> Remediation Planner
          +--> Execution Agent --------> Java SRE MCP :8081/mcp
          +--> Verification Agent              |
                                               +-- metrics
                                               +-- logs
                                               +-- deployments
                                               +-- pods
                                               +-- restart deployment
                                               +-- rollback deployment
                                               +-- scale deployment
                                               `-- approval enforcement

PostgreSQL: incidents, events, audit log, runbooks
Redis: cache / coordination
Prometheus: service metrics
```

## Safety model

The LLM **cannot authorize its own dangerous action**. Mutating Java tools require an externally created approval token for high-risk operations. The token is validated and consumed in the Java action plane.

This is important: "ask the model to be careful" is not a security boundary.

## Quick start

```bash
cp .env.example .env
# Add OPENAI_API_KEY
docker compose up --build
```

Seed runbooks:

```bash
curl -X POST localhost:8000/v1/runbooks \
  -H 'Content-Type: application/json' \
  -d '{"runbooks":[{"id":"latency-01","service":"checkout","title":"Checkout latency","text":"If p95 latency rises after a deployment, compare deployment timestamps, error rate and pod restarts. Prefer rollback only after confirming correlation."}]}'
```

Create incident:

```bash
curl -X POST localhost:8000/v1/incidents \
 -H 'Content-Type: application/json' \
 -d '{"service":"checkout","severity":"SEV2","summary":"p95 latency above 2 seconds and 5xx increasing"}'
```

Investigate:

```bash
curl -X POST localhost:8000/v1/incidents/<ID>/investigate
```

Approve a proposed high-risk action:

```bash
curl -X POST localhost:8081/api/approvals \
 -H 'Content-Type: application/json' \
 -d '{"incidentId":"<ID>","action":"rollback_deployment","target":"checkout"}'
```

Then execute with the approval token through:

```bash
curl -X POST localhost:8000/v1/incidents/<ID>/execute \
 -H 'Content-Type: application/json' \
 -d '{"instruction":"Rollback checkout to the previous stable revision.","approval_token":"TOKEN"}'
```

## Important

The included Kubernetes/Prometheus/log backends are safe in-memory simulators so the repo runs locally without a real cluster. The interfaces are intentionally shaped so you can replace them with:
- Kubernetes Java client
- Prometheus HTTP API
- Loki / Elasticsearch
- Azure Monitor / Application Insights
- PagerDuty / Opsgenie
- ServiceNow / Jira

See `docs/PRODUCTION.md`.


---

# Engineering Guide

## 1. Executive Architecture View

**Purpose.** Investigates incidents using telemetry and runbooks, produces evidence-backed RCA, proposes remediation, enforces approval and verifies recovery.

The repository deliberately separates **probabilistic AI reasoning** from **deterministic enterprise controls**. Model outputs may propose plans, rank evidence, summarize observations or choose among permitted tools, but identity, tenancy, authorization, approval, idempotency, rate limits and destructive-action boundaries belong to ordinary software.

### Control Plane vs Data / Action Plane

| Plane | Responsibilities |
|---|---|
| AI / Control Plane | Request interpretation, planning, routing, model invocation, agent coordination, evaluation hooks |
| Context Plane | Retrieval, memory, telemetry, documents, evidence and provenance |
| Policy Plane | Tenant context, RBAC/scopes, risk classification, approval and quotas |
| Action Plane | Narrow Java APIs/MCP tools that perform enterprise operations |
| State Plane | PostgreSQL/pgvector and Redis where used |
| Observability Plane | Metrics, traces, audit events, health and evaluation evidence |

### Trust Boundaries

```text
Untrusted user/content
        |
        v
API validation / identity
        |
        v
AI reasoning boundary
        |
        v
Policy + tool schema boundary
        |
        v
MCP / Java action boundary
        |
        v
Enterprise systems / durable state
```

A production implementation should assume that user prompts, retrieved documents, tool outputs and model-generated arguments can all be hostile or malformed.

## 2. Repository Structure

```text
.env.example
.gitignore
Makefile
README.md
docker-compose.yml
docs/
  INTERVIEW.md
  PRODUCTION.md
evals/
  dataset.json
  evaluate.py
java-sre/
  Dockerfile
  pom.xml
  src/
    main/
    test/
python-commander/
  Dockerfile
  app/
    __init__.py
    agents.py
    config.py
    database.py
    main.py
    models.py
    rag.py
    schemas.py
  requirements.txt
  tests/
    test_contracts.py
```

## 3. End-to-End Request Lifecycle

1. **Ingress** — validate request shape, establish tenant/principal context and attach a correlation id.
2. **Context assembly** — load only the memory, documents, telemetry or metadata required for the task.
3. **AI decision** — invoke the configured model/agent using structured contracts where possible.
4. **Policy decision** — independently check tool/model entitlement, risk, tenant and approval requirements.
5. **Execution** — invoke a narrow downstream API or MCP tool with bounded timeout/retry behavior.
6. **Verification** — validate tool result, citations, tests, health signals or other task-specific evidence.
7. **Persistence** — store durable domain state and minimal audit/evaluation evidence.
8. **Response** — return a stable API contract without leaking provider credentials or internal secrets.

## 4. API Surface

| Method | Endpoint | Service |
|---|---|---|
| `ON_EVENT` | `startup` | Python API |
| `GET` | `/health` | Python API |
| `POST` | `/v1/runbooks` | Python API |
| `POST` | `/v1/incidents` | Python API |
| `POST` | `/v1/incidents/{iid}/investigate` | Python API |
| `POST` | `/v1/incidents/{iid}/execute` | Python API |
| `GET` | `/v1/incidents/{iid}` | Python API |
| `POST` | `/` | Java API |

MCP tools form a separate typed API surface. The Java tool classes and Python MCP client/runtime are the authoritative definitions for those schemas.

## 5. Configuration

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Runtime configuration |
| `OPENAI_MODEL` | Runtime configuration |
| `EMBEDDING_MODEL` | Runtime configuration |
| `DATABASE_URL` | Runtime configuration |
| `REDIS_URL` | Runtime configuration |
| `SRE_MCP_URL` | Runtime configuration |

Use a secrets manager or workload identity in production. Never place long-lived service credentials inside prompts, model instructions or model-visible tool arguments.

## 6. Local Development

```bash
docker compose up --build
```

Useful test commands:

```bash
make python-test
make java-test
```

If a target is not defined in the Makefile, run `pytest` in the Python service and `mvn test` in the Java service.

## 7. Reliability Engineering

Production hardening should include:

- Explicit deadlines for model, database, MCP and downstream calls.
- Bounded retries with exponential backoff and jitter.
- Idempotency keys for every mutation that may be retried.
- Circuit breaking for unhealthy providers or downstream services.
- Cancellation propagation for abandoned requests.
- Concurrency limits to prevent retry storms and resource exhaustion.
- Persistent evidence for ambiguous failures where the caller cannot know whether a side effect committed.
- Schema/version compatibility checks between Python and Java boundaries.
- Graceful degradation when optional AI capabilities are unavailable.

## 8. Security & Governance

- Replace development tokens with OAuth/OIDC or workload identity.
- Validate tenant authorization at **every** storage and action boundary.
- Give agents narrow tools rather than unrestricted database/shell/cloud credentials.
- Treat RAG documents, webpages, images and tool results as untrusted data.
- Add enterprise DLP/PII controls; regex examples are not a complete DLP solution.
- Enforce egress allowlists and SSRF protection in connector services.
- Require human approval and separation of duties for high-impact actions.
- Redact secrets and sensitive payloads from traces.
- Export audit events to immutable/WORM storage when compliance requires it.

## 9. Observability

Correlate the following with a request/workflow/task/incident id:

| Signal | Examples |
|---|---|
| AI | model/provider, latency, tokens, tool calls, retries |
| Retrieval | query latency, candidate count, rerank latency, citations |
| Tools | tool name, decision, latency, success/failure, approval wait |
| Platform | HTTP latency, DB latency, queue depth, Redis errors |
| Business | task success, incident recovery, workflow completion, eval gate |
| Cost | input/output tokens, model cost, tool/infrastructure cost |

Do not log raw prompts or documents by default when they can contain confidential information.

## 10. Testing Strategy

### Deterministic software tests
Unit-test schemas, policy, routing, parsing, idempotency and tool adapters.

### Integration tests
Exercise PostgreSQL/pgvector, Redis, MCP/API contracts and provider adapters.

### AI evaluations
Use versioned datasets for correctness, groundedness, tool selection, citation behavior and refusal/safety behavior.

### Failure and security tests
Inject timeouts, duplicate requests, provider outages, malformed tool output, prompt injection, cross-tenant requests and approval bypass attempts.

## 11. Scaling and Production Topology

Separate investigation from privileged remediation workers, use durable incident state, distributed mutation locks and idempotency keys.

A typical production topology is:

```text
Global / Regional Load Balancer
            |
     Stateless API replicas
            |
    +-------+--------+
    |                |
AI workers       Policy services
    |                |
Retrieval        Approval/Audit
    |
Java/MCP tool services
    |
Enterprise systems

Managed PostgreSQL / Vector Store
Managed Redis
OpenTelemetry Collector
Secrets / Workload Identity
```

## 12. Key Trade-Off

More autonomy can reduce MTTR but increases blast radius; this design favors bounded actions, approval, rollback and verification.

The architecture should be evaluated on a **quality × latency × cost × reliability × security** frontier rather than optimizing model quality alone.

## 13. CI/CD and Deployment Roadmap

```text
Pull Request
   |
lint + unit tests
   |
integration tests
   |
AI/security eval gates
   |
container build + SBOM
   |
staging / shadow traffic
   |
canary
   |
production
   |
SLO + eval monitoring
```

Recommended next production steps:

- Kubernetes/Helm or a managed container platform.
- Workload identity and centralized secrets.
- OpenTelemetry propagation across Python → MCP → Java.
- Schema registry/versioning for tool contracts.
- Per-tenant quotas and cost budgets.
- Durable audit/event retention.
- Load tests and chaos/failure tests.
- Model/prompt/tool-policy canary rollout and rollback.
- Anonymized production-trace sampling into evaluation datasets.


1. Why Python owns AI-heavy orchestration while Java owns enterprise/action-plane concerns.
2. Which decisions must remain deterministic and outside the model.
3. Tenant identity propagation and confused-deputy prevention.
4. Idempotency under retries and ambiguous side-effect failures.
5. Provider/MCP failure modes and graceful degradation.
6. Schema evolution across polyglot services.
7. Human approval and separation-of-duties design.
8. Quality evaluation independent of uptime/latency.
9. Cost controls and token/tool-call budgets.
10. 10×/100× scaling and multi-region/data-residency changes.
11. Observability without leaking confidential prompts.
12. Threat modeling for prompt injection and poisoned tool/RAG content.

## 15. Portfolio Description

> **Agentic AI SRE / Autonomous Incident Commander** — Designed and implemented a Python/Java enterprise AI reference platform with explicit control-plane/action-plane boundaries, production-oriented reliability, security/governance, observability, testing and AI evaluation patterns. 

## 16. Production Disclaimer

This is a reference implementation. Before production use, pin and verify SDK/model versions, perform full dependency and container security scans, run end-to-end integration/load/security tests, and integrate the platform with the organization's real identity, secrets, policy, audit, DLP and compliance systems.
