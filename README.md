# 🎵 Last.fm Scrobbler

A modern, feature-rich web application for scrobbling music to Last.fm with advanced timing controls, real-time now playing updates, and a beautiful user interface.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Build Status](https://img.shields.io/github/actions/workflow/status/yourusername/lastfm-scrobbler/python-package.yml?branch=main)
![Coverage](https://img.shields.io/codecov/c/github/yourusername/lastfm-scrobbler)

## ✨ Features

### 🎯 Core Functionality
- **Last.fm Authentication** - Secure OAuth integration with Last.fm
- **Manual Scrobbling** - Scrobble any track with custom timestamps
- **Search Integration** - Find tracks using Last.fm's database
- **Now Playing Updates** - Set and display currently playing tracks

### ⏰ Advanced Timing
- **Custom Scrobble Times** - Scrobble tracks for any time in the past 14 days
- **Time Presets** - Quick options (now, 5m ago, 15m ago, 30m ago, 1h ago)
- **Flexible Input** - Support for various time formats and relative times

### 🎨 User Experience
- **Real-time Updates** - Live now playing detection every 30 seconds
- **Responsive Design** - Works perfectly on desktop and mobile
- **Beautiful UI** - Modern gradient design with smooth animations
- **Recent Tracks** - View and re-scrobble from your listening history

### 🔒 Security & Privacy
- **Encrypted Storage** - All tokens encrypted with industry-standard encryption
- **Rate Limiting** - Built-in protection against API abuse
- **Secure Sessions** - Proper session management and CSRF protection
- **Privacy Focused** - Minimal data collection with clear privacy policy

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- A Last.fm account
- Last.fm API credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/lastfm-scrobbler.git
   cd lastfm-scrobbler
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Last.fm API credentials
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Last.fm API credentials (required)
LASTFM_API_KEY=your_api_key_here
LASTFM_API_SECRET=your_api_secret_here

# Flask configuration
SECRET_KEY=your_secret_key_here
FLASK_ENV=development

# Optional: Redis for session storage
REDIS_URL=redis://localhost:6379

# Optional: Sentry for error tracking
SENTRY_DSN=your_sentry_dsn_here
```

### Getting Last.fm API Credentials

1. Visit [Last.fm API Account Creation](https://www.last.fm/api/account/create)
2. Create a new API account
3. Copy your API Key and Shared Secret
4. Add them to your `.env` file

## 📖 Usage

### Basic Scrobbling

1. **Login** - Click "Login with Last.fm" and authorize the application
2. **Search** - Use the search box to find tracks
3. **Select** - Click on a search result to select it
4. **Scrobble** - Choose your timing and click "Scrobble"

### Custom Timing Options

- **Now** - Scrobble for the current time
- **X minutes ago** - Enter a number (e.g., "30" for 30 minutes ago)
- **Specific time** - Enter a date/time string (e.g., "2025-01-15 14:30")
- **Relative time** - Use natural language (e.g., "1 hour ago", "yesterday")

### Now Playing

- **Auto-detection** - Automatically shows your current Last.fm now playing
- **Manual update** - Select a track and click "Now Playing"
- **Live updates** - Refreshes every 30 seconds automatically

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov=token_store --cov-report=html

# Run specific test file
pytest tests/test_app.py -v
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .

# Security scan
bandit -r . -ll
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📁 Project Structure

```
lastfm-scrobbler/
├── app.py                 # Main Flask application
├── token_store.py         # Encrypted token storage
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── LICENSE               # MIT license
├── pyproject.toml        # Python project configuration
├── pytest.ini           # Pytest configuration
├── templates/            # HTML templates
│   ├── index.html        # Main application page
│   ├── terms.html        # Terms of service
│   └── privacy.html      # Privacy policy
├── static/               # Static files (if any)
├── tests/                # Test suite
│   ├── __init__.py
│   ├── conftest.py       # Test configuration
│   ├── test_app.py       # Application tests
│   └── test_token_store.py # Token storage tests
└── .github/              # GitHub configuration
    └── workflows/
        └── python-package.yml # CI/CD pipeline
```

## 🐳 Docker Support

### Using Docker

```bash
# Build image
docker build -t lastfm-scrobbler .

# Run container
docker run -p 5000:5000 --env-file .env lastfm-scrobbler
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🚀 Deployment

### Heroku

1. Install Heroku CLI
2. Create Heroku app: `heroku create your-app-name`
3. Set environment variables: `heroku config:set LASTFM_API_KEY=your_key`
4. Deploy: `git push heroku main`

### Railway

1. Connect your GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Traditional VPS

1. Set up Python environment
2. Install dependencies
3. Configure reverse proxy (nginx)
4. Set up process manager (systemd/supervisor)
5. Configure SSL certificate

## 📊 API Rate Limits

The application implements rate limiting to comply with Last.fm's API limits:

- **Search requests**: 5 per minute per IP
- **Scrobbling**: 5 per minute per user
- **Now playing**: 5 per minute per user

## 🔐 Security

### Data Encryption
- All Last.fm tokens are encrypted using `cryptography.fernet`
- Token files have restrictive permissions (600)
- Session data is properly secured

### Privacy
- Minimal data collection
- No tracking or analytics cookies
- Transparent privacy policy
- User data can be deleted on request

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Areas for Contribution
- 🐛 Bug fixes and improvements
- ✨ New features (playlist import, bulk scrobbling, etc.)
- 📚 Documentation improvements
- 🧪 Test coverage expansion
- 🎨 UI/UX enhancements

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Last.fm](https://last.fm) for providing the API
- [Flask](https://flask.palletsprojects.com/) for the web framework
- All the open-source libraries that make this project possible

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/lastfm-scrobbler/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/yourusername/lastfm-scrobbler/discussions)
- 📧 **Security Issues**: Email maintainers directly

## 🔄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

---

Made with ❤️ by [fentbuscoding](https://github.com/fentbuscoding)