# FireBoard Integration - Physical Device Testing Guide

## Overview

This guide walks you through testing the FireBoard integration with your actual devices before GitHub/HACS submission.

## Prerequisites

- **Home Assistant Instance**: Running instance with custom_components support
- **FireBoard Account**: Active account with devices registered
- **Physical Devices**: At least one FireBoard device (Yoder YS640s, Spark, or 2 Pro)
- **FireBoard Credentials**: Email and password for your account

## Pre-Testing Checklist

- [ ] Home Assistant is running and accessible
- [ ] You can log into https://fireboard.io with your credentials
- [ ] At least one FireBoard device is online in the FireBoard app
- [ ] You have terminal/SSH access to your Home Assistant instance

## Installation Steps

### Step 1: Copy Integration to Home Assistant

```bash
# Navigate to project directory
cd /Users/garthdb/Projects/ha-fireboard

# Copy integration to Home Assistant custom_components
# Adjust the path if your HA config is in a different location
cp -r custom_components/fireboard ~/.homeassistant/custom_components/

# Or if using a different config directory:
# cp -r custom_components/fireboard /config/custom_components/
```

### Step 2: Restart Home Assistant

**Via UI:**
1. Go to Settings > System
2. Click "Restart"
3. Wait for restart to complete

**Via Terminal:**
```bash
# If using Home Assistant OS
ha core restart

# If using docker
docker restart homeassistant
```

### Step 3: Add the Integration

1. Go to **Settings > Devices & Services**
2. Click **"+ Add Integration"** (bottom right)
3. Search for **"FireBoard"**
4. If you don't see it, clear your browser cache and refresh

## Configuration Testing

### Test 1: Authentication

**Goal**: Verify credentials work with FireBoard API

1. Enter your FireBoard credentials:
   - **Email**: Your FireBoard account email
   - **Password**: Your FireBoard account password
   - **Polling Interval**: Leave default (40 seconds)

2. Click **Submit**

**Expected Result**: ✅ Configuration successful, taken to device/entity list

**If it fails**:
- Check Home Assistant logs: `tail -f ~/.homeassistant/home-assistant.log`
- Look for authentication errors
- Verify credentials work at https://fireboard.io
- Note the exact error message

### Test 2: Device Discovery

**Goal**: Verify all your devices are discovered

1. After successful configuration, check the integration page
2. You should see one "device" per FireBoard device

**Expected Devices**:
- [ ] Yoder YS640s (or its FireBoard controller)
- [ ] FireBoard Spark
- [ ] FireBoard 2 Pro

**For each device, verify**:
- Device name is correct
- Device model is shown
- Serial number or UUID is displayed

### Test 3: Entity Creation

**Goal**: Verify sensors are created correctly

For each device, check for these entities:

**Temperature Sensors** (one per channel):
- [ ] `sensor.{device_name}_probe_1`
- [ ] `sensor.{device_name}_probe_2`
- [ ] `sensor.{device_name}_probe_3`
- [ ] etc.

**Battery Sensor** (if wireless):
- [ ] `sensor.{device_name}_battery`

**Binary Sensors**:
- [ ] `binary_sensor.{device_name}_connectivity`
- [ ] `binary_sensor.{device_name}_battery_low`

## Functional Testing

### Test 4: Temperature Readings

**Goal**: Verify temperature sensors show correct values

1. **Check Current Values**:
   - Open a temperature sensor entity
   - Note the current temperature
   - Compare with FireBoard app

2. **Verify Units**:
   - Should be in °F (Fahrenheit)
   - Device class should be `temperature`

3. **Test with Temperature Change**:
   - Heat up a probe (or let one cool down)
   - Wait 40 seconds (one polling cycle)
   - Refresh entity state
   - Verify temperature updated

**Expected**: ✅ Temperatures match FireBoard app within reasonable margin

### Test 5: Channel Labels

**Goal**: Verify custom channel labels appear correctly

1. In FireBoard app, set custom labels for channels:
   - Example: "Grill", "Brisket", "Pork Shoulder"
2. Wait for next update cycle (40 seconds)
3. Check entity attributes in Home Assistant

