ALTER TABLE posts add annotation text[];
CREATE INDEX idx_handnle on  posts((post->>'{author,handle}'));
CREATE TABLE profile (
    profile JSON, 
    annotation text[],
    created_at TIMESTAMP DEFAULT NOW()
);
GRANT ALL on profile to jul;

