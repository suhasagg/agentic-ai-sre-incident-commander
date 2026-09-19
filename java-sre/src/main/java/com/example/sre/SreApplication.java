package com.example.sre;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
@SpringBootApplication
public class SreApplication {
 public static void main(String[] a){SpringApplication.run(SreApplication.class,a);}
 @Bean ToolCallbackProvider tools(SreToolService s){
  return MethodToolCallbackProvider.builder().toolObjects(s).build();
 }
}