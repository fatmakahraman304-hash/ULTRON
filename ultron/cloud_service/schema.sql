CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content TEXT NOT NULL,
  device_id TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS memories (
  user_id TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'FACT',
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_by_device TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(user_id, key)
);
CREATE INDEX IF NOT EXISTS idx_memories_user_updated ON memories(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  device_id TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_commands (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  target TEXT NOT NULL CHECK (target IN ('desktop','phone')),
  command TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_device TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','delivered')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  delivered_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_device_commands_pending
  ON device_commands(user_id, target, status, id);

-- Upgrade older command queues in place so the UI can report real progress.
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS result JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE device_commands
  DROP CONSTRAINT IF EXISTS device_commands_status_check;
ALTER TABLE device_commands
  ADD CONSTRAINT device_commands_status_check
  CHECK (status IN ('queued','delivered','completed','failed','cancelled','expired'));

CREATE TABLE IF NOT EXISTS device_presence (
  user_id TEXT NOT NULL,
  device TEXT NOT NULL CHECK (device IN ('desktop','phone')),
  state JSONB NOT NULL DEFAULT '{}'::jsonb,
  last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY(user_id, device)
);
CREATE INDEX IF NOT EXISTS idx_device_presence_seen
  ON device_presence(user_id, last_seen DESC);

