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
  ADD COLUMN IF NOT EXISTS progress JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS max_retries INTEGER NOT NULL DEFAULT 2;
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS run_after TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
-- Each claim receives a monotonically increasing fencing generation.
-- A stale worker from a prior lease cannot ack, renew, report or checkpoint
-- a task that has since been claimed again by a different worker.
ALTER TABLE device_commands
  ADD COLUMN IF NOT EXISTS delivery_attempt INTEGER NOT NULL DEFAULT 0;
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



CREATE TABLE IF NOT EXISTS speaker_profiles (
  user_id TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  embedding JSONB NOT NULL,
  sample_count INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Owner-authorized development requests. A mobile user cannot declare CI
-- success or a desktop installation by changing request JSON.
CREATE TABLE IF NOT EXISTS dev_requests (
  id UUID PRIMARY KEY,
  user_id TEXT NOT NULL,
  prompt TEXT NOT NULL CHECK (length(prompt) BETWEEN 12 AND 2000),
  target TEXT NOT NULL CHECK (target IN ('phone','desktop','both')),
  source_device TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'awaiting_chatgpt' CHECK (
    status IN ('awaiting_chatgpt','tests_pending','tests_failed',
               'release_pending','desktop_pending','completed')
  ),
  commit_sha TEXT NOT NULL DEFAULT '',
  desktop_sha TEXT NOT NULL DEFAULT '',
  verified_tests BOOLEAN NOT NULL DEFAULT FALSE,
  verified_cloud BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dev_requests_owner_time
  ON dev_requests(user_id,created_at DESC);


-- One record per locally routed conversation turn; no duplicate assistant messages.
CREATE TABLE IF NOT EXISTS local_chat_requests (
  command_id BIGINT PRIMARY KEY REFERENCES device_commands(id),
  user_id TEXT NOT NULL,
  conversation_id UUID NOT NULL,
  reply_saved BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_local_chat_requests_user ON local_chat_requests(user_id, command_id DESC);


-- Explicit owner-created manual plans. Not an external calendar sync or alarm queue.
CREATE TABLE IF NOT EXISTS owner_plans (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 140),
  scheduled_date DATE NOT NULL,
  scheduled_time TIME,
  note TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 500),
  is_done BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_owner_plans_user_date
  ON owner_plans(user_id, scheduled_date, scheduled_time, id);


-- Review inbox for explicitly owner-approved learning.
-- A pending/rejected entry is NOT part of assistant memories.
CREATE TABLE IF NOT EXISTS learning_proposals (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('PREFERENCE','PROJECT','GOAL','FACT','DEVICE')),
  key TEXT NOT NULL CHECK (length(key) BETWEEN 1 AND 120),
  value TEXT NOT NULL CHECK (length(value) BETWEEN 1 AND 1000),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reviewed_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_learning_pending_owner_key
  ON learning_proposals(user_id,key) WHERE status='pending';
CREATE INDEX IF NOT EXISTS idx_learning_owner_recent
  ON learning_proposals(user_id,id DESC);


-- Private, reversible, default-off learning switch. No surveillance/background job.
CREATE TABLE IF NOT EXISTS owner_auto_learning (
  user_id TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Editable, user-approved notes are NOT model-visible memories.
-- Retain notes only while the original owner's conversation exists.
CREATE TABLE IF NOT EXISTS conversation_notes (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 140),
  body TEXT NOT NULL CHECK(length(body) BETWEEN 1 AND 3000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversation_notes_owner_conversation
  ON conversation_notes(user_id,conversation_id,id DESC);
