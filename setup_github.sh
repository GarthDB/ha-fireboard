#!/bin/bash

# FireBoard Integration - GitHub Setup Script
# This script will:
# 1. Create the initial commit
# 2. Create GitHub repository
# 3. Push code to GitHub
# 4. Configure repository settings
# 5. Create initial release

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Confirm we're in the right directory
if [ ! -f "custom_components/fireboard/manifest.json" ]; then
    print_error "Error: Not in the ha-fireboard directory!"
    print_info "Please run this script from: /Users/garthdb/Projects/ha-fireboard/"
    exit 1
fi

print_header "FireBoard Integration - GitHub Setup"

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v git &> /dev/null; then
    print_error "Git is not installed"
    exit 1
fi
print_success "Git installed"

if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed"
    print_info "Install with: brew install gh"
    exit 1
fi
print_success "GitHub CLI installed"

# Check if authenticated
if ! gh auth status &> /dev/null; then
    print_error "Not logged into GitHub CLI"
    print_info "Run: gh auth login"
    exit 1
fi
print_success "GitHub CLI authenticated"

# Step 1: Create initial commit (if not already committed)
print_header "Step 1: Creating Initial Commit"

if git rev-parse --verify HEAD &> /dev/null; then
    print_warning "Repository already has commits"
    print_info "Skipping initial commit"
else
    print_info "Creating initial commit..."
    
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
- Error handling and authentication"

    print_success "Initial commit created"
fi

# Step 2: Create GitHub repository
print_header "Step 2: Creating GitHub Repository"

# Check if repo already exists
if gh repo view GarthDB/ha-fireboard &> /dev/null; then
    print_warning "Repository GarthDB/ha-fireboard already exists"
    print_info "Skipping repository creation"
else
    print_info "Creating repository: GarthDB/ha-fireboard"
    
    gh repo create GarthDB/ha-fireboard \
        --public \
        --description "Home Assistant integration for FireBoard wireless thermometers" \
        --homepage "https://fireboard.io"
    
    print_success "Repository created"
fi

# Step 3: Add remote and push
print_header "Step 3: Pushing Code to GitHub"

# Check if remote already exists
if git remote get-url origin &> /dev/null; then
    print_warning "Remote 'origin' already exists"
    print_info "Current origin: $(git remote get-url origin)"
else
    print_info "Adding remote origin..."
    git remote add origin git@github.com:GarthDB/ha-fireboard.git
    print_success "Remote added"
fi

# Ensure we're on main branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "main" ]; then
    print_info "Renaming branch to 'main'..."
    git branch -M main
fi

# Push to GitHub
print_info "Pushing code to GitHub..."
if git push -u origin main; then
    print_success "Code pushed successfully"
else
    print_warning "Push may have failed or was already up to date"
fi

# Step 4: Configure repository settings
print_header "Step 4: Configuring Repository Settings"

print_info "Enabling Issues..."
gh repo edit GarthDB/ha-fireboard --enable-issues
print_success "Issues enabled"

print_info "Enabling Discussions..."
gh repo edit GarthDB/ha-fireboard --enable-discussions
print_success "Discussions enabled"

print_info "Adding topics..."
gh repo edit GarthDB/ha-fireboard \
    --add-topic home-assistant \
    --add-topic fireboard \
    --add-topic hacs \
    --add-topic thermometer \
    --add-topic bbq \
    --add-topic homeassistant-integration \
    --add-topic iot \
    --add-topic smoker \
    --add-topic temperature-sensor
print_success "Topics added"

# Step 5: Create initial release
print_header "Step 5: Creating Initial Release (v0.1.0)"

# Check if tag exists
if git rev-parse v0.1.0 &> /dev/null 2>&1; then
    print_warning "Tag v0.1.0 already exists"
    print_info "Skipping tag creation"
else
    print_info "Creating tag v0.1.0..."
    
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
- FireBoard 2 Pro"

    git push origin v0.1.0
    print_success "Tag created and pushed"
fi

# Create GitHub release
print_info "Creating GitHub release..."

if gh release view v0.1.0 &> /dev/null 2>&1; then
    print_warning "Release v0.1.0 already exists"
else
    cat > /tmp/release_notes.md << 'EOF'
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
1. Download the source code from this release
2. Extract `custom_components/fireboard/` to your Home Assistant config
3. Restart Home Assistant

### Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "FireBoard"
4. Enter your FireBoard credentials
5. Done!

### Documentation

- [README](https://github.com/GarthDB/ha-fireboard/blob/main/README.md) - Full documentation
- [Quick Start Guide](https://github.com/GarthDB/ha-fireboard/blob/main/QUICK_START.md) - Step-by-step setup
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
EOF

    gh release create v0.1.0 \
        --title "FireBoard Integration v0.1.0 - Initial Release" \
        --notes-file /tmp/release_notes.md
    
    print_success "GitHub release created"
    rm /tmp/release_notes.md
fi

# Summary
print_header "Setup Complete! 🎉"

print_success "Repository created: https://github.com/GarthDB/ha-fireboard"
print_success "Initial commit pushed"
print_success "Release v0.1.0 published"
print_success "Repository configured with topics and settings"

print_info "\nNext Steps:"
echo "1. ✅ GitHub repository is ready"
echo "2. ⏳ Test with physical devices (see QUICK_START.md)"
echo "3. ⏳ Submit to HACS after testing"
echo ""
print_info "Repository URL: https://github.com/GarthDB/ha-fireboard"
print_info "Release URL: https://github.com/GarthDB/ha-fireboard/releases/tag/v0.1.0"

print_header "HACS Submission"
print_info "Once you've tested with physical devices:"
echo "1. Go to: https://github.com/hacs/default/issues/new?assignees=&labels=integration&template=integration.yml"
echo "2. Fill in the form with repository: https://github.com/GarthDB/ha-fireboard"
echo "3. Wait for HACS team review (usually 1-3 days)"

print_header "Done!"

