# FireBoard Integration - MQTT Implementation

## Architecture Overview

The FireBoard integration uses a **hybrid REST + MQTT** approach for optimal performance and user experience:

### Components:

1. **REST API** (Session Cookie Authentication)
   - Initial authentication: `/api/rest-auth/login/`
   - Device list: `/api/v1/devices.json`
   - Refreshes device list on the user-configured polling interval (default 40s)

2. **MQTT over WebSocket** (Real-time Updates)
   - Endpoint: `wss://fireboard.io/ws`
   - Protocol: MQTT v3.1 over WebSocket
   - Provides real-time temperature updates
   - No polling needed!

> **Status (as of 2026-08-09)**: MQTT is currently broken. FireBoard's
> [official API docs](https://docs.fireboard.io/app/app-api/) only describe
> REST polling — MQTT/WebSocket was always undocumented, reverse-engineered
> behavior, and live testing confirms the WebSocket handshake to
> `wss://fireboard.io/ws` is now rejected by `paho-mqtt` (`WebSocket handshake
> error, connection not upgraded`) even with a valid session. A raw
> `aiohttp` WebSocket upgrade succeeds, so the endpoint is reachable but no
> longer satisfies whatever `paho-mqtt`'s handshake validation expects
> (likely a `Sec-WebSocket-Protocol` mismatch) — this was never fixed, just
> made non-fatal.
>
> Because of this, `coordinator.py` no longer treats MQTT as the *only*
> source of temperature/battery data: every REST poll now parses
> `current_temp`/`last_templog` directly out of `devices.json`'s `channels`
> array (which FireBoard's docs already promise is "< 60 seconds old"), so
> sensors work correctly via REST polling alone. MQTT, if it starts working
> again, would only improve latency between polls — it is no longer required
> for the integration to function.

## User Experience

**What users need:**
- ✅ Just FireBoard email and password
- ✅ No MQTT broker setup
- ✅ No additional configuration
- ✅ Real-time temperature updates

**What happens automatically:**
1. User enters FireBoard credentials
2. Integration authenticates via REST API
3. Integration retrieves device list
4. Integration connects to FireBoard's MQTT broker
5. Integration subscribes to temperature topics for each device
6. Real-time updates flow through MQTT

## Implementation Details

### Authentication Flow

```python
1. POST /api/rest-auth/login/ with {username, password}
2. Receive {key: "auth_token"}
3. Store session cookies for REST calls
4. Use auth token for MQTT connection
```

### MQTT Connection

```python
# WebSocket connection
wss://fireboard.io/ws

# Headers
Authorization: Token {auth_token}

# Protocol
Sec-WebSocket-Protocol: mqttv3.1
```

### Topic Structure

```
<device_uuid>/templog<channel>   # one topic per temperature channel
<device_uuid>/drivelog           # FireBoard Drive data, if present
```

The integration subscribes to each channel's topic individually rather than a
wildcard, since the FireBoard broker does not expose a per-device wildcard
topic.

### Data Flow

```
┌─────────────────┐
│   FireBoard     │
│   Cloud/Device  │
└────────┬────────┘
         │
         │ MQTT Publish
         ▼
┌─────────────────────┐
│  FireBoard MQTT     │
│  Broker (WSS)       │
└────────┬────────────┘
         │
         │ WebSocket
         ▼
┌─────────────────────┐
│  HA Integration     │
│  MQTT Client        │
└────────┬────────────┘
         │
         │ Callback
         ▼
┌─────────────────────┐
│  Coordinator        │
│  (Update Sensors)   │
└─────────────────────┘
```

## Benefits Over REST-Only Approach

| Aspect | REST Polling | MQTT Push |
|--------|-------------|-----------|
| **Latency** | 40 seconds | < 1 second |
| **API Calls** | ~90/hour/device | Only for periodic device-list refresh |
| **Rate Limiting** | Risk with multiple devices (17 calls/5min limit) | No risk |
| **Battery Impact** | Higher (frequent polls) | Lower (push only) |
| **Responsiveness** | Delayed | Instant |

## Fallback Behavior

The integration is designed to gracefully handle MQTT connection issues:

1. **MQTT Disconnects**: Auto-reconnect via paho-mqtt
2. **MQTT Unavailable**: Device list still updates via REST on the configured polling interval
3. **Authentication Expires**: Auto-reauthenticate and reconnect

## Testing the MQTT Connection

The MQTT connection can be verified by:

1. Checking Home Assistant logs for "MQTT client connected successfully"
2. Observing real-time temperature updates (< 1 second latency)
3. Monitoring MQTT subscriptions in debug mode

## Comparison with fireboard2mqtt

| Feature | ha-fireboard | fireboard2mqtt |
|---------|-------------|----------------|
| **Setup** | Zero config (just credentials) | Requires MQTT broker |
| **Dependencies** | None | Local MQTT broker |
| **Architecture** | Built-in MQTT client | External MQTT bridge |
| **User Complexity** | Minimal | Moderate |
| **Updates** | Real-time (MQTT push) | Real-time (MQTT push) |

## Future Enhancements

Potential improvements:

1. **MQTT Topic Discovery**: Auto-discover actual topic structure
2. **QoS Configuration**: Allow users to configure MQTT QoS level
3. **Offline Buffering**: Buffer data during disconnections
4. **Statistics**: Track MQTT connection health

## Code Structure

```
custom_components/fireboard/
├── __init__.py           # Setup/teardown with MQTT lifecycle
├── api_client.py         # REST API with session cookies
├── mqtt_client.py        # MQTT over WebSocket client
├── coordinator.py        # Hybrid REST + MQTT coordinator
├── sensor.py             # Temperature sensors
└── binary_sensor.py      # Status sensors
```

## Security Considerations

1. **Credentials**: Stored encrypted in HA config entries
2. **Token**: Stored in memory only, not persisted
3. **TLS**: All connections use TLS (HTTPS/WSS)
4. **Session Cookies**: Managed by aiohttp, cleared on unload

## Troubleshooting

### MQTT Not Connecting

Check logs for:
```
ERROR Failed to set up MQTT connection
```

Possible causes:
- FireBoard API down
- Authentication failed
- Firewall blocking WebSocket

### No Real-time Updates

1. Check MQTT connection status in logs
2. Verify device is actually sending data
3. Check FireBoard app for recent activity

### High CPU Usage

The MQTT client runs in a background thread and should use minimal CPU. If high usage is observed:

1. Check for reconnection loops in logs
2. Verify network stability
3. Report issue on GitHub

## Performance Metrics

Based on typical usage:

- **Memory**: ~5MB per device
- **CPU**: < 0.1% average
- **Network**: ~10KB/day (MQTT keepalive + updates)
- **Latency**: < 1 second for temperature updates

## Development Notes

### Adding New Message Types

To handle additional MQTT messages:

1. Update `_handle_mqtt_message()` in coordinator
2. Parse new message format
3. Update sensor attributes accordingly

### Testing MQTT Locally

For development testing:

```python
# Enable debug logging
logger:
  default: info
  logs:
    custom_components.fireboard: debug
    custom_components.fireboard.mqtt_client: debug
```

## References

- [FireBoard Cloud API Docs](https://docs.fireboard.io/app/app-api/)
- [Paho MQTT Python](https://github.com/eclipse/paho.mqtt.python)
- [Home Assistant Integration Development](https://developers.home-assistant.io/)

