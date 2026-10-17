<p align="center">
  <svg width="400" height="110" viewBox="0 0 400 110" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="42" y1="22" x2="28" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
      <circle cx="26" cy="5" r="4.5" fill="#b45309"/>
      <line x1="62" y1="22" x2="78" y2="6" stroke="#b45309" stroke-width="4" stroke-linecap="round"/>
      <circle cx="80" cy="5" r="4.5" fill="#b45309"/>
      <rect x="12" y="22" width="82" height="62" rx="14" fill="#271705" stroke="#b45309" stroke-width="5"/>
      <rect x="20" y="30" width="54" height="46" rx="8" fill="#180e02" stroke="#78350f" stroke-width="2"/>
      <polygon points="40,42 40,64 60,53" fill="#f97316"/>
      <circle cx="83" cy="39" r="3.5" fill="#f97316"/>
      <circle cx="83" cy="50" r="3.5" fill="#f97316"/>
      <line x1="28" y1="84" x2="22" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
      <line x1="74" y1="84" x2="80" y2="96" stroke="#b45309" stroke-width="5" stroke-linecap="round"/>
      <rect x="65" y="52" width="38" height="38" rx="8" fill="#fef3c7" stroke="#f97316" stroke-width="3"/>
      <path d="M65 62 C65 56, 103 56, 103 62" fill="#f97316"/>
      <line x1="74" y1="49" x2="74" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
      <line x1="94" y1="49" x2="94" y2="56" stroke="#f97316" stroke-width="4" stroke-linecap="round"/>
      <line x1="72" y1="69" x2="88" y2="69" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
      <line x1="72" y1="76" x2="85" y2="76" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
      <line x1="72" y1="83" x2="82" y2="83" stroke="#451a03" stroke-width="3" stroke-linecap="round"/>
      <circle cx="98" cy="84" r="14" fill="#f97316" stroke="#fef3c7" stroke-width="2.5"/>
      <polyline points="98,76 98,84 104,88" stroke="#fef3c7" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="125" y="68" font-family="system-ui, -apple-system, sans-serif" font-size="42" font-weight="800" letter-spacing="-1">
          <tspan fill="#b45309">M3u-</tspan><tspan fill="#f97316">Monitor</tspan>
      </text>
  </svg>
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
