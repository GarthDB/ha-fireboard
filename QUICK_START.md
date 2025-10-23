# FireBoard Integration - Quick Start Guide

**Status**: Ready for Physical Device Testing ✅

## Overview

This guide provides a streamlined process to:
1. Test API connectivity (5 minutes)
2. Install in Home Assistant (10 minutes)
3. Verify with physical devices (15 minutes)
4. Deploy to GitHub and HACS (15 minutes)

**Total Time**: ~45 minutes

---

## Phase 1: Pre-Flight API Test (5 minutes)

Before installing in Home Assistant, let's verify the API endpoints work correctly.

### Step 1: Test API Connection

```bash
cd /Users/garthdb/Projects/ha-fireboard

# Install aiohttp if not already installed
pip3 install aiohttp

# Run the API test script
python3 test_api_connection.py
```

**This script will**:
- Test authentication with your FireBoard credentials
- Verify API endpoints match our implementation
- Check device discovery
- Validate temperature data structure
- Calculate rate limiting for your devices

**Expected Output**: ✅ All tests passed

**If tests fail**:
- Note the exact error messages
- Check which endpoint failed
- We'll fix the integration code before installing

---

## Phase 2: Install in Home Assistant (10 minutes)

Once API tests pass, install the integration.

### Step 2: Copy Integration Files

```bash
cd /Users/garthdb/Projects/ha-fireboard

# Copy to Home Assistant custom_components
# Adjust path if your HA config is elsewhere
cp -r custom_components/fireboard ~/.homeassistant/custom_components/

# Verify it copied correctly
ls -la ~/.homeassistant/custom_components/fireboard/
```

**Expected**: You should see all integration files including `__init__.py`, `manifest.json`, etc.

### Step 3: Restart Home Assistant

**Method 1: UI** (Recommended)
1. Go to **Settings → System**
2. Click **Restart**
3. Wait 1-2 minutes

**Method 2: Command Line**
```bash
# If using Home Assistant OS
ha core restart

# If using Docker
docker restart homeassistant

# If using venv
# Stop and start your HA process
```

### Step 4: Clear Browser Cache

**Important**: Home Assistant caches integration data

**Chrome/Edge**:
- Press `Cmd + Shift + Delete` (Mac) or `Ctrl + Shift + Delete` (Windows)
- Select "Cached images and files"
- Click "Clear data"

**Safari**:
- Press `Cmd + Option + E`
- Refresh the page

**Or**: Open Home Assistant in an Incognito/Private window

---

## Phase 3: Configure Integration (5 minutes)

### Step 5: Add FireBoard Integration

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"** (bottom right)
3. Search for **"FireBoard"**
4. Select it from the list

**Can't find it?**
- Clear browser cache again
- Check logs: `tail -f ~/.homeassistant/home-assistant.log | grep fireboard`
- Verify files are in the right location

### Step 6: Enter Credentials

**Configuration Form**:
- **Email**: Your FireBoard account email
- **Password**: Your FireBoard account password  
- **Polling Interval**: 40 (default - recommended)

Click **Submit**

**Expected**: ✅ "Configuration successful" message

**If authentication fails**:
- Verify credentials at https://fireboard.io
- Check Home Assistant logs for detailed error
- Run the API test script again to diagnose

### Step 7: Verify Devices

After successful configuration, you should see:

**Devices Tab**:
- [ ] Yoder YS640s (or its FireBoard controller)
- [ ] FireBoard Spark
- [ ] FireBoard 2 Pro

**For each device, check**:
- Device name appears correctly
- Device information is populated
- Click on device to see entities

---

## Phase 4: Verify Sensors (10 minutes)

### Step 8: Check Temperature Sensors

For each device, verify these entities exist:

**Temperature Sensors** (one per channel):
```
sensor.{device_name}_probe_1
sensor.{device_name}_probe_2
sensor.{device_name}_probe_3
... (up to 6)
```

**Click on a temperature sensor**:
- Current temperature should be displayed
- Unit should be °F
- Should match value in FireBoard app

**Check attributes**:
- `channel`: Channel number (1-6)
- `label`: Custom label from FireBoard app
- `target_temp`: Target temperature (if set)

### Step 9: Check Binary Sensors

**Connectivity Sensor**: `binary_sensor.{device_name}_connectivity`
- Should be **ON** if device is online
- Should be **OFF** if device is offline