**Expected**: ✅ Labels appear in entity attributes

### Test 6: Battery Monitoring

**Goal**: Test battery level reporting (for wireless devices only)

1. Check battery sensor for your wireless device (Spark)
2. Verify battery percentage is reasonable (0-100%)
3. Compare with FireBoard app
4. Check `binary_sensor.{device}_battery_low` state

**Expected**: ✅ Battery level matches app, binary sensor OFF if >20%

### Test 7: Connectivity Status

**Goal**: Test device online/offline detection

1. Check `binary_sensor.{device}_connectivity` - should be ON
2. Turn off a FireBoard device
3. Wait 40 seconds for next update
4. Check connectivity sensor again

**Expected**: ✅ Sensor changes to OFF when device is offline

### Test 8: Multiple Devices

**Goal**: Verify multiple devices work simultaneously

1. Ensure all your devices are online
2. Check that each device appears separately
3. Verify each device has its own set of sensors
4. Confirm no entity name conflicts

**Expected**: ✅ All devices and sensors work independently

### Test 9: Update Frequency

**Goal**: Verify polling respects rate limits

1. Note the timestamp on a temperature sensor
2. Watch for updates
3. Verify updates happen approximately every 40 seconds

**Calculate rate**: 
- 40 seconds = 90 calls/hour
- Should be well under 200 calls/hour limit
- With 3 devices: ~270 calls/hour (might need adjustment)

**If you have >2 devices**: Consider increasing polling interval to 60 seconds

## Error Testing

### Test 10: Invalid Credentials

**Goal**: Verify error handling for bad credentials

1. Remove the integration
2. Try to add it again with wrong password
3. Verify clear error message appears

**Expected**: ✅ "Invalid email or password" error

### Test 11: Network Issues

**Goal**: Test behavior during connectivity loss

1. While integration is working, disconnect your internet
2. Wait 40 seconds
3. Check logs for errors
4. Reconnect internet
5. Verify integration recovers

**Expected**: ✅ Graceful error handling, automatic recovery

### Test 12: Token Expiration

**Goal**: Verify automatic re-authentication

1. Let integration run for several hours
2. Check if it continues working
3. Look for re-authentication in logs

**Expected**: ✅ Seamless re-authentication when token expires

## API Verification

### Test 13: Verify API Endpoints

**Goal**: Ensure implementation matches actual FireBoard API

While the integration is running, check the logs for any API errors:

```bash
# Watch Home Assistant logs
tail -f ~/.homeassistant/home-assistant.log | grep fireboard
```

**Look for**:
- ✅ Successful API calls
- ❌ 404 errors (wrong endpoints)
- ❌ Unexpected response format errors

**Common API variations to check**:
- Authentication endpoint: `/login` or `/auth/login`?
- Token format: `Token {token}` or `Bearer {token}`?
- Devices endpoint: `/devices` or `/v1/devices`?
- Temperature endpoint: `/devices/{uuid}/temps` or `/devices/{uuid}/temperatures`?

## Dashboard Testing

### Test 14: Create Dashboard

**Goal**: Verify entities work in dashboards

1. Create a new dashboard
2. Add a temperature gauge card
3. Add an entities card with multiple temperatures
4. Add binary sensors to show status

**Expected**: ✅ All cards display data correctly and update

### Test 15: History and Graphs

**Goal**: Verify data is being recorded

1. Let integration run for at least 5 minutes
2. Go to a temperature sensor entity
3. Click "Show More" to see history
4. Verify temperature graph displays

**Expected**: ✅ Historical data is recorded and graphable

## Automation Testing

### Test 16: Temperature Automation

**Goal**: Test automations with temperature triggers

1. Create a simple automation:
```yaml
automation:
  - alias: "Test FireBoard Temp"
    trigger:
      - platform: numeric_state
        entity_id: sensor.{your_device}_probe_1
        above: 100
    action:
      - service: persistent_notification.create
        data:
          message: "FireBoard temperature automation works!"
```

2. Heat a probe above 100°F
3. Wait for trigger

**Expected**: ✅ Automation triggers correctly

