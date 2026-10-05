package com.ai_crew.goal;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.OffsetDateTime;

@Entity
@Table(name = "goals")
public class GoalEntity {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false)
  private String title;

  @Column(columnDefinition = "TEXT")
  private String description;

  @Column(name = "created_at", insertable = false, updatable = false)
  private OffsetDateTime createdAt;

  protected GoalEntity() {
    // required by JPA
  }

  public GoalEntity(String title, String description) {
    this.title = title;
    this.description = description;
  }

  public Long getId() {
    return id;
  }

  public void setTitle(String title) { this.title = title; }

  public void setDescription(String description) { this.description = description; }

  public String getTitle() {
    return title;
  }

  public String getDescription() {
    return description;
  }

  public OffsetDateTime getCreatedAt() {
    return createdAt;
  }
}