**Battery Low Sensor**: `binary_sensor.{device_name}_battery_low`
- Should be **ON** if battery < 20%
- Should be **OFF** if battery > 20%

### Step 10: Check Battery Sensor (Wireless Devices Only)

**Battery Sensor**: `sensor.{device_name}_battery`
- Should show percentage (0-100%)
- Only exists for devices with batteries (e.g., Spark)
- Compare with FireBoard app

---

## Phase 5: Functional Testing (10 minutes)

### Step 11: Test Temperature Updates

1. **Note current temperature** on a probe
2. **Heat it up** (or let it cool down)
3. **Wait 40 seconds** (one polling cycle)
4. **Refresh** the entity state
5. **Verify** temperature changed

**Expected**: Temperature updates every 40 seconds

### Step 12: Test Multiple Devices

1. Check that all devices appear separately
2. Verify no entity name conflicts
3. Confirm each device updates independently

### Step 13: Monitor Logs

While the integration is running, watch the logs:

```bash
# Open a terminal and run:
tail -f ~/.homeassistant/home-assistant.log | grep -i fireboard
```

**Look for**:
- ✅ Successful API calls every 40 seconds
- ✅ Data updates
- ❌ Any errors or warnings

**Common things to check**:
- No rate limit errors (429)
- No authentication errors (401)
- No 404 errors (wrong endpoints)

---

## Phase 6: Create Dashboard (5 minutes)

### Step 14: Create Test Dashboard

1. Go to **Overview** (or any dashboard)
2. Click **Edit Dashboard** (top right)
3. Click **"+ Add Card"**
4. Choose **"Entities"** card
5. Add your FireBoard sensors

**Example Configuration**:
```yaml
type: entities
title: FireBoard Temperatures
entities:
  - entity: sensor.backyard_smoker_probe_1
    name: Grill Temp
  - entity: sensor.backyard_smoker_probe_2
    name: Brisket
  - entity: sensor.fireboard_spark_battery
    name: Spark Battery
  - entity: binary_sensor.backyard_smoker_connectivity
    name: Status
```

**Verify**: All entities display correctly and update every 40 seconds

---

## Phase 7: Document Results

### Step 15: Record Testing Results

Create `TESTING_RESULTS.md` with your findings:

```markdown
# FireBoard Integration - Testing Results

**Date**: October 23, 2024
**Tester**: Garth DB
**HA Version**: [YOUR VERSION]

## Devices Tested
- [x] Yoder YS640s
- [x] FireBoard Spark
- [x] FireBoard 2 Pro

## Test Results

### API Connection: ✅ / ❌
- Authentication: 
- Device Discovery:
- Temperature Data:

### Integration Installation: ✅ / ❌
- Files copied correctly:
- Integration appeared in UI:
- Configuration successful:

### Sensor Creation: ✅ / ❌
- Temperature sensors:
- Battery sensors:
- Binary sensors:

### Functional Tests: ✅ / ❌
- Temperature updates:
- Update frequency:
- Multiple device support:

## Issues Found

### Issue 1: [If any]
- Description:
- Severity: Critical / Major / Minor
- Steps to reproduce:
- Logs:

## API Endpoint Verification

- Authentication endpoint: `/login` ✅ / ❌
- Token format: `Token {token}` ✅ / ❌
- Devices endpoint: `/devices` ✅ / ❌
- Temperature endpoint: `/devices/{uuid}/temps` ✅ / ❌

## Recommendations

[Any changes needed to the integration]

## Overall Assessment

**Ready for GitHub/HACS**: Yes / No / With Changes
```

---

## Phase 8: GitHub Setup (15 minutes)

**Only proceed if testing was successful!**

### Step 16: Initialize Git Repository

```bash
cd /Users/garthdb/Projects/ha-fireboard

# Initialize repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial implementation of FireBoard Home Assistant integration

- Direct FireBoard Cloud API integration
- UI-based configuration with config flow
- Temperature sensors per channel
- Battery monitoring for wireless devices
- Binary sensors for connectivity and battery status
- Comprehensive test coverage (>80%)
- Full documentation and examples
- HACS compatible

Supported devices:
- FireBoard 2 Pro
- FireBoard Spark
- Other FireBoard models

Features:
- No MQTT broker required
- Auto-discovery of devices
- Real-time temperature updates
- Rate limiting (200 calls/hour)
- Error handling and authentication
"
```

### Step 17: Create GitHub Repository

