import json
from dataclasses import dataclass
from agents import Agent, Runner, function_tool
from agents.mcp import MCPServerStreamableHttp
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .rag import search_runbooks

@dataclass
class IncidentContext:
    incident_id: str
    service: str
    severity: str
    db: AsyncSession
    approval_token: str | None = None

def build(ctx: IncidentContext, mcp):
    @function_tool
    async def search_runbook(query: str) -> str:
        """Search operational runbooks for the affected service."""
        return json.dumps(await search_runbooks(ctx.db,ctx.service,query))

    triage=Agent(
        name="Triage Agent", model=settings.openai_model,
        instructions="Classify symptoms, blast radius, urgency and immediate safety concerns. Do not mutate systems.")

    investigator=Agent(
        name="Investigator Agent", model=settings.openai_model,
        instructions=("Investigate using read-only SRE MCP tools and runbooks. Correlate metrics, logs, "
                      "pods, deployment history and events. State evidence, timestamps and uncertainty."),
        tools=[search_runbook], mcp_servers=[mcp])

    rca=Agent(
        name="Root Cause Agent", model=settings.openai_model,
        instructions=("Generate ranked hypotheses from supplied evidence. Separate correlation from causation. "
                      "For each hypothesis give supporting/refuting evidence and next discriminating check."))

    planner=Agent(
        name="Remediation Planner", model=settings.openai_model,
        instructions=("Propose the least risky reversible remediation. Include preconditions, expected effect, "
                      "verification, rollback and whether human approval is needed. Never execute."))

    executor=Agent(
        name="Execution Agent", model=settings.openai_model,
        instructions=("Execute only the explicitly requested remediation using MCP. Pass the supplied approval "
                      "token when a tool requires it. Never invent approval. Never claim success without tool confirmation."),
        mcp_servers=[mcp])

    verifier=Agent(
        name="Verification Agent", model=settings.openai_model,
        instructions=("Use read-only MCP tools to verify SLO recovery after an action. Compare latency, error rate, "
                      "availability, pod health and deployment state. Recommend rollback/escalation if not recovered."),
        mcp_servers=[mcp])

    commander=Agent(
        name="Incident Commander", model=settings.openai_model,
        instructions=("Coordinate an SRE incident. Delegate triage, investigation, root-cause analysis and remediation "
                      "planning. Do NOT call mutating execution tools during investigation. Produce structured sections: "
                      "Situation, Evidence, Hypotheses, Recommended Action, Approval Requirement, Verification Plan."),
        tools=[
            triage.as_tool(tool_name="triage",tool_description="Assess severity and blast radius."),
            investigator.as_tool(tool_name="investigate",tool_description="Gather telemetry and runbook evidence."),
            rca.as_tool(tool_name="root_cause_analysis",tool_description="Develop evidence-based root-cause hypotheses."),
            planner.as_tool(tool_name="remediation_plan",tool_description="Design safe reversible remediation.")
        ])
    return commander,executor,verifier

async def investigate(ctx: IncidentContext, incident_text: str):
    async with MCPServerStreamableHttp(
        name="sre-action-plane",
        params={"url":settings.sre_mcp_url,"headers":{"X-Incident-Id":ctx.incident_id},"timeout":20},
        cache_tools_list=True,max_retry_attempts=2) as mcp:
        commander,_,_=build(ctx,mcp)
        r=await Runner.run(commander,incident_text)
        return str(r.final_output)

async def execute(ctx: IncidentContext, instruction: str):
    headers={"X-Incident-Id":ctx.incident_id}
    if ctx.approval_token: headers["X-Approval-Token"]=ctx.approval_token
    async with MCPServerStreamableHttp(
        name="sre-action-plane",
        params={"url":settings.sre_mcp_url,"headers":headers,"timeout":20},
        cache_tools_list=True,max_retry_attempts=1) as mcp:
        _,executor,_=build(ctx,mcp)
        r=await Runner.run(executor,
            f"Incident={ctx.incident_id}; service={ctx.service}; instruction={instruction}; "
            f"approval_token={ctx.approval_token or 'NONE'}")
        return str(r.final_output)

async def verify(ctx: IncidentContext, action_result: str):
    async with MCPServerStreamableHttp(
        name="sre-action-plane",
        params={"url":settings.sre_mcp_url,"headers":{"X-Incident-Id":ctx.incident_id},"timeout":20},
        cache_tools_list=True) as mcp:
        *_,verifier=build(ctx,mcp)
        r=await Runner.run(verifier,
            f"Verify service {ctx.service} after this action result:\n{action_result}")
        return str(r.final_output)
