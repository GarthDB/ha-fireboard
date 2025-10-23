# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of our integration seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **Email**: Send details to garthdb@gmail.com
2. **GitHub Security Advisory**: Use the [Security Advisory](https://github.com/GarthDB/ha-fireboard/security/advisories/new) feature

### What to Include

Please include the following information in your report:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### What to Expect

- **Initial Response**: Within 48 hours, you'll receive acknowledgment of your report
- **Status Updates**: We'll keep you informed about our progress
- **Fix Timeline**: We aim to release a fix within 90 days of initial report
- **Credit**: With your permission, we'll credit you in the security advisory

## Security Considerations

### Authentication

- **Credentials Storage**: User credentials are stored in Home Assistant's secure config entry system
- **Token Handling**: API tokens are stored in memory only and refreshed as needed
- **No Logging**: Credentials and tokens are never logged

### API Communication

- **HTTPS Only**: All API communication uses HTTPS
- **Token Authentication**: API tokens are sent in headers, not URLs
- **Rate Limiting**: Built-in rate limiting prevents abuse

### Data Privacy

- **Local Processing**: All data processing happens locally in Home Assistant
- **No Third-Party Sharing**: We don't share data with any third parties
- **Minimal Data Collection**: Only necessary device and temperature data is fetched

### Dependencies

- **Regular Updates**: Dependencies are regularly updated for security patches
- **Minimal Dependencies**: We use minimal external dependencies
- **Dependency Scanning**: Automated security scanning via GitHub Actions

### Best Practices for Users

1. **Strong Passwords**: Use strong, unique passwords for your FireBoard account
2. **Keep Updated**: Keep Home Assistant and this integration updated
3. **Secure Network**: Ensure your Home Assistant instance is on a secure network
4. **HTTPS**: Access Home Assistant over HTTPS
5. **Firewall**: Use a firewall to restrict access to Home Assistant

## Known Security Limitations

- **Cloud API Dependency**: This integration relies on FireBoard's cloud API
- **API Rate Limits**: FireBoard enforces rate limits (200 calls/hour)
- **No Local Access**: Currently no support for local network access

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release patches as soon as possible
5. Publish a security advisory on GitHub

## Security Update Notifications

To receive security updates:

1. **Watch Repository**: Click "Watch" → "Custom" → "Security alerts"
2. **GitHub Notifications**: Enable notifications for security advisories
3. **HACS**: Keep HACS integration updated for automatic notifications

## Supported Security Features

- ✅ Secure credential storage via Home Assistant config entries
- ✅ HTTPS-only API communication
- ✅ Token-based authentication with automatic refresh
- ✅ Rate limiting to prevent API abuse
- ✅ No credential logging
- ✅ Automated dependency security scanning
- ✅ Regular security updates

## Contact

For security concerns, contact:
- **Email**: garthdb@gmail.com
- **GitHub**: [@GarthDB](https://github.com/GarthDB)

## Acknowledgments

We appreciate the security research community and will credit researchers who responsibly disclose vulnerabilities (with their permission).

