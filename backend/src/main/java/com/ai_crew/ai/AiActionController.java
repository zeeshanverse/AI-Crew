package com.ai_crew.ai;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.sql.Date;
import java.time.LocalDate;
import java.util.*;

@RestController
@RequestMapping("/api/ai/internal")
public class AiActionController {
    private final JdbcTemplate db;
    @Value("${ai_crew.internal-token:ai-crew-internal}")
    private String internalToken;

    public AiActionController(JdbcTemplate db) { this.db = db; }

    private void guard(String token) {
        if (!Objects.equals(token, internalToken)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Internal AI access denied");
        }
    }

    private String text(Map<String,Object> b, String key, String fallback) {
        Object v = b.get(key); return v == null ? fallback : String.valueOf(v).trim();
    }
    private void required(Map<String,Object> b, String key) {
        if (text(b,key,"").isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, key+" is required");
    }
    private BigDecimal decimal(Map<String,Object> b, String key) {
        Object v=b.get(key);
        if(v==null || String.valueOf(v).isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,key+" is required");
        try { return new BigDecimal(String.valueOf(v)); } catch(Exception e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,key+" must be numeric"); }
    }
    private Long longValue(Object v, String key) {
        if(v==null || String.valueOf(v).isBlank()) return null;
        try { return Long.valueOf(String.valueOf(v)); } catch(Exception e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,key+" must be numeric"); }
    }
    private Map<String,Object> one(String sql,Object... args) {
        List<Map<String,Object>> rows=db.queryForList(sql,args);
        if(rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Record not found");
        return rows.get(0);
    }

    @GetMapping("/company-context")
    public Map<String,Object> companyContext(@RequestHeader(value="X-AI-Crew-Internal", required=false) String token) {
        guard(token);
        Map<String,Object> out = new LinkedHashMap<>();
        out.put("goals", db.queryForList("SELECT id,title,description,created_at FROM goals ORDER BY created_at DESC LIMIT 20"));
        out.put("projects", db.queryForList("SELECT id,name,description,status,created_at FROM projects ORDER BY created_at DESC LIMIT 20"));
        out.put("tasks", db.queryForList("SELECT t.id,t.title,t.description,t.status,t.assigned_agent,t.project_id,p.name AS project_name FROM tasks t LEFT JOIN projects p ON p.id=t.project_id ORDER BY t.created_at DESC LIMIT 30"));
        out.put("metrics", db.queryForList("SELECT id,metric_name,value,unit,period,notes FROM business_metrics ORDER BY created_at DESC LIMIT 30"));
        out.put("vendors", db.queryForList("SELECT id,name,category,status,notes FROM vendors ORDER BY created_at DESC LIMIT 20"));
        out.put("finance", Map.of(
            "income", db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='INCOME'", BigDecimal.class),
            "expense", db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='EXPENSE'", BigDecimal.class)
        ));
        out.put("knowledge", db.queryForList("SELECT id,title,content FROM documents ORDER BY created_at DESC LIMIT 20"));
        return out;
    }

    @PostMapping("/actions/execute")
    public Map<String,Object> execute(
            @RequestHeader(value="X-AI-Crew-Internal", required=false) String token,
            @RequestHeader(value="X-AI-Crew-Agent", required=false) String agent,
            @RequestBody Map<String,Object> body) {
        guard(token);
        String tool = text(body,"tool","");
        @SuppressWarnings("unchecked") Map<String,Object> a = body.get("arguments") instanceof Map ? (Map<String,Object>) body.get("arguments") : Map.of();
        Map<String,Object> result = switch(tool) {
            case "create_goal" -> createGoal(a);
            case "create_project" -> createProject(a);
            case "create_task" -> createTask(a);
            case "create_metric" -> createMetric(a);
            case "create_vendor" -> createVendor(a);
            case "record_transaction" -> createTransaction(a);
            case "create_knowledge_document" -> createDocument(a);
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Unsupported AI action: "+tool);
        };
        try {
            db.update("INSERT INTO ai_action_audit(agent_code,tool_name,arguments,result,status) VALUES(?,?,?::jsonb,?::jsonb,?)",
                agent == null ? "UNKNOWN" : agent, tool, new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(a),
                new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result), "COMPLETED");
        } catch (Exception ignored) {}
        return result;
    }

    private Map<String,Object> createGoal(Map<String,Object> b) {
        required(b,"title");
        Long id=db.queryForObject("INSERT INTO goals(title,description) VALUES(?,?) RETURNING id",Long.class,text(b,"title",""),text(b,"description",""));
        return one("SELECT id,title,description,created_at FROM goals WHERE id=?",id);
    }
    private Map<String,Object> createProject(Map<String,Object> b) {
        required(b,"name");
        Long id=db.queryForObject("INSERT INTO projects(name,description,status) VALUES(?,?,?) RETURNING id",Long.class,text(b,"name",""),text(b,"description",""),text(b,"status","PLANNED"));
        return one("SELECT id,name,description,status,created_at FROM projects WHERE id=?",id);
    }
    private Map<String,Object> createTask(Map<String,Object> b) {
        required(b,"title");
        Long projectId=longValue(b.get("projectId"),"projectId");
        Long id=db.queryForObject("INSERT INTO tasks(title,description,status,assigned_agent,project_id) VALUES(?,?,?,?,?) RETURNING id",Long.class,text(b,"title",""),text(b,"description",""),text(b,"status","TODO"),text(b,"assignedAgent",null),projectId);
        return one("SELECT id,title,description,status,assigned_agent,project_id,created_at FROM tasks WHERE id=?",id);
    }
    private Map<String,Object> createMetric(Map<String,Object> b) {
        required(b,"metricName");
        Long id=db.queryForObject("INSERT INTO business_metrics(metric_name,value,unit,period,notes) VALUES(?,?,?,?,?) RETURNING id",Long.class,text(b,"metricName",""),decimal(b,"value"),text(b,"unit",""),text(b,"period",""),text(b,"notes",""));
        return one("SELECT id,metric_name,value,unit,period,notes,created_at FROM business_metrics WHERE id=?",id);
    }
    private Map<String,Object> createVendor(Map<String,Object> b) {
        required(b,"name");
        Long id=db.queryForObject("INSERT INTO vendors(name,category,contact,status,notes) VALUES(?,?,?,?,?) RETURNING id",Long.class,text(b,"name",""),text(b,"category",""),text(b,"contact",""),text(b,"status","ACTIVE"),text(b,"notes",""));
        return one("SELECT id,name,category,contact,status,notes,created_at FROM vendors WHERE id=?",id);
    }
    private Map<String,Object> createTransaction(Map<String,Object> b) {
        required(b,"type"); required(b,"category");
        String type=text(b,"type","EXPENSE").toUpperCase();
        if(!Set.of("INCOME","EXPENSE").contains(type)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"type must be INCOME or EXPENSE");
        Date date=Date.valueOf(text(b,"transactionDate", LocalDate.now().toString()));
        Long id=db.queryForObject("INSERT INTO finance_transactions(type,category,amount,description,transaction_date) VALUES(?,?,?,?,?) RETURNING id",Long.class,type,text(b,"category",""),decimal(b,"amount"),text(b,"description",""),date);
        return one("SELECT id,type,category,amount,description,transaction_date,created_at FROM finance_transactions WHERE id=?",id);
    }
    private Map<String,Object> createDocument(Map<String,Object> b) {
        required(b,"title"); required(b,"content");
        Long id=db.queryForObject("INSERT INTO documents(title,content) VALUES(?,?) RETURNING id",Long.class,text(b,"title",""),text(b,"content",""));
        return one("SELECT id,title,content,created_at FROM documents WHERE id=?",id);
    }
}
