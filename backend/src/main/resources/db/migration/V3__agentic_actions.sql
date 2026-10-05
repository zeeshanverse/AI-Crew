CREATE TABLE IF NOT EXISTS ai_action_audit (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 agent_code VARCHAR(100) NOT NULL,
 tool_name VARCHAR(120) NOT NULL,
 arguments JSONB NOT NULL,
 result JSONB,
 status VARCHAR(40) NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_action_audit_created_at ON ai_action_audit(created_at);
