package com.ai_crew.agent;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/agents")
public class AgentController {
  private final List<Agent> agents = List.of(
    new Agent(1L,"CEO","CEO AI","EXECUTIVE","Sets company goals, priorities and strategic direction."),
    new Agent(2L,"MANAGER","Manager AI","MANAGEMENT","Breaks goals into plans, tasks and coordinates agents."),
    new Agent(3L,"BUSINESS_ANALYST","Business Analyst AI","BUSINESS","Analyzes KPIs, data, opportunities and business performance."),
    new Agent(4L,"SOFTWARE_ENGINEER","Software Engineer AI","ENGINEERING","Designs, builds, tests and improves software."),
    new Agent(5L,"RESEARCH","Research AI","RESEARCH","Researches markets, competitors, technologies and external information.")
  );

  @GetMapping
  public List<Agent> all() {
    return agents;
  }
}