1. Go to https://github.com/new
2. **Repository name**: `ha-fireboard`
3. **Description**: "Home Assistant integration for FireBoard wireless thermometers"
4. **Visibility**: Public
5. **Don't** initialize with README (we have one)
6. Click **"Create repository"**

### Step 18: Push to GitHub

```bash
# Add remote
git remote add origin https://github.com/GarthDB/ha-fireboard.git

# Push code
git branch -M main
git push -u origin main
```

### Step 19: Configure Repository

**Settings to configure**:

1. **Enable Issues**:
   - Go to **Settings → General**
   - Check "Issues"

2. **Add Topics**:
   - Click "Add topics" (top of repo page)
   - Add: `home-assistant`, `fireboard`, `hacs`, `thermometer`, `bbq`, `homeassistant-integration`

3. **Create Repository Description**:
   - Edit description at top of page
   - Add: "Home Assistant integration for FireBoard wireless thermometers"
   - Add website: `https://fireboard.io`

4. **Branch Protection** (Optional for now):
   - Settings → Branches
   - Add rule for `main`
   - Enable: "Require status checks to pass before merging"

---

## Phase 9: Create Release (5 minutes)

### Step 20: Create v0.1.0 Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Initial release

First public release of the FireBoard Home Assistant integration.

Features:
- Direct FireBoard Cloud API integration
- UI-based configuration
- Temperature monitoring (all channels)
- Battery monitoring (wireless devices)
- Connectivity status
- Auto-discovery
- Rate limiting
- HACS compatible

Tested with:
- Yoder YS640s
- FireBoard Spark
- FireBoard 2 Pro
"

# Push the tag
git push origin v0.1.0
```

### Step 21: Create GitHub Release

1. Go to your repo: `https://github.com/GarthDB/ha-fireboard`
2. Click **"Releases"** (right sidebar)
3. Click **"Draft a new release"**
4. Choose tag: **v0.1.0**
5. Release title: **"FireBoard Integration v0.1.0 - Initial Release"**
6. Description:

```markdown
# FireBoard Home Assistant Integration v0.1.0

First public release! 🎉

## What's New

This is the initial release of the FireBoard Home Assistant integration, providing direct cloud API integration with your FireBoard devices.

### Features

✅ **Direct API Integration** - No MQTT broker required
✅ **UI Configuration** - Easy setup through Home Assistant UI  
✅ **Auto-Discovery** - Automatically discovers all devices and channels
✅ **Temperature Monitoring** - Real-time temperature readings from all channels
✅ **Battery Monitoring** - Track battery levels on wireless devices
✅ **Connectivity Status** - Know when devices go offline
✅ **Rate Limiting** - Respects FireBoard's 200 calls/hour limit
✅ **HACS Compatible** - Easy installation through HACS

### Supported Devices

- FireBoard 2 Pro (6-channel WiFi thermometer)
- FireBoard Spark (Portable instant-read)  
- Other FireBoard models compatible with FireBoard Cloud

### Installation

#### Via HACS (Recommended)
1. Open HACS → Integrations
2. Click "+ Explore & Download Repositories"
3. Search for "FireBoard"
4. Download and restart Home Assistant

#### Manual Installation
1. Download `fireboard.zip` from this release
2. Extract to `custom_components/fireboard/`
3. Restart Home Assistant

### Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "FireBoard"
4. Enter your FireBoard credentials
5. Done!

### Documentation

- [README](https://github.com/GarthDB/ha-fireboard/blob/main/README.md) - Full documentation
- [Examples](https://github.com/GarthDB/ha-fireboard/blob/main/README.md#dashboard-examples) - Dashboard and automation examples
- [Troubleshooting](https://github.com/GarthDB/ha-fireboard/blob/main/README.md#troubleshooting) - Common issues

### Tested With

✅ Yoder YS640s
✅ FireBoard Spark
✅ FireBoard 2 Pro

### Requirements

- Home Assistant 2023.1.0 or newer
- FireBoard account with devices
- Internet connection for cloud API access

### Support

- [Report Issues](https://github.com/GarthDB/ha-fireboard/issues)
- [Discussions](https://github.com/GarthDB/ha-fireboard/discussions)

---

**First time?** Check out the [README](https://github.com/GarthDB/ha-fireboard/blob/main/README.md) for detailed setup instructions and examples.
```

7. Click **"Publish release"**

---

## Phase 10: Submit to HACS (10 minutes)

### Step 22: Verify HACS Requirements

