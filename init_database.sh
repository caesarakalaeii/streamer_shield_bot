#!/bin/bash
# Database initialization script for StreamerShield
# Run this script to create and initialize the PostgreSQL database

echo "Creating StreamerShield PostgreSQL database..."

# Set default values if environment variables are not set
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-streamer_shield}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-password}
DB_ADMIN_USER=${DB_ADMIN_USER:-postgres}

echo "Database configuration:"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"

# Create database and user
echo "Creating database and user..."
psql -h $DB_HOST -p $DB_PORT -U $DB_ADMIN_USER -c "CREATE DATABASE $DB_NAME;"
psql -h $DB_HOST -p $DB_PORT -U $DB_ADMIN_USER -c "CREATE USER ${DB_USER} WITH PASSWORD '$DB_PASSWORD';"
psql -h $DB_HOST -p $DB_PORT -U $DB_ADMIN_USER -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Run the database setup SQL
echo "Creating tables and indexes..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f database_setup.sql

echo "Database initialization complete!"
echo ""
echo "To migrate existing JSON data, you can run the migration commands in database_setup.sql"
echo "Make sure to set the following environment variables before running the services:"
echo "export TWITCH_APP_ID='your_twitch_app_id'"
echo "export TWITCH_APP_SECRET='your_twitch_app_secret'"
echo "export DB_HOST='$DB_HOST'"
echo "export DB_PORT='$DB_PORT'"
echo "export DB_NAME='$DB_NAME'"
echo "export DB_USER='$DB_USER'"
echo "export DB_PASSWORD='$DB_PASSWORD'"
