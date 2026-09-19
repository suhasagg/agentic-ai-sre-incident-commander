import uuid,time
from fastapi import FastAPI,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import Counter,Histogram,make_asgi_app
from .database import init_db,get_db
from .models import Incident,IncidentEvent
from .schemas import IncidentCreate,ExecuteRequest,RunbookRequest
from .rag import ingest
from .agents import IncidentContext,investigate,execute,verify

REQ=Counter("incident_commander_requests_total","Requests",["operation"])
LAT=Histogram("incident_commander_seconds","Latency",["operation"])

app=FastAPI(title="Agentic AI SRE Incident Commander",version="1.0.0")
app.mount("/metrics",make_asgi_app())

@app.on_event("startup")
async def startup(): await init_db()

@app.get("/health")
async def health(): return {"status":"ok"}

@app.post("/v1/runbooks")
async def runbooks(req:RunbookRequest,db:AsyncSession=Depends(get_db)):
    await ingest(db,req.runbooks); return {"ingested":len(req.runbooks)}

@app.post("/v1/incidents")
async def create(req:IncidentCreate,db:AsyncSession=Depends(get_db)):
    iid="INC-"+uuid.uuid4().hex[:10]
    obj=Incident(id=iid,service=req.service,severity=req.severity,summary=req.summary,status="OPEN")
    db.add(obj); db.add(IncidentEvent(incident_id=iid,kind="CREATED",payload=req.model_dump()))
    await db.commit()
    return {"id":iid,"status":"OPEN"}

async def get_incident(db,iid):
    x=await db.get(Incident,iid)
    if not x: raise HTTPException(404,"incident not found")
    return x

@app.post("/v1/incidents/{iid}/investigate")
async def investigate_incident(iid:str,db:AsyncSession=Depends(get_db)):
    REQ.labels("investigate").inc(); start=time.perf_counter()
    inc=await get_incident(db,iid); inc.status="INVESTIGATING"
    ctx=IncidentContext(iid,inc.service,inc.severity,db)
    answer=await investigate(ctx,f"Service: {inc.service}\nSeverity: {inc.severity}\nSymptoms: {inc.summary}")
    inc.analysis={"investigation":answer}; inc.status="MITIGATION_PROPOSED"
    db.add(IncidentEvent(incident_id=iid,kind="AI_INVESTIGATION",payload={"answer":answer}))
    await db.commit(); LAT.labels("investigate").observe(time.perf_counter()-start)
    return {"incident_id":iid,"analysis":answer,"status":inc.status}

@app.post("/v1/incidents/{iid}/execute")
async def execute_action(iid:str,req:ExecuteRequest,db:AsyncSession=Depends(get_db)):
    inc=await get_incident(db,iid)
    ctx=IncidentContext(iid,inc.service,inc.severity,db,req.approval_token)
    result=await execute(ctx,req.instruction)
    verification=await verify(ctx,result)
    inc.status="MONITORING"
    inc.analysis={**(inc.analysis or {}),"execution":result,"verification":verification}
    db.add(IncidentEvent(incident_id=iid,kind="REMEDIATION",payload={
        "instruction":req.instruction,"result":result,"verification":verification}))
    await db.commit()
    return {"incident_id":iid,"execution":result,"verification":verification,"status":inc.status}

@app.get("/v1/incidents/{iid}")
async def incident(iid:str,db:AsyncSession=Depends(get_db)):
    x=await get_incident(db,iid)
    return {"id":x.id,"service":x.service,"severity":x.severity,"summary":x.summary,
            "status":x.status,"analysis":x.analysis}
