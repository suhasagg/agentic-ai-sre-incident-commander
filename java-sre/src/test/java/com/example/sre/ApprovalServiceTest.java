package com.example.sre;
import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;
class ApprovalServiceTest {
 @Test void tokenIsOneTimeAndBoundToAction(){
  var a=new ApprovalService();
  var t=a.create("INC-1","rollback_deployment","checkout");
  assertTrue(a.consume(t,"INC-1","rollback_deployment","checkout"));
  assertFalse(a.consume(t,"INC-1","rollback_deployment","checkout"));
 }
 @Test void wrongTargetDenied(){
  var a=new ApprovalService();
  var t=a.create("INC-1","rollback_deployment","checkout");
  assertFalse(a.consume(t,"INC-1","rollback_deployment","payments"));
 }
}