Check that your repository meets all requirements:

- [x] Public GitHub repository
- [x] `hacs.json` in repository root
- [x] `manifest.json` with proper format
- [x] README with installation instructions
- [x] Tagged release (v0.1.0)
- [x] License file (MIT)
- [x] Integration in `custom_components/` directory

### Step 23: Submit to HACS

1. Go to [HACS Integration Submission](https://github.com/hacs/default/issues/new?assignees=&labels=integration&template=integration.yml)
2. Fill out the form:
   - **Repository**: `https://github.com/GarthDB/ha-fireboard`
   - **Description**: Home Assistant integration for FireBoard wireless thermometers
   - **Category**: Integration
3. Submit the form

**Wait time**: Usually 1-3 days for review

### Step 24: Respond to Review

HACS maintainers may ask for changes:
- Respond promptly
- Make requested changes
- Push updates to your repo
- Comment on the submission issue when ready

---

## Success Checklist

Before marking this project complete, verify:

### Testing
- [ ] API connection test passed
- [ ] Integration installed in Home Assistant
- [ ] All devices discovered
- [ ] Temperature sensors working
- [ ] Battery sensors working (wireless devices)
- [ ] Binary sensors working
- [ ] Updates every 40 seconds
- [ ] No rate limiting errors
- [ ] Dashboard cards display correctly
- [ ] Tested with all physical devices

### GitHub
- [ ] Repository created and pushed
- [ ] Issues enabled
- [ ] Topics added
- [ ] README displays correctly
- [ ] License file included
- [ ] Tagged release (v0.1.0) created
- [ ] GitHub release published

### HACS
- [ ] `hacs.json` validated
- [ ] Submission created
- [ ] Awaiting review

### Documentation
- [ ] TESTING_RESULTS.md created with findings
- [ ] README updated with any testing discoveries
- [ ] Examples tested and verified

---

## Troubleshooting

### Integration Not Appearing in UI

**Problem**: Can't find "FireBoard" in Add Integration list

**Solutions**:
1. Clear browser cache completely
2. Try incognito/private window
3. Check files are in: `~/.homeassistant/custom_components/fireboard/`
4. Check logs: `grep -i fireboard ~/.homeassistant/home-assistant.log`
5. Verify `manifest.json` is valid JSON

### API Test Script Fails

**Problem**: `test_api_connection.py` shows errors

**Solutions**:
1. Check credentials at https://fireboard.io
2. Ensure internet connection is working
3. Check if FireBoard API is down: https://status.fireboard.io (if exists)
4. Note exact error and endpoint that failed
5. We'll update the integration code to match actual API

### Rate Limit Errors

**Problem**: "Rate limit exceeded" in logs

**Solutions**:
1. Increase polling interval to 60 seconds
2. Check if you have multiple HA instances using same account
3. Calculate: (3600 / interval) * num_devices should be < 200

### Devices Not Discovered

**Problem**: Integration configures but no devices appear

**Solutions**:
1. Check devices are online in FireBoard app
2. Check logs for API errors
3. Verify devices are associated with your account
4. Try removing and re-adding integration

---

## Getting Help

If you encounter issues during testing:

1. **Document the issue**:
   - Exact error message
   - Steps to reproduce
   - Logs from Home Assistant
   - API test script output

2. **Check these files**:
   - `~/.homeassistant/home-assistant.log`
   - Output from `test_api_connection.py`
   - Browser console (F12)

3. **Create TESTING_RESULTS.md** with your findings

4. We can debug together based on your results!

---

## Next Steps After HACS Submission

While waiting for HACS review:

1. **Monitor your repository**:
   - Watch for issues from users
   - Respond to questions
   - Fix any bugs discovered

2. **Improve documentation**:
   - Add screenshots
   - Create video guide
   - Write blog post

3. **Community engagement**:
   - Post on Home Assistant community forum
   - Share on Reddit r/homeassistant
   - Tweet about it

4. **Future enhancements**:
   - Additional sensor types
   - Configuration options
   - Advanced features
   - Support for more device models

---

## Congratulations! 🎉

Once you've completed all these steps, you'll have:

- ✅ A fully tested Home Assistant integration
- ✅ Code on GitHub with proper documentation
- ✅ A tagged release
- ✅ HACS submission pending

**Estimated total time**: ~45 minutes (plus HACS review wait time)

---

**Questions?** Create an issue on GitHub or ask in the Home Assistant community!

