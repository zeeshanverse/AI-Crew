package com.ai_crew;
import com.ai_crew.agent.AgentController;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class AgentControllerTest {
  @Test void catalogHasFiveInitialAgents() {
    var controller = new AgentController();
    assertEquals(5, controller.all().size());
    assertEquals("CEO", controller.all().get(0).code());
  }
}
