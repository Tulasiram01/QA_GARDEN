-- PostgreSQL Schema for Locator System

CREATE TABLE IF NOT EXISTS screens (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    name VARCHAR(200),
    title VARCHAR(300),
    dom_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS elements (
    id SERIAL PRIMARY KEY,
    screen_id INTEGER REFERENCES screens(id) ON DELETE CASCADE,
    element_name VARCHAR(200),
    element_type VARCHAR(50) NOT NULL,
    element_id VARCHAR(200),
    element_name_attr VARCHAR(200),
    data_testid VARCHAR(200),
    aria_label VARCHAR(500),
    role VARCHAR(100),
    css_selector TEXT NOT NULL,
    xpath TEXT NOT NULL,
    text_content TEXT,
    stability_score INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS execution_metadata (
    id SERIAL PRIMARY KEY,
    execution_id VARCHAR(100) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    screens_crawled INTEGER DEFAULT 0,
    elements_extracted INTEGER DEFAULT 0,
    errors TEXT
);

CREATE INDEX idx_screens_url ON screens(url);
CREATE INDEX idx_elements_screen_id ON elements(screen_id);
CREATE INDEX idx_elements_type ON elements(element_type);
CREATE INDEX idx_elements_verified ON elements(verified);