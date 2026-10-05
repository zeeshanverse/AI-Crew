-- AI-Crew operating-system domain tables
CREATE TABLE IF NOT EXISTS vendors (
 id BIGSERIAL PRIMARY KEY,
 name VARCHAR(255) NOT NULL,
 category VARCHAR(120),
 contact VARCHAR(255),
 status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
 notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_metrics (
 id BIGSERIAL PRIMARY KEY,
 metric_name VARCHAR(255) NOT NULL,
 value NUMERIC(18,4) NOT NULL DEFAULT 0,
 unit VARCHAR(40),
 period VARCHAR(80),
 notes TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS finance_transactions (
 id BIGSERIAL PRIMARY KEY,
 type VARCHAR(20) NOT NULL,
 category VARCHAR(120) NOT NULL,
 amount NUMERIC(18,2) NOT NULL,
 description TEXT,
 transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at);
