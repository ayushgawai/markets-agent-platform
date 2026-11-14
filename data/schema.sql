-- Postgres + pgvector schema (applied by app owner in production; tests use in-memory)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS docs  (id TEXT PRIMARY KEY, source TEXT, text TEXT, embedding vector(128));
CREATE TABLE IF NOT EXISTS turns (conv TEXT, role TEXT, text TEXT, embedding vector(128));
CREATE INDEX IF NOT EXISTS docs_vec ON docs USING ivfflat (embedding vector_cosine_ops);
