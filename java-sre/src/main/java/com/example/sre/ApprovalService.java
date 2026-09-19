package com.example.sre;
import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

@Service
public class ApprovalService {
 record Approval(String token,String incidentId,String action,String target,Instant expiresAt,boolean used){}
 private final ConcurrentHashMap<String,Approval> approvals=new ConcurrentHashMap<>();

 public String create(String incidentId,String action,String target){
  String t=UUID.randomUUID().toString();
  approvals.put(t,new Approval(t,incidentId,action,target,Instant.now().plusSeconds(900),false));
  return t;
 }
 public synchronized boolean consume(String token,String incidentId,String action,String target){
  Approval a=approvals.get(token);
  if(a==null||a.used()||Instant.now().isAfter(a.expiresAt())) return false;
  if(!a.incidentId().equals(incidentId)||!a.action().equals(action)||!a.target().equals(target)) return false;
  approvals.put(token,new Approval(a.token(),a.incidentId(),a.action(),a.target(),a.expiresAt(),true));
  return true;
 }
}