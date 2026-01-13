CREATE TABLE posts (
    uri     TEXT PRIMARY KEY,
    url     TEXT NOT NULL,
    post JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_spam BOOL,
    maybe_spam BOOL,
    score INTEGER not NULL
);
