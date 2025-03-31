#!/usr/bin/env python3
# Sonos Song Tracker - Tracks songs playing on a selected Sonos device

import soco
import time
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from soco.data_structures import DidlMusicTrack, DidlResource  # Updated import

# Spotify API configuration
SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state app-remote-control streaming'
SPOTIFY_CLIENT_ID = 'c6574dd525bd4d58a95c2ef7541056bb'
SPOTIFY_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spotify_credentials.json')
SPOTIFY_REDIRECT_URIS = [
    "http://localhost:8888/callback",
    "http://127.0.0.1:8888/callback",
]

# Track origin to prevent transfer loops
LAST_TRANSFERRED_URI = None
TRANSFER_COOLDOWN = 0  # Cooldown timer to prevent immediate transfers

def load_spotify_credentials():
    """Load Spotify credentials from a file if it exists."""
    if os.path.exists(SPOTIFY_CREDENTIALS_FILE):
        try:
            with open(SPOTIFY_CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Spotify credentials: {e}")
    return None

def save_spotify_credentials(client_id, client_secret):
    """Save Spotify credentials to a file."""
    try:
        credentials = {'client_id': client_id, 'client_secret': client_secret}
        with open(SPOTIFY_CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)
        print("Spotify credentials saved for future use.")
    except Exception as e:
        print(f"Error saving Spotify credentials: {e}")

def setup_spotify_client(token=None):
    """Set up and return a Spotify client."""
    try:
        if token:
            return spotipy.Spotify(auth=token)
        else:
            credentials = load_spotify_credentials()
            client_id = SPOTIFY_CLIENT_ID
            client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET', '')

            if credentials:
                client_id = credentials.get('client_id', client_id)
                client_secret = credentials.get('client_secret')
                print("Using saved Spotify credentials.")
            elif not client_secret:
                client_secret = input("Enter your Spotify Client Secret: ").strip()
                if not client_secret:
                    raise ValueError("Client secret is required")
                if input("Save credentials? (y/n): ").lower() == 'y':
                    save_spotify_credentials(client_id, client_secret)

            for redirect_uri in SPOTIFY_REDIRECT_URIS:
                try:
                    print(f"Attempting authentication with redirect URI: {redirect_uri}")
                    auth_manager = SpotifyOAuth(
                        client_id=client_id,
                        client_secret=client_secret,
                        scope=SPOTIFY_SCOPE,
                        redirect_uri=redirect_uri,
                        open_browser=True
                    )
                    return spotipy.Spotify(auth_manager=auth_manager)
                except Exception as e:
                    print(f"Authentication failed with this redirect URI: {e}")
                    continue
            raise ValueError("Failed to authenticate with any redirect URI")
    except Exception as e:
        print(f"Error setting up Spotify client: {e}")
        print("\nCheck that your Spotify app’s redirect URI matches one of:")
        for uri in SPOTIFY_REDIRECT_URIS:
            print(f"- {uri}")
        return None

def wait_for_spotify_device(spotify, device_name):
    """Wait for an active Spotify device."""
    print("\n=== Spotify Device Connection ===")
    print("Open Spotify, play a song, and ensure a device is active.")
    
    try:
        while True:
            devices = spotify.devices()
            active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
            if active_devices:
                device = active_devices[0]
                print(f"\nConnected to: {device['name']} ({device['type']})")
                return device['id']
            print(".", end="", flush=True)
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nDevice connection cancelled.")
        return None

def update_spotify_with_sonos_track(spotify, track_info, device_id=None, device_name=None):
    """Update Spotify with the current Sonos track."""
    global LAST_TRANSFERRED_URI
    
    if not spotify or not track_info.get('title'):
        return False
    
    try:
        query = f"track:{track_info['title']} artist:{track_info['artist']}"
        results = spotify.search(q=query, type='track', limit=1)
        
        if not results['tracks']['items']:
            print(f"Could not find: {track_info['artist']} - {track_info['title']}")
            return False
            
        track_uri = results['tracks']['items'][0]['uri']
        LAST_TRANSFERRED_URI = track_uri
        
        if not device_id:
            devices = spotify.devices()
            active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
            device_id = active_devices[0]['id'] if active_devices else wait_for_spotify_device(spotify, device_name)
            if not device_id:
                return False
        
        spotify.start_playback(device_id=device_id, uris=[track_uri])
        current_position = 0
        if 'position' in track_info and track_info['position']:
            time_parts = track_info['position'].split(':')
            if len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
                current_position = (hours * 3600 + minutes * 60 + seconds) * 1000
            elif len(time_parts) == 2:
                minutes, seconds = map(int, time_parts)
                current_position = (minutes * 60 + seconds) * 1000
            spotify.seek_track(current_position, device_id=device_id)
        print(f"Updated Spotify: {track_info['artist']} - {track_info['title']}")
        return True
    except Exception as e:
        print(f"Spotify playback error: {e}")
        return False

def discover_sonos_devices():
    """Discover Sonos devices on the network."""
    print("Discovering Sonos devices...")
    return list(soco.discover())

def select_device(devices):
    """Allow user to select a Sonos device."""
    if not devices:
        print("No Sonos devices found.")
        exit(1)
    
    print("\nFound Sonos devices:")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.player_name} ({device.ip_address})")
    
    while True:
        try:
            selection = int(input("\nSelect device number: "))
            if 1 <= selection <= len(devices):
                return devices[selection - 1]
            print("Invalid selection.")
        except ValueError:
            print("Enter a number.")

def ms_to_time_string(ms):
    """Convert milliseconds to HH:MM:SS format."""
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def track_songs(device, spotify=None):
    """Track songs on the selected Sonos device."""
    print(f"\nTracking {device.player_name}...")
    spotify_device_id = None
    
    if spotify:
        print("Spotify enabled - songs will update in Spotify.")
        devices = spotify.devices()
        active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
        spotify_device_id = active_devices[0]['id'] if active_devices else None
    
    print("Press Ctrl+C to stop.\n")
    
    current_track_info = None
    
    try:
        while True:
            track_info = device.get_current_track_info()
            track_info['player_name'] = device.player_name
            
            if (not current_track_info or 
                track_info['title'] != current_track_info['title'] or
                track_info['artist'] != current_track_info['artist']):
                if track_info['title']:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] Now playing:")
                    print(f"Title: {track_info['title']}")
                    print(f"Artist: {track_info['artist']}")
                    print(f"Album: {track_info['album']}")
                    print("-" * 50)
                    current_track_info = track_info
                    
                    if spotify:
                        success = update_spotify_with_sonos_track(
                            spotify, track_info, spotify_device_id, f"EMU: {device.player_name}"
                        )
                        if success and not spotify_device_id:
                            active_devices = [d for d in spotify.devices().get('devices', []) if d.get('is_active')]
                            spotify_device_id = active_devices[0]['id'] if active_devices else None
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nStopped tracking.")

def main():
    """Main function with Spotify integration."""
    print("=== Sonos Song Tracker ===")
    
    use_spotify = input("Enable Spotify integration? (y/n): ").lower() == 'y'
    spotify = None
    
    if use_spotify:
        token = input("Spotify API token (blank for interactive): ").strip()
        spotify = setup_spotify_client(token if token else None)
        if not spotify:
            print("Spotify integration failed. Continuing without it.")
    
    devices = discover_sonos_devices()
    selected_device = select_device(devices)
    
    # Track Sonos songs and optionally update Spotify
    track_songs(selected_device, spotify)

if __name__ == "__main__":
    main()