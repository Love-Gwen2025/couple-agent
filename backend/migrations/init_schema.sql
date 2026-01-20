-- =============================================
-- MyAgent 数据库初始化脚本
-- =============================================
-- 版本: 2.0.0
-- 包含: 用户、会话、消息、知识库、用户模型配置
-- 特点: 所有语句使用 IF NOT EXISTS，可重复执行
-- 执行: psql -U postgres -d my_agent -f init_schema.sql
-- =============================================

-- 启用 pgvector 扩展（用于向量检索）
CREATE EXTENSION IF NOT EXISTS vector;


-- =============================================
-- 1. 用户表 (t_user)
-- =============================================
CREATE TABLE IF NOT EXISTS t_user (
    id BIGINT PRIMARY KEY,
    user_code VARCHAR(100) NOT NULL UNIQUE,
    user_name VARCHAR(100) NOT NULL,
    user_password VARCHAR(255) NOT NULL,
    user_sex INTEGER DEFAULT 0,
    user_phone VARCHAR(20),
    address VARCHAR(500),
    max_login_num INTEGER DEFAULT 3,
    avatar VARCHAR(500),
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_user_code ON t_user(user_code);
CREATE INDEX IF NOT EXISTS idx_user_phone ON t_user(user_phone);

COMMENT ON TABLE t_user IS '用户表';
COMMENT ON COLUMN t_user.user_code IS '用户编码（唯一）';
COMMENT ON COLUMN t_user.user_name IS '用户名';
COMMENT ON COLUMN t_user.user_password IS '密码（加密存储）';
COMMENT ON COLUMN t_user.user_sex IS '性别: 0-未知, 1-男, 2-女';
COMMENT ON COLUMN t_user.max_login_num IS '最大同时登录数';


-- =============================================
-- 2. 会话表 (t_conversation)
-- =============================================
CREATE TABLE IF NOT EXISTS t_conversation (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(255),
    model_code VARCHAR(50),
    last_message_id BIGINT,
    last_message_at TIMESTAMP,
    ext JSONB,
    avatar VARCHAR(512),
    current_message_id BIGINT,
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON t_conversation(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_last_message_at ON t_conversation(last_message_at DESC);

COMMENT ON TABLE t_conversation IS '会话表';
COMMENT ON COLUMN t_conversation.user_id IS '所属用户 ID';
COMMENT ON COLUMN t_conversation.title IS '会话标题';
COMMENT ON COLUMN t_conversation.model_code IS '使用的模型编码';
COMMENT ON COLUMN t_conversation.ext IS '扩展信息（JSON）';


-- =============================================
-- 3. 消息表 (t_message)
-- =============================================
CREATE TABLE IF NOT EXISTS t_message (
    id BIGINT PRIMARY KEY,
    conversation_id BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'TEXT',
    token_count INTEGER DEFAULT 0,
    model_code VARCHAR(50),
    status INTEGER DEFAULT 1,
    parent_id BIGINT,
    checkpoint_id VARCHAR(100),
    ext JSONB,
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_message_conversation_id ON t_message(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_sender_id ON t_message(sender_id);
CREATE INDEX IF NOT EXISTS idx_message_create_time ON t_message(create_time DESC);
CREATE INDEX IF NOT EXISTS idx_message_parent_id ON t_message(parent_id);

COMMENT ON TABLE t_message IS '消息表';
COMMENT ON COLUMN t_message.conversation_id IS '所属会话 ID';
COMMENT ON COLUMN t_message.sender_id IS '发送者 ID（-1 表示 AI）';
COMMENT ON COLUMN t_message.role IS '角色: user/assistant/system';
COMMENT ON COLUMN t_message.content IS '消息内容';
COMMENT ON COLUMN t_message.content_type IS '内容类型: TEXT/IMAGE/FILE';
COMMENT ON COLUMN t_message.token_count IS 'Token 消耗数';
COMMENT ON COLUMN t_message.status IS '状态: 1-正常, 0-删除';
COMMENT ON COLUMN t_message.parent_id IS '父消息 ID，用于构建消息树分支';
COMMENT ON COLUMN t_message.checkpoint_id IS 'LangGraph checkpoint ID，用于恢复执行';


-- =============================================
-- 4. 消息向量表 (t_message_embedding)
-- =============================================
CREATE TABLE IF NOT EXISTS t_message_embedding (
    id BIGINT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    conversation_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(512),
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_msg_embed_message_id ON t_message_embedding(message_id);
CREATE INDEX IF NOT EXISTS idx_msg_embed_conversation_id ON t_message_embedding(conversation_id);
CREATE INDEX IF NOT EXISTS idx_msg_embed_user_id ON t_message_embedding(user_id);
CREATE INDEX IF NOT EXISTS idx_msg_embed_vector ON t_message_embedding 
    USING hnsw (embedding vector_cosine_ops);

COMMENT ON TABLE t_message_embedding IS '消息向量存储表（RAG 语义检索）';
COMMENT ON COLUMN t_message_embedding.message_id IS '关联的消息 ID';
COMMENT ON COLUMN t_message_embedding.conversation_id IS '所属会话 ID';
COMMENT ON COLUMN t_message_embedding.user_id IS '所属用户 ID';
COMMENT ON COLUMN t_message_embedding.role IS '消息角色: user/assistant';
COMMENT ON COLUMN t_message_embedding.content IS '消息文本内容';
COMMENT ON COLUMN t_message_embedding.embedding IS '消息的向量表示（512维）';


-- =============================================
-- 5. 知识库表 (t_knowledge_base)
-- =============================================
CREATE TABLE IF NOT EXISTS t_knowledge_base (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    document_count INTEGER DEFAULT 0,
    chunk_count INTEGER DEFAULT 0,
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_kb_user_id ON t_knowledge_base(user_id);

COMMENT ON TABLE t_knowledge_base IS '知识库表';
COMMENT ON COLUMN t_knowledge_base.user_id IS '所属用户 ID';
COMMENT ON COLUMN t_knowledge_base.name IS '知识库名称';
COMMENT ON COLUMN t_knowledge_base.description IS '知识库描述';
COMMENT ON COLUMN t_knowledge_base.document_count IS '文档数量';
COMMENT ON COLUMN t_knowledge_base.chunk_count IS '分块总数';


-- =============================================
-- 6. 文档表 (t_document)
-- =============================================
CREATE TABLE IF NOT EXISTS t_document (
    id BIGINT PRIMARY KEY,
    knowledge_base_id BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(512) NOT NULL,
    file_size BIGINT,
    file_type VARCHAR(50),
    chunk_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_doc_kb_id ON t_document(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_doc_status ON t_document(status);

COMMENT ON TABLE t_document IS '文档表（知识库文档元信息）';
COMMENT ON COLUMN t_document.knowledge_base_id IS '所属知识库 ID';
COMMENT ON COLUMN t_document.file_name IS '原始文件名';
COMMENT ON COLUMN t_document.file_url IS 'OSS 存储 URL';
COMMENT ON COLUMN t_document.file_size IS '文件大小（字节）';
COMMENT ON COLUMN t_document.file_type IS '文件类型: pdf/docx/txt';
COMMENT ON COLUMN t_document.chunk_count IS '分块数量';
COMMENT ON COLUMN t_document.status IS '处理状态: pending/processing/done/failed';


-- =============================================
-- 7. 文档分块表 (t_document_chunk)
-- =============================================
CREATE TABLE IF NOT EXISTS t_document_chunk (
    id BIGINT PRIMARY KEY,
    knowledge_base_id BIGINT NOT NULL,
    document_id BIGINT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(512),
    metadata JSONB,
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chunk_kb_id ON t_document_chunk(knowledge_base_id);
CREATE INDEX IF NOT EXISTS idx_chunk_doc_id ON t_document_chunk(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_vector ON t_document_chunk 
    USING hnsw (embedding vector_cosine_ops);

COMMENT ON TABLE t_document_chunk IS '文档分块表（知识库向量存储）';
COMMENT ON COLUMN t_document_chunk.knowledge_base_id IS '所属知识库 ID';
COMMENT ON COLUMN t_document_chunk.document_id IS '所属文档 ID';
COMMENT ON COLUMN t_document_chunk.chunk_index IS '分块序号';
COMMENT ON COLUMN t_document_chunk.content IS '分块文本内容';
COMMENT ON COLUMN t_document_chunk.embedding IS '向量表示（512维）';
COMMENT ON COLUMN t_document_chunk.metadata IS '元数据（页码、段落等）';


-- =============================================
-- 8. 用户自定义模型表 (t_user_model)
-- =============================================
CREATE TABLE IF NOT EXISTS t_user_model (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_code VARCHAR(100) NOT NULL,
    api_key VARCHAR(1000) NOT NULL,
    base_url VARCHAR(500),
    temperature DECIMAL(3,2) DEFAULT 0.70,
    timeout INTEGER DEFAULT 30,
    is_default BOOLEAN DEFAULT FALSE,
    status INTEGER DEFAULT 1,
    top_p DECIMAL(3,2) DEFAULT NULL,
    max_tokens INTEGER DEFAULT NULL,
    top_k INTEGER DEFAULT NULL,
    create_time TIMESTAMP DEFAULT NOW() NOT NULL,
    update_time TIMESTAMP DEFAULT NOW() NOT NULL,
    version INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_user_model_user_id ON t_user_model(user_id);

COMMENT ON TABLE t_user_model IS '用户自定义 AI 模型配置表';
COMMENT ON COLUMN t_user_model.user_id IS '所属用户 ID';
COMMENT ON COLUMN t_user_model.model_name IS '模型显示名称';
COMMENT ON COLUMN t_user_model.provider IS '提供商: openai/deepseek/gemini/custom';
COMMENT ON COLUMN t_user_model.model_code IS '模型编码';
COMMENT ON COLUMN t_user_model.api_key IS 'API Key（加密存储）';
COMMENT ON COLUMN t_user_model.base_url IS 'Base URL';
COMMENT ON COLUMN t_user_model.temperature IS '温度参数 0-2';
COMMENT ON COLUMN t_user_model.timeout IS '请求超时秒数';
COMMENT ON COLUMN t_user_model.is_default IS '是否为用户默认模型';
COMMENT ON COLUMN t_user_model.status IS '状态: 0=禁用 1=启用';
COMMENT ON COLUMN t_user_model.top_p IS 'Top P 核采样参数 (0-1)';
COMMENT ON COLUMN t_user_model.max_tokens IS '最大输出 token 数';
COMMENT ON COLUMN t_user_model.top_k IS 'Top K 参数，Gemini 专用';


-- =============================================
-- 完成
-- =============================================
SELECT '✅ 数据库初始化完成！共创建 8 张表' AS result;
