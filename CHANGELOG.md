# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with >90% coverage
- Docker support with multi-stage builds
- GitHub Actions CI/CD pipeline
- Security scanning with Bandit
- Code quality checks with Black, isort, and flake8

### Changed
- Improved error handling and user feedback
- Enhanced UI with better loading states
- Optimized API rate limiting

## [1.0.0] - 2025-06-16

### Added
- **Core Features**
  - Last.fm OAuth authentication
  - Manual track scrobbling with search
  - Custom scrobble timestamps (now, minutes ago, specific dates)
  - Real-time now playing detection and updates
  - Recent tracks display with re-scrobble functionality

- **User Interface**
  - Modern responsive design with gradient backgrounds
  - Real-time search with keyboard navigation
  - Animated loading states and transitions
  - Mobile-optimized layout
  - Dark theme support

- **Security & Privacy**
  - Encrypted token storage using Fernet encryption
  - Secure session management
  - Rate limiting to prevent API abuse
  - Privacy-focused data handling
  - CSRF protection

- **Advanced Features**
  - Time preset buttons (5m, 15m, 30m, 1h ago)
  - Natural language time parsing
  - Auto-refresh for now playing status
  - Search result caching
  - Graceful error handling

- **Technical Features**
  - File-based encrypted token storage
  - Comprehensive logging
  - Environment-based configuration
  - Health check endpoint
  - Request/response validation

### Security
- All authentication tokens encrypted at rest
- Token files have restrictive permissions (600)
- Rate limiting implemented for all API endpoints
- Input validation and sanitization
- Secure session cookies

### Documentation
- Comprehensive README with setup instructions
- Terms of Service and Privacy Policy pages
- API documentation
- Contributing guidelines
- Security guidelines

## [0.1.0] - 2025-06-15

### Added
- Initial project setup
- Basic Flask application structure
- Last.fm API integration
- Token storage system
- Basic HTML templates

---

## Release Notes

### v1.0.0 - "Harmony" 🎵

This is the first stable release of Last.fm Scrobbler! After extensive development and testing, we're proud to present a fully-featured, secure, and user-friendly Last.fm scrobbling application.

**Key Highlights:**
- **Beautiful UI**: Modern, responsive design that works great on all devices
- **Advanced Timing**: Scrobble tracks for any time in the past 14 days with flexible input options
- **Real-time Updates**: Live now playing detection that updates every 30 seconds
- **Security First**: All sensitive data encrypted, rate limiting, and privacy-focused design
- **Developer Friendly**: Comprehensive tests, CI/CD, and clear documentation

**Breaking Changes:** None (initial release)

**Migration Guide:** Not applicable (initial release)

**Known Issues:**
- Search results limited to 30 items (Last.fm API limitation)
- Scrobbling limited to past 14 days (Last.fm API limitation)
- No bulk scrobbling yet (planned for v1.1.0)

**Upgrade Instructions:**
This is the initial release. Follow the installation instructions in the README.

**Contributors:**
- [@yourusername](https://github.com/yourusername) - Lead developer

**Special Thanks:**
- Last.fm for providing the API
- The Flask community for excellent documentation
- All beta testers who provided valuable feedback

---

### Upcoming Releases

#### v1.1.0 - "Playlist" (Planned)
- Bulk scrobbling from CSV/text files
- Playlist import from various services
- Advanced search filters
- Export scrobble history

#### v1.2.0 - "Social" (Planned)
- Multiple user support
- Scrobble sharing
- Social features integration
- Enhanced privacy controls

#### v2.0.0 - "Orchestra" (Future)
- Complete UI redesign
- Database backend
- API for third-party integrations
- Advanced analytics and insights

---

## Support

If you encounter any issues or have questions:

1. Check the [FAQ](https://github.com/yourusername/lastfm-scrobbler/wiki/FAQ)
2. Search [existing issues](https://github.com/yourusername/lastfm-scrobbler/issues)
3. Create a [new issue](https://github.com/yourusername/lastfm-scrobbler/issues/new)
4. Join our [discussions](https://github.com/yourusername/lastfm-scrobbler/discussions)