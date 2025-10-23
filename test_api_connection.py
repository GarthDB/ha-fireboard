#!/usr/bin/env python3
"""
FireBoard API Connection Test Script

This script helps verify that the FireBoard API endpoints and data structures
match what the integration expects. Run this BEFORE installing in Home Assistant
to catch any API discrepancies.

Usage:
    python3 test_api_connection.py

You'll be prompted for your FireBoard credentials.
"""

import asyncio
import json
import sys
from getpass import getpass

import aiohttp


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(msg):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg):
    """Print error message."""
    print(f"{Colors.RED}✗ {msg}{Colors.END}")


def print_info(msg):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def print_warning(msg):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")


def print_header(msg):
    """Print header message."""
    print(f"\n{Colors.BOLD}{msg}{Colors.END}")


async def test_fireboard_api():
    """Test FireBoard API connection and data structures."""
    
    print_header("FireBoard API Connection Test")
    print_info("This will test your FireBoard API credentials and verify data structures\n")
    
    # Get credentials
    email = input("FireBoard Email: ").strip()
    password = getpass("FireBoard Password: ")
    
    if not email or not password:
        print_error("Email and password are required")
        return False
    
    api_base_url = "https://fireboard.io/api/v1"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Authentication
        print_header("Test 1: Authentication")
        try:
            async with session.post(
                f"{api_base_url}/login",
                json={"email": email, "password": password},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 401:
                    print_error("Authentication failed: Invalid credentials")
                    return False
                elif response.status == 404:
                    print_error("Authentication endpoint not found")
                    print_warning("Trying alternate endpoint: /auth/login")
                    async with session.post(
                        f"{api_base_url}/auth/login",
                        json={"email": email, "password": password},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as alt_response:
                        if alt_response.status == 200:
                            auth_data = await alt_response.json()
                            print_success("Authenticated with alternate endpoint: /auth/login")
                        else:
                            print_error(f"Alternate endpoint failed: {alt_response.status}")
                            return False
                elif response.status == 200:
                    auth_data = await response.json()
                    print_success("Authentication successful")
                else:
                    print_error(f"Unexpected status code: {response.status}")
                    return False
                
                print_info(f"Response: {json.dumps(auth_data, indent=2)}")
                
                # Extract token
                token = auth_data.get("auth_token") or auth_data.get("token")
                if not token:
                    print_error("No authentication token in response")
                    print_warning(f"Available keys: {list(auth_data.keys())}")
                    return False
                
                print_success(f"Token received: {token[:20]}...")
                
        except aiohttp.ClientError as e:
            print_error(f"Connection error: {e}")
            return False
        except asyncio.TimeoutError:
            print_error("Connection timeout")
            return False
        
        # Test 2: Get Devices
        print_header("Test 2: Get Devices")
        headers = {"Authorization": f"Token {token}"}
        
        try:
            async with session.get(
                f"{api_base_url}/devices",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 401:
                    print_warning("Token format might be wrong. Trying 'Bearer' instead of 'Token'")
                    headers = {"Authorization": f"Bearer {token}"}
                    async with session.get(
                        f"{api_base_url}/devices",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as retry_response:
                        if retry_response.status == 200:
                            devices = await retry_response.json()
                            print_success("Retrieved devices with 'Bearer' token format")
                        else:
                            print_error(f"Failed with Bearer token: {retry_response.status}")
                            return False
                elif response.status == 200:
                    devices = await response.json()
                    print_success("Retrieved devices successfully")
                else:
                    print_error(f"Failed to get devices: {response.status}")
                    text = await response.text()
                    print_warning(f"Response: {text}")
                    return False
                
                if not isinstance(devices, list):
                    print_warning("Devices response is not a list, might need to extract from object")
                    print_info(f"Response type: {type(devices)}")
                    print_info(f"Response keys: {devices.keys() if isinstance(devices, dict) else 'N/A'}")
                    if isinstance(devices, dict) and "devices" in devices:
                        devices = devices["devices"]
                        print_info("Extracted devices from response object")
                
                print_info(f"Found {len(devices)} device(s)")
                print_info(f"\nDevices Response:\n{json.dumps(devices, indent=2)}")
                
                if not devices:
                    print_warning("No devices found in your account")
                    print_info("Make sure your FireBoard devices are registered and online")
                    return False
                
                # Analyze device structure
                print_header("Device Structure Analysis")
                device = devices[0]
                expected_keys = ["uuid", "title", "hardware_id", "model", "battery_level"]
                
                for key in expected_keys:
                    if key in device:
                        print_success(f"Found expected key: '{key}'")
                    else:
                        print_warning(f"Missing expected key: '{key}'")
                
                actual_keys = set(device.keys())
                unexpected_keys = actual_keys - set(expected_keys)
                if unexpected_keys:
                    print_info(f"Additional keys found: {', '.join(unexpected_keys)}")
                
                device_uuid = device.get("uuid") or device.get("id") or device.get("device_id")
                if not device_uuid:
                    print_error("Cannot find device UUID/ID in response")
                    return False
                
                print_success(f"Device UUID: {device_uuid}")
                
        except aiohttp.ClientError as e:
            print_error(f"Connection error: {e}")
            return False
        
        # Test 3: Get Temperatures
        print_header("Test 3: Get Temperature Data")
        
        try:
            # Try standard endpoint first
            async with session.get(
                f"{api_base_url}/devices/{device_uuid}/temps",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 404:
                    print_warning("Endpoint /temps not found, trying /temperatures")
                    async with session.get(
                        f"{api_base_url}/devices/{device_uuid}/temperatures",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as alt_response:
                        if alt_response.status == 200:
                            temp_data = await alt_response.json()
                            print_success("Retrieved temperatures from alternate endpoint")
                        else:
                            print_error(f"Alternate endpoint failed: {alt_response.status}")
                            return False
                elif response.status == 200:
                    temp_data = await response.json()
                    print_success("Retrieved temperature data")
                else:
                    print_error(f"Failed to get temperatures: {response.status}")
                    return False
                
                print_info(f"\nTemperature Response:\n{json.dumps(temp_data, indent=2)}")
                
                # Analyze temperature structure
                print_header("Temperature Structure Analysis")
                
                if "channels" in temp_data:
                    channels = temp_data["channels"]
                    print_success(f"Found {len(channels)} channels")
                    
                    if channels:
                        channel = channels[0]
                        expected_keys = ["channel", "label", "current_temp", "target_temp"]
                        
                        for key in expected_keys:
                            if key in channel:
                                print_success(f"Found expected key: '{key}'")
                            else:
                                print_warning(f"Missing expected key: '{key}'")
                        
                        # Check for alternate key names
                        if "current_temp" not in channel:
                            if "temp" in channel:
                                print_warning("Using 'temp' instead of 'current_temp'")
                            elif "temperature" in channel:
                                print_warning("Using 'temperature' instead of 'current_temp'")
                else:
                    print_warning("No 'channels' key in temperature response")
                    print_info(f"Available keys: {list(temp_data.keys())}")
                
        except aiohttp.ClientError as e:
            print_error(f"Connection error: {e}")
            return False
        
        # Test 4: Rate Limiting Check
        print_header("Test 4: Rate Limiting Check")
        print_info("FireBoard API allows 200 calls per hour")
        print_info("With 40-second polling interval: ~90 calls/hour per device")
        
        num_devices = len(devices)
        calls_per_device = 90  # 40-second polling
        total_calls = calls_per_device * num_devices
        
        if total_calls > 200:
            print_error(f"⚠️  WARNING: {num_devices} devices = ~{total_calls} calls/hour")
            print_warning(f"This exceeds the 200 calls/hour limit!")
            print_info(f"Recommended: Increase polling interval to {int(40 * total_calls / 200) + 5} seconds")
        else:
            print_success(f"Rate limit OK: {num_devices} devices = ~{total_calls} calls/hour")
        
        # Summary
        print_header("Summary")
        print_success("All API tests passed!")
        print_info(f"Devices found: {num_devices}")
        print_info("The integration should work with your FireBoard account")
        
        return True


async def main():
    """Main entry point."""
    try:
        success = await test_fireboard_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

