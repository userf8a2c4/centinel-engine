-- Centinel Electoral Honduras — Supabase Schema
-- Ejecutar una sola vez en el proyecto Supabase (SQL Editor)
-- Run once in your Supabase project (SQL Editor)

-- ================================================================
-- TABLAS PÚBLICAS (lectura sin autenticación)
-- PUBLIC TABLES (read without authentication)
-- ================================================================

CREATE TABLE IF NOT EXISTS snapshots_public (
  id           BIGSERIAL PRIMARY KEY,
  captured_at  TIMESTAMPTZ NOT NULL,
  dept_code    TEXT,                    -- HN-FM, HN-CR, etc. (NULL = nacional)
  merkle_root  TEXT NOT NULL,
  chain_hash   TEXT NOT NULL,
  chain_length BIGINT,
  ots_proof    TEXT,                    -- base64 del .ots (NULL si pendiente)
  bitcoin_tx   TEXT,                    -- txid cuando confirme en Bitcoin
  anomaly_flag BOOLEAN DEFAULT FALSE,
  alert_state  TEXT DEFAULT 'normal',   -- normal / anomaly / hash_broken
  raw_meta     JSONB                    -- metadata adicional opcional
);

CREATE TABLE IF NOT EXISTS alerts_public (
  id          BIGSERIAL PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL,
  severity    TEXT NOT NULL,           -- LOW / MEDIUM / HIGH / CRITICAL
  rule_id     TEXT,
  kind        TEXT,                    -- tipo de anomalía (benford_deviation, etc.)
  description TEXT,
  dept_code   TEXT,
  snapshot_id BIGINT REFERENCES snapshots_public(id) ON DELETE SET NULL
);

-- ================================================================
-- TABLA UPNFM (solo usuarios autenticados con acceso otorgado)
-- UPNFM TABLE (only authenticated users with granted access)
-- ================================================================

CREATE TABLE IF NOT EXISTS upnfm_rules (
  id           BIGSERIAL PRIMARY KEY,
  created_by   UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  rule_name    TEXT NOT NULL,
  rule_yaml    TEXT NOT NULL,
  description  TEXT,
  is_active    BOOLEAN DEFAULT FALSE,
  test_result  JSONB,                   -- resultado del último /audit/rules/test
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de miembros UPNFM autorizados (manejada manualmente por el operador)
CREATE TABLE IF NOT EXISTS upnfm_members (
  id         BIGSERIAL PRIMARY KEY,
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name       TEXT,
  role       TEXT DEFAULT 'researcher', -- researcher / operator
  added_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- ROW LEVEL SECURITY (RLS)
-- ================================================================

ALTER TABLE snapshots_public ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts_public    ENABLE ROW LEVEL SECURITY;
ALTER TABLE upnfm_rules      ENABLE ROW LEVEL SECURITY;
ALTER TABLE upnfm_members    ENABLE ROW LEVEL SECURITY;

-- Eliminar policies si ya existen (idempotente)
DROP POLICY IF EXISTS "public_read_snapshots"    ON snapshots_public;
DROP POLICY IF EXISTS "public_read_alerts"       ON alerts_public;
DROP POLICY IF EXISTS "service_insert_snapshots" ON snapshots_public;
DROP POLICY IF EXISTS "service_insert_alerts"    ON alerts_public;
DROP POLICY IF EXISTS "service_update_snapshots" ON snapshots_public;
DROP POLICY IF EXISTS "upnfm_read_rules"         ON upnfm_rules;
DROP POLICY IF EXISTS "upnfm_insert_rules"       ON upnfm_rules;
DROP POLICY IF EXISTS "upnfm_update_own_rules"   ON upnfm_rules;
DROP POLICY IF EXISTS "upnfm_read_members"       ON upnfm_members;

-- Lectura pública sin auth
CREATE POLICY "public_read_snapshots"
  ON snapshots_public FOR SELECT USING (true);

CREATE POLICY "public_read_alerts"
  ON alerts_public FOR SELECT USING (true);

-- Solo el engine (service role) puede insertar/actualizar snapshots y alertas
CREATE POLICY "service_insert_snapshots"
  ON snapshots_public FOR INSERT
  WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_insert_alerts"
  ON alerts_public FOR INSERT
  WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "service_update_snapshots"
  ON snapshots_public FOR UPDATE
  USING (auth.role() = 'service_role');

-- Reglas UPNFM: solo miembros autorizados pueden leer/insertar
CREATE POLICY "upnfm_read_rules"
  ON upnfm_rules FOR SELECT
  USING (
    auth.uid() IN (SELECT user_id FROM upnfm_members)
    OR auth.role() = 'service_role'
  );

CREATE POLICY "upnfm_insert_rules"
  ON upnfm_rules FOR INSERT
  WITH CHECK (
    auth.uid() IN (SELECT user_id FROM upnfm_members)
  );

CREATE POLICY "upnfm_update_own_rules"
  ON upnfm_rules FOR UPDATE
  USING (
    created_by = auth.uid()
    OR auth.role() = 'service_role'
  );

CREATE POLICY "upnfm_read_members"
  ON upnfm_members FOR SELECT
  USING (auth.role() = 'service_role' OR auth.uid() IN (SELECT user_id FROM upnfm_members));

-- ================================================================
-- ÍNDICES
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_snapshots_captured_at ON snapshots_public(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_dept        ON snapshots_public(dept_code);
CREATE INDEX IF NOT EXISTS idx_snapshots_anomaly     ON snapshots_public(anomaly_flag) WHERE anomaly_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_alerts_created_at     ON alerts_public(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity       ON alerts_public(severity);

-- ================================================================
-- TRIGGER: actualizar updated_at en upnfm_rules
-- ================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER upnfm_rules_updated_at
  BEFORE UPDATE ON upnfm_rules
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ================================================================
-- MULTI-ORG: columnas org y access_level en upnfm_members
-- org: upnfm | unah | admin | external
-- access_level: admin | researcher | readonly
-- ================================================================

ALTER TABLE upnfm_members ADD COLUMN IF NOT EXISTS org TEXT DEFAULT 'upnfm';
ALTER TABLE upnfm_members ADD COLUMN IF NOT EXISTS access_level TEXT DEFAULT 'researcher';

-- ================================================================
-- REPLAY 2025: tabla privada de snapshots históricos
-- Solo usuarios en upnfm_members pueden leer (RLS)
-- ================================================================

CREATE TABLE IF NOT EXISTS replay_snapshots (
  id          BIGSERIAL PRIMARY KEY,
  captured_at TIMESTAMPTZ NOT NULL,
  dept_code   TEXT,
  raw_json    JSONB NOT NULL,
  source      TEXT DEFAULT 'nov2025',
  imported_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE replay_snapshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_replay_read"   ON replay_snapshots;
DROP POLICY IF EXISTS "service_replay_ins" ON replay_snapshots;

CREATE POLICY "auth_replay_read" ON replay_snapshots FOR SELECT
  USING (EXISTS (SELECT 1 FROM upnfm_members WHERE user_id = auth.uid()));

CREATE POLICY "service_replay_ins" ON replay_snapshots FOR INSERT
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_replay_captured_at ON replay_snapshots(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_replay_dept        ON replay_snapshots(dept_code);
