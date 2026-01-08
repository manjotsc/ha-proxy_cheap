<p align="center">
  <img src="https://brands.home-assistant.io/_/proxy_cheap/icon.png" alt="Proxy-Cheap Logo" width="150" height="150">
</p>

<h1 align="center">Proxy-Cheap for Home Assistant</h1>

<p align="center">
  <strong>Monitor and manage your Proxy-Cheap proxies directly from Home Assistant</strong>
</p>

<p align="center">
  <a href="https://github.com/me/ha-proxy_cheap/releases">
    <img src="https://img.shields.io/github/v/release/me/ha-proxy_cheap?style=for-the-badge&color=blue" alt="Release">
  </a>
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge" alt="HACS">
  </a>
  <a href="https://github.com/me/ha-proxy_cheap/actions/workflows/validate.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/me/ha-proxy_cheap/validate.yml?style=for-the-badge&label=validation" alt="Validation">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/me/ha-proxy_cheap?style=for-the-badge" alt="License">
  </a>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#services">Services</a> •
  <a href="#automations">Automations</a>
</p>

---

## Overview

This custom integration connects your [Proxy-Cheap](https://proxy-cheap.com) account to Home Assistant, giving you real-time visibility into your proxy infrastructure. Track bandwidth usage, monitor expiry dates, and automate proxy management—all from your smart home dashboard.

## Features

### Sensors

| Type | Sensors |
|------|---------|
| **Account** | Balance (USD), Total Proxy Count |
| **Proxy** | IP Address, Port, Username, Protocol, Network Type, Country, Region |
| **Bandwidth** | Total (GB), Used (GB), Remaining (GB) |
| **Status** | Expiry Date, Auto Extend Status |

### Binary Sensors

| Sensor | Description |
|--------|-------------|
| **Active Status** | Indicates if the proxy is currently active |
| **Auto Extend** | Shows if auto-extend is enabled |

### Services

| Service | Description |
|---------|-------------|
| `proxy_cheap.refresh` | Force refresh all data from API |
| `proxy_cheap.extend_proxy` | Extend proxy rental period |
| `proxy_cheap.buy_bandwidth` | Purchase additional bandwidth |
| `proxy_cheap.update_whitelist` | Update IP whitelist |
| `proxy_cheap.set_auto_extend` | Toggle auto-extend feature |

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant instance
2. Click the **three-dot menu** in the top right
3. Select **Custom repositories**
4. Add the repository URL:
   ```
   https://github.com/me/ha-proxy_cheap
   ```
5. Select **Integration** as the category
6. Click **Add**
7. Search for **Proxy-Cheap** and install
8. **Restart Home Assistant**

### Manual

1. Download the latest release from the [releases page](https://github.com/me/ha-proxy_cheap/releases)
2. Extract and copy `custom_components/proxy_cheap` to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Adding the Integration

1. Navigate to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Proxy-Cheap**
4. Enter your credentials:
   - **API Key**: Your Proxy-Cheap API key
   - **API Secret**: Your Proxy-Cheap API secret
5. Configure update interval (default: 300 seconds)

### Getting API Credentials

1. Log in to [Proxy-Cheap](https://proxy-cheap.com)
2. Go to **Dashboard** → **API**
3. Click **Create API Key**
4. Copy both the **API Key** and **API Secret**

> **Note**: Keep your API credentials secure. Never share them publicly.

## Entities

Each proxy creates a device with associated entities:

```
sensor.proxy_cheap_account_balance
sensor.proxy_cheap_total_proxies
sensor.proxy_{country}_{network}_ip_address
sensor.proxy_{country}_{network}_bandwidth_remaining
sensor.proxy_{country}_{network}_expiry_date
binary_sensor.proxy_{country}_{network}_active
```

## Automations

### Low Bandwidth Alert

```yaml
automation:
  - alias: "Proxy Bandwidth Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.proxy_us_residential_bandwidth_remaining
        below: 1
    action:
      - service: notify.mobile_app
        data:
          title: "Low Proxy Bandwidth"
          message: "US Residential proxy has less than 1GB remaining"
```

### Auto-Purchase Bandwidth

```yaml
automation:
  - alias: "Auto Purchase Bandwidth"
    trigger:
      - platform: numeric_state
        entity_id: sensor.proxy_us_residential_bandwidth_remaining
        below: 0.5
    action:
      - service: proxy_cheap.buy_bandwidth
        data:
          proxy_id: "{{ state_attr('sensor.proxy_us_residential_bandwidth_remaining', 'proxy_id') }}"
          amount_gb: 10
```

### Expiry Reminder

```yaml
automation:
  - alias: "Proxy Expiry Reminder"
    trigger:
      - platform: template
        value_template: >
          {{ (as_timestamp(states('sensor.proxy_us_residential_expiry_date'))
              - as_timestamp(now())) < 604800 }}
    action:
      - service: notify.mobile_app
        data:
          title: "Proxy Expiring Soon"
          message: "Your proxy expires in less than 7 days"
```

### Proxy Status Monitor

```yaml
automation:
  - alias: "Proxy Offline Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.proxy_us_residential_active
        to: "off"
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          title: "Proxy Offline"
          message: "US Residential proxy has been inactive for 5 minutes"
```

## Dashboard Card Example

```yaml
type: entities
title: Proxy Status
entities:
  - entity: sensor.proxy_cheap_account_balance
    name: Account Balance
  - entity: sensor.proxy_us_residential_bandwidth_remaining
    name: Bandwidth Remaining
  - entity: sensor.proxy_us_residential_expiry_date
    name: Expires
  - entity: binary_sensor.proxy_us_residential_active
    name: Status
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Invalid Authentication** | Verify API Key and Secret are correct |
| **No Proxies Found** | Ensure you have active proxies in your account |
| **Rate Limiting** | Increase the update interval in integration options |
| **Entities Unavailable** | Check Home Assistant logs for API errors |

## Support

- [Report an Issue](https://github.com/me/ha-proxy_cheap/issues)
- [Proxy-Cheap Support](https://proxy-cheap.com/support)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <sub>Built with ❤️ for the Home Assistant community</sub>
</p>
