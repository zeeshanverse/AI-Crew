package com.ai_crew.goal;
import jakarta.validation.constraints.NotBlank;
public record GoalRequest(@NotBlank String title, String description) {}
