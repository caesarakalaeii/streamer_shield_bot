# StreamerShield Twitch Bot

StreamerShield is an AI-powered ChatBot designed to protect Twitch streamers from scammers and malicious users. It uses machine learning to analyze chat messages and automatically moderates suspicious content.

## Features

- **AI-Powered Moderation**: Uses machine learning to detect and ban scammers automatically
- **Real-time Chat Monitoring**: Monitors chat messages in real-time for suspicious patterns
- **Database Integration**: Stores user data and chat logs for analysis
- **Twitch EventSub Integration**: Receives real-time events from Twitch
- **Configurable Thresholds**: Adjustable settings for user age and message length filtering
- **Automated Banning**: Can automatically ban users based on AI predictions
- **Data Collection**: Optional data collection for improving the AI model

## Project Structure

```
├── streamer_shield_chatbot.py  # Main bot application
├── twitch_config.py           # Configuration management
├── database_manager.py        # Database operations
├── logger.py                  # Logging utilities
├── database_setup.sql         # Database schema
├── requirements.txt           # Python dependencies
├── Dockerfile                # Docker configuration
├── init_database.ps1         # Windows database initialization
├── init_database.sh          # Linux database initialization
└── README.md                 # This file
```

## Requirements

- Python 3.12+
- PostgreSQL database
- Twitch Developer Application
- AI prediction service endpoint

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TWITCH_APP_ID` | Twitch application client ID from developer console | `abc123def456` |
| `TWITCH_APP_SECRET` | Twitch application client secret from developer console | `your_secret_here` |

### Optional Variables (with defaults)

#### Twitch Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `TWITCH_USER` | Bot username on Twitch | `streamer_shield` |
| `ADMIN_USER` | Admin username for bot management | `caesarlp` |

#### Database Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL database host | `localhost` |
| `DB_PORT` | PostgreSQL database port | `5432` |
| `DB_NAME` | Database name | `streamer_shield` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database password | `password` |

#### Service URLs
| Variable | Description | Default |
|----------|-------------|---------|
| `EVENTSUB_URL` | EventSub webhook URL | `https://webhook.caes.ar` |
| `SHIELD_URL` | AI prediction service endpoint | `http://localhost:38080/api/predict` |
| `AUTH_URL` | Authentication confirmation URL | `https://shield.caes.ar/login/confirm` |

#### Bot Behavior Settings
| Variable | Description | Default |
|----------|-------------|---------|
| `IS_ARMED` | Enable/disable automatic banning | `true` |
| `COLLECT_DATA` | Enable/disable data collection | `true` |
| `AGE_THRESHOLD` | Minimum account age (months) for filtering | `6` |
| `MAX_LENGTH` | Maximum message length for processing | `31` |

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd twitch_bot
```

2. Set up environment variables:
```bash
# Create a .env file with your configuration
cp .env.example .env
# Edit .env with your values
```

3. Build and run with Docker:
```bash
docker build -t streamer-shield .
docker run -d --env-file .env streamer-shield
```

### Manual Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database:
```bash
# On Windows
.\init_database.ps1

# On Linux/Mac
./init_database.sh
```

3. Set environment variables and run:
```bash
export TWITCH_APP_ID="your_app_id"
export TWITCH_APP_SECRET="your_app_secret"
# Set other variables as needed...

python streamer_shield_chatbot.py
```

## Setup Instructions

### 1. Twitch Developer Application

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Create a new application
3. Set the OAuth Redirect URL to your auth URL
4. Note down the Client ID and Client Secret
5. Set `TWITCH_APP_ID` and `TWITCH_APP_SECRET` environment variables

### 2. Database Setup

The bot requires a PostgreSQL database. Use the provided initialization scripts:

- **Windows**: Run `init_database.ps1`
- **Linux/Mac**: Run `init_database.sh`

Or manually execute the SQL in `database_setup.sql`.

### 3. AI Service

Ensure your AI prediction service is running and accessible at the configured `SHIELD_URL`.

## Bot Commands

- `!shield_info` - Display information about StreamerShield

## Permissions Required

The bot requires the following Twitch OAuth scopes:
- `chat:read` - Read chat messages
- `chat:edit` - Send chat messages
- `moderator:read:chatters` - Read chatter information
- `moderator:manage:banned_users` - Ban/unban users
- `moderator:read:followers` - Read follower information

## Security Notes

- Never commit your `TWITCH_APP_SECRET` to version control
- Use environment variables or secure secret management
- Regularly rotate your API credentials
- Monitor bot activity and adjust thresholds as needed

## Troubleshooting

1. **Authentication Issues**: Ensure your Twitch app credentials are correct and the redirect URL matches
2. **Database Connection**: Verify PostgreSQL is running and credentials are correct
3. **Permission Errors**: Make sure the bot account has moderator permissions in your channel
4. **AI Service**: Ensure the prediction service is accessible and responding

## More Information

For more details about StreamerShield, visit: https://caes.ar

## License

[Add your license information here]
