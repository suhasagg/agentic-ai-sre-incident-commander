from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .models import Runbook
client=AsyncOpenAI(api_key=settings.openai_api_key)

async def embed(text):
    r=await client.embeddings.create(model=settings.embedding_model,input=text)
    return r.data[0].embedding

async def ingest(db: AsyncSession, docs):
    for d in docs:
        v=await embed(d.text)
        old=await db.get(Runbook,d.id)
        if old:
            old.service,old.title,old.text,old.embedding=d.service,d.title,d.text,v
        else:
            db.add(Runbook(id=d.id,service=d.service,title=d.title,text=d.text,embedding=v))
    await db.commit()

async def search_runbooks(db: AsyncSession, service: str, query: str, k=4):
    v=await embed(query)
    dist=Runbook.embedding.cosine_distance(v)
    q=(select(Runbook,dist.label("distance"))
       .where(Runbook.service==service).order_by(dist).limit(k))
    rows=(await db.execute(q)).all()
    return [{"id":r.id,"title":r.title,"text":r.text,"score":float(1-d)} for r,d in rows]
