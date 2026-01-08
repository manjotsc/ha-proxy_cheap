# Proxy-Cheap for Home Assistant

<p align="center">
  <a href="https://github.com/me/ha-proxy_cheap/releases"><img src="https://img.shields.io/github/v/release/me/ha-proxy_cheap?style=flat-square" alt="Release"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square" alt="HACS"></a>
  <a href="https://github.com/me/ha-proxy_cheap/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/me/ha-proxy_cheap/validate.yml?style=flat-square&label=validation" alt="Validation"></a>
</p>

Monitor and manage your [Proxy-Cheap](https://proxy-cheap.com) proxies from Home Assistant.

## Features

- **Sensors**: Balance, IP, Port, Protocol, Country, Bandwidth (total/used/remaining), Expiry Date
- **Binary Sensors**: Active Status, Auto-Extend Status
- **Services**: `refresh`, `extend_proxy`, `update_whitelist`, `set_auto_extend`

## Installation

### HACS (Recommended)

1. Open HACS → Three-dot menu → **Custom repositories**
2. Add `https://github.com/me/ha-proxy_cheap` as **Integration**
3. Install **Proxy-Cheap** and restart Home Assistant

### Manual

Copy `custom_components/proxy_cheap` to your `config/custom_components/` directory.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Proxy-Cheap**
3. Enter your API Key and API Secret from [Proxy-Cheap Dashboard](https://proxy-cheap.com)

## Example Automation

```yaml
automation:
  - alias: "Low Bandwidth Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.proxy_us_residential_bandwidth_remaining
        below: 1
    action:
      - service: notify.mobile_app
        data:
          title: "Low Proxy Bandwidth"
          message: "Less than 1GB remaining"
```

## Support

- [GitHub Issues](https://github.com/me/ha-proxy_cheap/issues)
- [Proxy-Cheap Support](https://proxy-cheap.com/support)

## License

MIT
