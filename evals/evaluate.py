import json,os,httpx
base=os.getenv("API","http://localhost:8000")
cases=json.load(open("dataset.json"))
passed=0
for c in cases:
 r=httpx.post(base+"/v1/incidents",json={k:c[k] for k in ("service","severity","summary")},timeout=20)
 r.raise_for_status(); iid=r.json()["id"]
 x=httpx.post(f"{base}/v1/incidents/{iid}/investigate",timeout=180); x.raise_for_status()
 answer=x.json()["analysis"]
 ok=all(s.lower() in answer.lower() for s in c["expected"])
 print("PASS" if ok else "FAIL",c["id"],answer[:200].replace("\n"," "))
 passed+=ok
print(f"{passed}/{len(cases)} passed")
