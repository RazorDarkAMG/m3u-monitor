<p align="center">
  <img src="logo-banner.svg" alt="M3U-Monitor Logo" width="400">
</p>

<p align="center">
  A lightweight, secure, and self-hosted web application to monitor Xtream Codes (M3U) playlist credentials and expiration dates, with built-in Gotify notifications and automatic background scheduling.
</p>

## Features
- **Multi-language support:** French 🇫🇷, English 🇬🇧, Spanish 🇪🇸, German 🇩🇪 with native SVG flags.
- **Secure by design:** Password hashing (PBKDF2-SHA256) and AES-128 encryption for IPTV credentials in local storage.
- **Multi-user workspace:** Isolated dashboards per user with customizable admin controls.
- **Gotify Integration:** Custom automated expiration alerts with adjustable thresholds and repeat frequencies.
- **Background Scheduler:** Automated daily/periodic background checks with an in-app notification center.
- **Extremely lightweight:** Built with Python (Flask) on Alpine Linux (~15-20 MB RAM).

## Docker Compose Setup

```yaml
services:
  m3u-monitor:
    image: ghcr.io/razordarkamg/m3u-monitor:latest
    container_name: m3u-monitor
    restart: unless-stopped
    environment:
      - TZ=Europe/Paris
    volumes:
      - /path/to/data:/data
    ports:
      - "5056:5000"
