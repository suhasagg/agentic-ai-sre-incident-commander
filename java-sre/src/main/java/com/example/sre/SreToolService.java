package com.example.sre;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

@Service
public class SreToolService {
 private final ApprovalService approvals;
 private final Map<String,Deployment> deployments=new ConcurrentHashMap<>();

 public SreToolService(ApprovalService approvals){
  this.approvals=approvals;
  deployments.put("checkout",new Deployment("checkout","checkout:v42",6,6,"Healthy",Instant.now().minusSeconds(600).toString()));
  deployments.put("payments",new Deployment("payments","payments:v18",4,4,"Healthy",Instant.now().minusSeconds(7200).toString()));
 }

 @Tool(description="Read current service metrics including p95 latency, error rate and availability. Read-only.")
 public Metrics getServiceMetrics(@ToolParam(description="Service name") String service){
  if(service.equals("checkout")) return new Metrics(service,2.35,0.072,99.10,Instant.now().toString());
  return new Metrics(service,0.18,0.003,99.99,Instant.now().toString());
 }

 @Tool(description="Search recent application logs for a service and query. Read-only.")
 public List<LogLine> searchLogs(String service,String query,int minutes){
  if(service.equals("checkout")) return List.of(
   new LogLine(Instant.now().minusSeconds(90).toString(),"ERROR","upstream timeout calling inventory"),
   new LogLine(Instant.now().minusSeconds(70).toString(),"WARN","request latency exceeded 2000ms"));
  return List.of(new LogLine(Instant.now().minusSeconds(60).toString(),"INFO","healthy"));
 }

 @Tool(description="Get Kubernetes-style deployment state and current revision. Read-only.")
 public Deployment getDeployment(String service){
  return deployments.getOrDefault(service,new Deployment(service,"unknown",0,0,"NotFound",""));
 }

 @Tool(description="Get recent deployment history. Read-only.")
 public List<String> deploymentHistory(String service){
  if(service.equals("checkout")) return List.of("checkout:v42 deployed 10m ago","checkout:v41 deployed 3d ago");
  return List.of(service+": no recent rollout");
 }

 @Tool(description="List pod health for a service. Read-only.")
 public List<Pod> listPods(String service){
  Deployment d=getDeployment(service);
  List<Pod> p=new ArrayList<>();
  for(int i=0;i<Math.max(1,d.desiredReplicas());i++)
   p.add(new Pod(service+"-"+i,i==0&&service.equals("checkout")?"CrashLoopBackOff":"Running",i==0?5:0));
  return p;
 }

 @Tool(description="Restart a deployment. Mutating action. Requires incident id and may require approval.")
 public ActionResult restartDeployment(String incidentId,String service,String approvalToken){
  // restart is medium risk in demo; SEV policy can be strengthened in production.
  return new ActionResult(true,"restart_deployment",service,"Restart requested","act-"+UUID.randomUUID());
 }

 @Tool(description="Rollback a deployment to its previous stable revision. HIGH RISK. Requires a valid one-time human approval token.")
 public ActionResult rollbackDeployment(String incidentId,String service,String approvalToken){
  if(approvalToken==null||!approvals.consume(approvalToken,incidentId,"rollback_deployment",service))
   return new ActionResult(false,"rollback_deployment",service,"DENIED: valid human approval required","");
  Deployment old=getDeployment(service);
  String previous=old.image().replace("v42","v41");
  deployments.put(service,new Deployment(service,previous,old.desiredReplicas(),old.desiredReplicas(),"Healthy",Instant.now().toString()));
  return new ActionResult(true,"rollback_deployment",service,"Rolled back to "+previous,"act-"+UUID.randomUUID());
 }

 @Tool(description="Scale a deployment. HIGH RISK above 10 replicas. Requires approval token for large changes.")
 public ActionResult scaleDeployment(String incidentId,String service,int replicas,String approvalToken){
  if(replicas<1||replicas>50) return new ActionResult(false,"scale_deployment",service,"DENIED: replicas outside policy","");
  if(replicas>10 && (approvalToken==null||!approvals.consume(approvalToken,incidentId,"scale_deployment",service)))
   return new ActionResult(false,"scale_deployment",service,"DENIED: human approval required","");
  Deployment old=getDeployment(service);
  deployments.put(service,new Deployment(service,old.image(),replicas,replicas,"Healthy",Instant.now().toString()));
  return new ActionResult(true,"scale_deployment",service,"Scaled to "+replicas,"act-"+UUID.randomUUID());
 }

 public record Metrics(String service,double p95LatencySeconds,double errorRate,double availabilityPercent,String observedAt){}
 public record LogLine(String timestamp,String level,String message){}
 public record Pod(String name,String status,int restartCount){}
 public record Deployment(String service,String image,int desiredReplicas,int readyReplicas,String status,String updatedAt){}
 public record ActionResult(boolean success,String action,String target,String message,String actionId){}
}