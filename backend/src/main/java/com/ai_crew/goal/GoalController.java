package com.ai_crew.goal;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/goals")
public class GoalController {
  private final GoalRepository repository;

  public GoalController(GoalRepository repository) {
    this.repository = repository;
  }

  @GetMapping
  public List<Goal> all() {
    return repository.findAll().stream()
        .map(g -> new Goal(g.getId(), g.getTitle(), g.getDescription()))
        .toList();
  }

  @PostMapping
  public Goal create(@Valid @RequestBody GoalRequest r) {
    GoalEntity saved = repository.save(new GoalEntity(r.title(), r.description()));
    return new Goal(saved.getId(), saved.getTitle(), saved.getDescription());
  }

  @PutMapping("/{id}")
  public Goal update(@PathVariable Long id, @Valid @RequestBody GoalRequest r) {
    GoalEntity entity = repository.findById(id).orElseThrow();
    entity.setTitle(r.title());
    entity.setDescription(r.description());
    GoalEntity saved = repository.save(entity);
    return new Goal(saved.getId(), saved.getTitle(), saved.getDescription());
  }

  @DeleteMapping("/{id}")
  public java.util.Map<String,Object> delete(@PathVariable Long id) {
    repository.deleteById(id);
    return java.util.Map.of("deleted", true, "id", id);
  }
}
