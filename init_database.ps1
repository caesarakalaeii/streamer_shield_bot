# Windows PowerShell commands to create and initialize the database

# Set environment variables (customize these values)
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "streamer_shield"
$env:DB_USER = "streamer_shield_user"
$env:DB_PASSWORD = "your_secure_password_here"
$env:DB_ADMIN_USER = "postgres"

Write-Host "Creating StreamerShield PostgreSQL database..."

# Create database and user (run as postgres admin)
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_ADMIN_USER -c "CREATE DATABASE $env:DB_NAME;"
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_ADMIN_USER -c "CREATE USER $env:DB_USER WITH PASSWORD '$env:DB_PASSWORD';"
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_ADMIN_USER -c "GRANT ALL PRIVILEGES ON DATABASE $env:DB_NAME TO $env:DB_USER;"

# Create tables and indexes
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -f database_setup.sql

Write-Host "Database initialization complete!"

# Required environment variables for the services
Write-Host "Set these environment variables before running the services:"
Write-Host "TWITCH_APP_ID='your_twitch_app_id'"
Write-Host "TWITCH_APP_SECRET='your_twitch_app_secret'"
Write-Host "DB_HOST='$env:DB_HOST'"
Write-Host "DB_PORT='$env:DB_PORT'"
Write-Host "DB_NAME='$env:DB_NAME'"
Write-Host "DB_USER='$env:DB_USER'"
Write-Host "DB_PASSWORD='$env:DB_PASSWORD'"
