#!/usr/bin/env python3
"""
Generate DefaultLoadControl settings for ExoPlayer based on an HLS live stream.
Includes a custom User-Agent to mimic an Android Chrome browser.
"""

import sys
import re
import requests
from urllib.parse import urlparse

# Default User-Agent that mimics Chrome on Android 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36"
)

def fetch_playlist(url, user_agent=DEFAULT_USER_AGENT):
    """
    Download the HLS playlist content using the given User-Agent.
    """
    headers = {
        'User-Agent': user_agent,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching playlist: {e}", file=sys.stderr)
        sys.exit(1)

def parse_target_duration(playlist_text):
    """Extract EXT-X-TARGETDURATION value."""
    match = re.search(r'#EXT-X-TARGETDURATION:(\d+)', playlist_text)
    if match:
        return int(match.group(1))
    else:
        print("ERROR: No EXT-X-TARGETDURATION found. Is this a live playlist?", file=sys.stderr)
        sys.exit(1)

def is_low_latency(playlist_text):
    """Check if the playlist contains LL-HLS tags (EXT-X-PART or EXT-X-PRELOAD-HINT)."""
    return '#EXT-X-PART' in playlist_text or '#EXT-X-PRELOAD-HINT' in playlist_text

def recommend_settings(target_duration, low_latency):
    """
    Return a dictionary of recommended LoadControl parameters (in milliseconds).
    All values are multiples of target_duration.
    """
    if low_latency:
        # For low-latency, keep buffer very small to minimize latency.
        factor_min = 2
        factor_max = 3
        factor_start = 1
        factor_rebuffer = 1
    else:
        # Standard live: more buffer for stability.
        factor_min = 3
        factor_max = 6
        factor_start = 1
        factor_rebuffer = 2

    target_ms = target_duration * 1000
    return {
        'minBufferMs': factor_min * target_ms,
        'maxBufferMs': factor_max * target_ms,
        'bufferForPlaybackMs': factor_start * target_ms,
        'bufferForPlaybackAfterRebufferMs': factor_rebuffer * target_ms,
        'backBufferMs': 120_000,  # default 2 minutes, adjust as needed
        'retainBackBufferFromKeyframe': True
    }

def print_java_code(settings):
    """Output Java code snippet for DefaultLoadControl.Builder."""
    print("\n// Recommended DefaultLoadControl settings (Java)\n")
    print("DefaultLoadControl.Builder builder = new DefaultLoadControl.Builder();")
    print("builder.setBufferDurationsMs(")
    print(f"    {settings['minBufferMs']},  // minBufferMs")
    print(f"    {settings['maxBufferMs']},  // maxBufferMs")
    print(f"    {settings['bufferForPlaybackMs']},  // bufferForPlaybackMs")
    print(f"    {settings['bufferForPlaybackAfterRebufferMs']}   // bufferForPlaybackAfterRebufferMs")
    print(");")
    print(f"builder.setBackBuffer({settings['backBufferMs']}, {str(settings['retainBackBufferFromKeyframe']).lower()});")
    print("DefaultLoadControl loadControl = builder.build();")

def print_json(settings):
    """Output JSON for programmatic use."""
    import json
    print("\n// JSON configuration\n")
    print(json.dumps(settings, indent=2))

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <HLS_PLAYLIST_URL> [--user-agent <custom_ua>]")
        sys.exit(1)

    url = sys.argv[1]
    user_agent = DEFAULT_USER_AGENT

    # Optional custom user agent via command-line flag
    if '--user-agent' in sys.argv:
        idx = sys.argv.index('--user-agent')
        if idx + 1 < len(sys.argv):
            user_agent = sys.argv[idx + 1]
        else:
            print("ERROR: --user-agent requires a value", file=sys.stderr)
            sys.exit(1)

    print(f"Fetching playlist from: {url}")
    print(f"Using User-Agent: {user_agent}\n")

    playlist_text = fetch_playlist(url, user_agent)

    target_duration = parse_target_duration(playlist_text)
    print(f"Detected EXT-X-TARGETDURATION: {target_duration} seconds")

    low_latency = is_low_latency(playlist_text)
    print(f"Low-latency stream: {'Yes' if low_latency else 'No'}")

    settings = recommend_settings(target_duration, low_latency)

    print_java_code(settings)
    print_json(settings)

if __name__ == "__main__":
    main()
