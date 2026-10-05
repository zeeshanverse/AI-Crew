package com.ai_crew.operations;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.sql.Date;
import java.time.LocalDate;
import java.util.*;

@RestController
@RequestMapping("/api")
public class OperationsController {
    private final JdbcTemplate db;

    public OperationsController(JdbcTemplate db) { this.db = db; }

    private String text(Map<String,Object> b, String key, String fallback) {
        Object v=b.get(key); return v == null ? fallback : String.valueOf(v).trim();
    }
    private void required(Map<String,Object> b, String key) {
        if (text(b,key,"").isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, key+" is required");
    }
    private BigDecimal decimal(Map<String,Object> b, String key) {
        Object v=b.get(key);
        if (v == null || String.valueOf(v).isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,key+" is required");
        try { return new BigDecimal(String.valueOf(v)); } catch(Exception e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,key+" must be numeric"); }
    }
    private Long id(Map<String,Object> b) {
        Object v=b.get("id");
        try { return Long.valueOf(String.valueOf(v)); } catch(Exception e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Invalid id"); }
    }
    private Map<String,Object> one(String sql,Object... args) {
        List<Map<String,Object>> rows=db.queryForList(sql,args);
        if(rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND,"Record not found");
        return rows.get(0);
    }

    // ---------------- Projects ----------------
    @GetMapping("/projects")
    public List<Map<String,Object>> projects() {
        return db.queryForList("SELECT id,name,description,status,created_at FROM projects ORDER BY created_at DESC");
    }
    @PostMapping("/projects")
    public Map<String,Object> createProject(@RequestBody Map<String,Object> b) {
        required(b,"name");
        Long id=db.queryForObject("INSERT INTO projects(name,description,status) VALUES(?,?,?) RETURNING id",
                Long.class,text(b,"name",""),text(b,"description",""),text(b,"status","PLANNED"));
        return one("SELECT id,name,description,status,created_at FROM projects WHERE id=?",id);
    }
    @PutMapping("/projects/{id}")
    public Map<String,Object> updateProject(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"name");
        db.update("UPDATE projects SET name=?,description=?,status=? WHERE id=?",
                text(b,"name",""),text(b,"description",""),text(b,"status","PLANNED"),id);
        return one("SELECT id,name,description,status,created_at FROM projects WHERE id=?",id);
    }
    @DeleteMapping("/projects/{id}")
    public Map<String,Object> deleteProject(@PathVariable long id) {
        db.update("DELETE FROM tasks WHERE project_id=?",id);
        db.update("DELETE FROM projects WHERE id=?",id);
        return Map.of("deleted",true,"id",id);
    }

    // ---------------- Tasks ----------------
    @GetMapping("/tasks")
    public List<Map<String,Object>> tasks() {
        return db.queryForList("""
            SELECT t.id,t.title,t.description,t.status,t.assigned_agent,t.project_id,
                   p.name AS project_name,t.created_at
            FROM tasks t LEFT JOIN projects p ON p.id=t.project_id
            ORDER BY t.created_at DESC
            """);
    }
    @PostMapping("/tasks")
    public Map<String,Object> createTask(@RequestBody Map<String,Object> b) {
        required(b,"title");
        String agent=text(b,"assignedAgent",null);
        Long project=b.get("projectId")==null||String.valueOf(b.get("projectId")).isBlank()?null:Long.valueOf(String.valueOf(b.get("projectId")));
        Long id=db.queryForObject("INSERT INTO tasks(title,description,status,assigned_agent,project_id) VALUES(?,?,?,?,?) RETURNING id",
                Long.class,text(b,"title",""),text(b,"description",""),text(b,"status","TODO"),agent,project);
        return one("SELECT id,title,description,status,assigned_agent,project_id,created_at FROM tasks WHERE id=?",id);
    }
    @PutMapping("/tasks/{id}")
    public Map<String,Object> updateTask(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"title");
        String agent=text(b,"assignedAgent",null);
        Long project=b.get("projectId")==null||String.valueOf(b.get("projectId")).isBlank()?null:Long.valueOf(String.valueOf(b.get("projectId")));
        db.update("UPDATE tasks SET title=?,description=?,status=?,assigned_agent=?,project_id=? WHERE id=?",
                text(b,"title",""),text(b,"description",""),text(b,"status","TODO"),agent,project,id);
        return one("SELECT id,title,description,status,assigned_agent,project_id,created_at FROM tasks WHERE id=?",id);
    }
    @DeleteMapping("/tasks/{id}")
    public Map<String,Object> deleteTask(@PathVariable long id) {
        db.update("DELETE FROM tasks WHERE id=?",id);
        return Map.of("deleted",true,"id",id);
    }

    // ---------------- Vendors ----------------
    @GetMapping("/vendors")
    public List<Map<String,Object>> vendors() {
        return db.queryForList("SELECT id,name,category,contact,status,notes,created_at FROM vendors ORDER BY created_at DESC");
    }
    @PostMapping("/vendors")
    public Map<String,Object> createVendor(@RequestBody Map<String,Object> b) {
        required(b,"name");
        Long id=db.queryForObject("INSERT INTO vendors(name,category,contact,status,notes) VALUES(?,?,?,?,?) RETURNING id",
                Long.class,text(b,"name",""),text(b,"category",""),text(b,"contact",""),text(b,"status","ACTIVE"),text(b,"notes",""));
        return one("SELECT id,name,category,contact,status,notes,created_at FROM vendors WHERE id=?",id);
    }
    @PutMapping("/vendors/{id}")
    public Map<String,Object> updateVendor(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"name");
        db.update("UPDATE vendors SET name=?,category=?,contact=?,status=?,notes=? WHERE id=?",
                text(b,"name",""),text(b,"category",""),text(b,"contact",""),text(b,"status","ACTIVE"),text(b,"notes",""),id);
        return one("SELECT id,name,category,contact,status,notes,created_at FROM vendors WHERE id=?",id);
    }
    @DeleteMapping("/vendors/{id}")
    public Map<String,Object> deleteVendor(@PathVariable long id) {
        db.update("DELETE FROM vendors WHERE id=?",id); return Map.of("deleted",true,"id",id);
    }

    // ---------------- Business ----------------
    @GetMapping("/business/metrics")
    public List<Map<String,Object>> metrics() {
        return db.queryForList("SELECT id,metric_name,value,unit,period,notes,created_at FROM business_metrics ORDER BY created_at DESC");
    }
    @PostMapping("/business/metrics")
    public Map<String,Object> createMetric(@RequestBody Map<String,Object> b) {
        required(b,"metricName");
        BigDecimal value=decimal(b,"value");
        Long id=db.queryForObject("INSERT INTO business_metrics(metric_name,value,unit,period,notes) VALUES(?,?,?,?,?) RETURNING id",
                Long.class,text(b,"metricName",""),value,text(b,"unit",""),text(b,"period",""),text(b,"notes",""));
        return one("SELECT id,metric_name,value,unit,period,notes,created_at FROM business_metrics WHERE id=?",id);
    }
    @PutMapping("/business/metrics/{id}")
    public Map<String,Object> updateMetric(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"metricName");
        db.update("UPDATE business_metrics SET metric_name=?,value=?,unit=?,period=?,notes=? WHERE id=?",
                text(b,"metricName",""),decimal(b,"value"),text(b,"unit",""),text(b,"period",""),text(b,"notes",""),id);
        return one("SELECT id,metric_name,value,unit,period,notes,created_at FROM business_metrics WHERE id=?",id);
    }
    @DeleteMapping("/business/metrics/{id}")
    public Map<String,Object> deleteMetric(@PathVariable long id) {
        db.update("DELETE FROM business_metrics WHERE id=?",id); return Map.of("deleted",true,"id",id);
    }
    @GetMapping("/business/summary")
    public Map<String,Object> businessSummary() {
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("projects", db.queryForObject("SELECT COUNT(*) FROM projects",Long.class));
        out.put("openTasks", db.queryForObject("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('DONE','COMPLETED')",Long.class));
        out.put("completedTasks", db.queryForObject("SELECT COUNT(*) FROM tasks WHERE status IN ('DONE','COMPLETED')",Long.class));
        out.put("vendors", db.queryForObject("SELECT COUNT(*) FROM vendors",Long.class));
        return out;
    }

    // ---------------- Finance ----------------
    @GetMapping("/finance/transactions")
    public List<Map<String,Object>> transactions() {
        return db.queryForList("SELECT id,type,category,amount,description,transaction_date,created_at FROM finance_transactions ORDER BY transaction_date DESC,created_at DESC");
    }
    @PostMapping("/finance/transactions")
    public Map<String,Object> createTransaction(@RequestBody Map<String,Object> b) {
        required(b,"type"); required(b,"category");
        String type=text(b,"type","EXPENSE").toUpperCase();
        if(!Set.of("INCOME","EXPENSE").contains(type)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"type must be INCOME or EXPENSE");
        String date=text(b,"transactionDate",LocalDate.now().toString());
        Long id=db.queryForObject("INSERT INTO finance_transactions(type,category,amount,description,transaction_date) VALUES(?,?,?,?,?) RETURNING id",
                Long.class,type,text(b,"category",""),decimal(b,"amount"),text(b,"description",""),Date.valueOf(date));
        return one("SELECT id,type,category,amount,description,transaction_date,created_at FROM finance_transactions WHERE id=?",id);
    }
    @PutMapping("/finance/transactions/{id}")
    public Map<String,Object> updateTransaction(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"type"); required(b,"category");
        String type=text(b,"type","EXPENSE").toUpperCase();
        db.update("UPDATE finance_transactions SET type=?,category=?,amount=?,description=?,transaction_date=? WHERE id=?",
                type,text(b,"category",""),decimal(b,"amount"),text(b,"description",""),Date.valueOf(text(b,"transactionDate",LocalDate.now().toString())),id);
        return one("SELECT id,type,category,amount,description,transaction_date,created_at FROM finance_transactions WHERE id=?",id);
    }
    @DeleteMapping("/finance/transactions/{id}")
    public Map<String,Object> deleteTransaction(@PathVariable long id) {
        db.update("DELETE FROM finance_transactions WHERE id=?",id); return Map.of("deleted",true,"id",id);
    }
    @GetMapping("/finance/summary")
    public Map<String,Object> financeSummary() {
        BigDecimal income=db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='INCOME'",BigDecimal.class);
        BigDecimal expense=db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='EXPENSE'",BigDecimal.class);
        return Map.of("income",income,"expense",expense,"balance",income.subtract(expense));
    }

    // ---------------- Knowledge ----------------
    @GetMapping("/knowledge/documents")
    public List<Map<String,Object>> documents() {
        return db.queryForList("SELECT id,title,content,created_at FROM documents ORDER BY created_at DESC");
    }
    @PostMapping("/knowledge/documents")
    public Map<String,Object> createDocument(@RequestBody Map<String,Object> b) {
        required(b,"title"); required(b,"content");
        Long id=db.queryForObject("INSERT INTO documents(title,content) VALUES(?,?) RETURNING id",
                Long.class,text(b,"title",""),text(b,"content",""));
        return one("SELECT id,title,content,created_at FROM documents WHERE id=?",id);
    }
    @PutMapping("/knowledge/documents/{id}")
    public Map<String,Object> updateDocument(@PathVariable long id,@RequestBody Map<String,Object> b) {
        required(b,"title"); required(b,"content");
        db.update("UPDATE documents SET title=?,content=? WHERE id=?",text(b,"title",""),text(b,"content",""),id);
        return one("SELECT id,title,content,created_at FROM documents WHERE id=?",id);
    }
    @DeleteMapping("/knowledge/documents/{id}")
    public Map<String,Object> deleteDocument(@PathVariable long id) {
        db.update("DELETE FROM documents WHERE id=?",id); return Map.of("deleted",true,"id",id);
    }
    @GetMapping("/knowledge/search")
    public List<Map<String,Object>> searchKnowledge(@RequestParam(defaultValue="") String q) {
        if(q.isBlank()) return documents();
        String term="%"+q.toLowerCase()+"%";
        return db.queryForList("SELECT id,title,content,created_at FROM documents WHERE LOWER(title) LIKE ? OR LOWER(content) LIKE ? ORDER BY created_at DESC",term,term);
    }

    // ---------------- Dashboard ----------------
    @GetMapping("/dashboard")
    public Map<String,Object> dashboard() {
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("agents", db.queryForObject("SELECT COUNT(*) FROM (SELECT 'CEO' UNION ALL SELECT 'MANAGER' UNION ALL SELECT 'BUSINESS_ANALYST' UNION ALL SELECT 'SOFTWARE_ENGINEER' UNION ALL SELECT 'RESEARCH') x",Long.class));
        out.put("goals", db.queryForObject("SELECT COUNT(*) FROM goals",Long.class));
        out.put("projects", db.queryForObject("SELECT COUNT(*) FROM projects",Long.class));
        out.put("tasks", db.queryForObject("SELECT COUNT(*) FROM tasks",Long.class));
        out.put("openTasks", db.queryForObject("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('DONE','COMPLETED')",Long.class));
        out.put("vendors", db.queryForObject("SELECT COUNT(*) FROM vendors",Long.class));
        out.put("knowledge", db.queryForObject("SELECT COUNT(*) FROM documents",Long.class));
        BigDecimal income=db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='INCOME'",BigDecimal.class);
        BigDecimal expense=db.queryForObject("SELECT COALESCE(SUM(amount),0) FROM finance_transactions WHERE type='EXPENSE'",BigDecimal.class);
        out.put("income",income); out.put("expense",expense); out.put("balance",income.subtract(expense));
        return out;
    }

    // ---------------- Agent run history ----------------
    @GetMapping("/runs")
    public List<Map<String,Object>> runs() {
        return db.queryForList("SELECT id,agent_code,input,output,status,created_at FROM agent_runs ORDER BY created_at DESC LIMIT 50");
    }
}
