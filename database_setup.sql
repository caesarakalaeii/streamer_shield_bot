-- PostgreSQL Database Setup Commands for StreamerShield
-- Run these commands to create and initialize the database

-- 1. Create the database (run as postgres superuser)
CREATE DATABASE streamer_shield;

-- 2. Create a user for the application (optional, but recommended)
CREATE USER streamer_shield_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE streamer_shield TO streamer_shield_user;

-- 3. Connect to the streamer_shield database and create tables
\c streamer_shield;

-- Create whitelist table
CREATE TABLE whitelist (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create blacklist table
CREATE TABLE blacklist (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create joinable channels table
CREATE TABLE joinable_channels (
    id SERIAL PRIMARY KEY,
    channel_name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create known users table
CREATE TABLE known_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE,
    confidence_score INTEGER,
    account_age_years INTEGER,
    account_age_months INTEGER,
    account_age_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create settings table for misc data like pat counter
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize pat counter
INSERT INTO settings (key, value) VALUES ('pat_counter', '0');

-- Grant permissions to the application user (if created)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO streamer_shield_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO streamer_shield_user;

-- Create indexes for better performance
CREATE INDEX idx_whitelist_username ON whitelist(username);
CREATE INDEX idx_blacklist_username ON blacklist(username);
CREATE INDEX idx_channels_name ON joinable_channels(channel_name);
CREATE INDEX idx_known_users_username ON known_users(username);
CREATE INDEX idx_settings_key ON settings(key);

-- Optional: Migrate existing JSON data
-- You can run these INSERT statements to migrate your existing data from JSON files

-- Example migration from whitelist.json:
-- INSERT INTO whitelist (username) VALUES
-- ('somepoorsoul'), ('caesarlp'), ('streamer_shield'), ('nightbot'),
-- ('spyfox090'), ('creak_creak'), ('dreamytatas'), ('roooooooooberrrrrrrrrrrt'),
-- ('pope_pontius'), ('demonlordraijuvt')
-- ON CONFLICT (username) DO NOTHING;

-- Example migration from blacklist.json:
-- INSERT INTO blacklist (username) VALUES
-- ('somepoorsoul'), ('ceiuhhskna'), ('tinnaalex12')
-- ON CONFLICT (username) DO NOTHING;

-- Note: You'll need to manually create migration scripts for your specific JSON data
