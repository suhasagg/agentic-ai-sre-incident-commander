package com.example.sre;
import java.util.Map;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/approvals")
public class ApprovalController {
 private final ApprovalService approvals;
 public ApprovalController(ApprovalService a){this.approvals=a;}
 public record Request(String incidentId,String action,String target){}
 @PostMapping public Map<String,String> create(@RequestBody Request r){
  // Demo endpoint. Production: authenticate an authorized human/incident commander here.
  return Map.of("approvalToken",approvals.create(r.incidentId(),r.action(),r.target()),"expiresIn","900s");
 }
}