## Data Structure Verification

### Test 17: Check API Response Format

**Goal**: Verify our assumed data structures match reality

1. Enable debug logging in Home Assistant:
```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.fireboard: debug
```

2. Restart Home Assistant
3. Check logs for API responses
4. Compare with our expected format in `tests/fixtures/api_responses.json`

**Key things to verify**:
- Device object structure
- Temperature data format
- Channel information
- Battery data (if present)

## Performance Testing

### Test 18: Resource Usage

**Goal**: Ensure integration doesn't impact performance

1. Note Home Assistant memory usage before
2. Add integration with all devices
3. Let run for 1 hour
4. Check memory usage after

**Expected**: ✅ Minimal resource usage, no memory leaks

## Issue Documentation

### When You Find Issues

For each issue discovered, document:

1. **What happened**: Exact error message or behavior
2. **Expected behavior**: What should have happened
3. **Steps to reproduce**: How to trigger the issue
4. **Logs**: Relevant error messages from HA logs
5. **API responses**: If it's an API format issue

**Save to**: Create `TESTING_RESULTS.md` with your findings

## Testing Results Template

```markdown
# FireBoard Integration - Testing Results

**Testing Date**: [DATE]
**Home Assistant Version**: [VERSION]
**Integration Version**: 0.1.0

## Devices Tested
- [ ] Yoder YS640s
- [ ] FireBoard Spark  
- [ ] FireBoard 2 Pro

## Test Results

### Authentication: ✅ / ❌
- Notes:

### Device Discovery: ✅ / ❌
- Devices found:
- Notes:

### Temperature Sensors: ✅ / ❌
- Accuracy:
- Update frequency:
- Notes:

### Battery Monitoring: ✅ / ❌
- Notes:

### Connectivity Status: ✅ / ❌
- Notes:

### API Endpoints: ✅ / ❌
- Issues found:

## Issues Discovered

### Issue 1: [Title]
- **Severity**: Critical / Major / Minor
- **Description**:
- **Steps to reproduce**:
- **Expected**:
- **Actual**:
- **Logs**:

## API Response Format

### Device Object
```json
[Paste actual response]
```

### Temperature Data
```json
[Paste actual response]
```

## Recommendations

1. [Any changes needed]
2. [Configuration adjustments]
3. [Documentation updates]

## Overall Assessment

**Ready for Release**: Yes / No / With Changes

**Notes**:
```

## Next Steps After Testing

Once testing is complete and any issues are fixed:

1. **Document Results**: Fill out the testing results template
2. **Update Code**: Fix any issues discovered
3. **Update Documentation**: Adjust README based on findings
4. **Run Tests**: Ensure unit tests still pass
5. **Ready for GitHub**: Proceed with repository setup

## Quick Reference: Home Assistant Logs

```bash
# Watch live logs
tail -f ~/.homeassistant/home-assistant.log

# Filter for FireBoard only
tail -f ~/.homeassistant/home-assistant.log | grep -i fireboard

# Check for errors
grep -i "error" ~/.homeassistant/home-assistant.log | grep -i fireboard

# Check API communication
grep -i "api" ~/.homeassistant/home-assistant.log | grep -i fireboard
```

## Troubleshooting Common Issues

### Integration Doesn't Appear in UI
- Clear browser cache
- Check `custom_components/fireboard/manifest.json` exists
- Verify Home Assistant restarted fully
- Check logs for Python errors on startup

### Authentication Fails
- Test credentials at https://fireboard.io
- Check for typos in email/password
- Look for API errors in logs
- Try using the FireBoard mobile app to confirm account is active

### No Devices Found
- Verify devices are online in FireBoard app
- Check API response in logs (debug mode)
- Confirm devices are associated with your account
- Check for API endpoint errors (404s)

### Temperatures Not Updating
- Check polling interval setting
- Look for rate limit errors in logs
- Verify device is actually sending data
- Check FireBoard app shows recent data

## Need Help?

If you encounter issues during testing:
1. Save complete error logs
2. Note exact steps that cause the issue
3. Check FireBoard API documentation
4. We can debug together based on your results

