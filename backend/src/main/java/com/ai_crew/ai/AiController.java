package com.ai_crew.ai;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@RestController
@RequestMapping("/api/ai")
public class AiController {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final JdbcTemplate db;

    @Value("${ai_crew.ai-service-url}")
    private String aiServiceUrl;

    public AiController(ObjectMapper objectMapper, JdbcTemplate db) {
        this.restTemplate = new RestTemplate();
        this.objectMapper = objectMapper;
        this.db = db;
    }


    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(
                    aiServiceUrl + "/health",
                    Map.class
            );
            Map<String, Object> body = response.getBody();
            return ResponseEntity.ok(body == null ? Map.of("status", "unknown") : body);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(Map.of("status", "unavailable", "mode", "unknown"));
        }
    }

    @PostMapping("/run")
    public ResponseEntity<String> run(
            @RequestBody Map<String, Object> request) throws Exception {

        // Convert incoming request to real JSON
        String json = objectMapper.writeValueAsString(request);

        // Explicitly tell FastAPI that this is JSON
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));

        HttpEntity<String> entity = new HttpEntity<>(json, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + "/agents/run",
                    entity,
                    String.class
            );

            String body = response.getBody();
            String agent = String.valueOf(request.getOrDefault("agent", "CEO")).toUpperCase();
            try {
                db.update("INSERT INTO agent_runs(agent_code,input,output,status) VALUES(?,?::jsonb,?::jsonb,?)",
                        agent, json, body == null ? "{}" : body, response.getStatusCode().is2xxSuccessful() ? "COMPLETED" : "FAILED");
            } catch (Exception ignored) {
                // Run history must never make a successful AI request fail.
            }
            return ResponseEntity
                    .status(response.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body);
        } catch (ResourceAccessException e) {
            // AI service is down or unreachable
            return ResponseEntity
                    .status(HttpStatus.BAD_GATEWAY)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body("{\"error\":\"AI service is unreachable\"}");
        } catch (RestClientResponseException e) {
            // AI service responded with an error status
            return ResponseEntity
                    .status(e.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(e.getResponseBodyAsString());
        }
    }
    @PostMapping("/actions/execute")
    public ResponseEntity<String> executeAction(@RequestBody Map<String,Object> request) throws Exception {
        String json = objectMapper.writeValueAsString(request);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setAccept(java.util.List.of(MediaType.APPLICATION_JSON));
        try {
            ResponseEntity<String> response = restTemplate.postForEntity(
                    aiServiceUrl + "/actions/execute",
                    new HttpEntity<>(json, headers),
                    String.class
            );
            return ResponseEntity.status(response.getStatusCode()).contentType(MediaType.APPLICATION_JSON).body(response.getBody());
        } catch (ResourceAccessException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).contentType(MediaType.APPLICATION_JSON).body("{\"error\":\"AI service is unreachable\"}");
        } catch (RestClientResponseException e) {
            return ResponseEntity.status(e.getStatusCode()).contentType(MediaType.APPLICATION_JSON).body(e.getResponseBodyAsString());
        }
    }

}
