#!/usr/bin/env python3
# BigFM Song Tracker - Fetches current playing song from BigFM and updates Spotify

import requests
import time
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
import re
import urllib.parse

# Reuse Spotify configuration from run.py
SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state app-remote-control streaming'
SPOTIFY_CLIENT_ID = 'c6574dd525bd4d58a95c2ef7541056bb'
SPOTIFY_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spotify_credentials.json')
SPOTIFY_REDIRECT_URIS = [
    "http://localhost:8888/callback",
    "http://127.0.0.1:8888/callback",
]

# Track last processed song to avoid duplicates
last_processed_song = None

def generate_bigfm_url():
    """Generate BigFM API URL with current time range for the past 5 minutes."""
    now = datetime.now()
    past = now - timedelta(minutes=5)
    
    # Format times in ISO 8601 format with URL encoding
    end_time = urllib.parse.quote_plus(now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+01:00')
    start_time = urllib.parse.quote_plus(past.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+01:00')
    
    return f"https://asw.api.iris.radiorepo.io/v2/playlist/search.json?station=3&start={start_time}&end={end_time}"

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
        print("\nCheck that your Spotify app's redirect URI matches one of:")
        for uri in SPOTIFY_REDIRECT_URIS:
            print(f"- {uri}")
        return None

def wait_for_spotify_device(spotify, device_name=None):
    """Wait for an active Spotify device."""
    print("\n=== Spotify Device Connection ===")
    print("Open Spotify, play a song, and ensure a device is active.")
    
    try:
        devices = spotify.devices()
        if not devices['devices']:
            print("No Spotify devices found. Please open Spotify and play something.")
        else:
            print("\nAvailable devices:")
            for i, device in enumerate(devices['devices'], 1):
                status = " (active)" if device['is_active'] else ""
                print(f"{i}. {device['name']} - {device['type']}{status}")
    except Exception as e:
        print(f"Error getting devices: {e}")
    
    print("\nWaiting for an active device... (Press Ctrl+C to cancel)")
    
    try:
        while True:
            try:
                devices = spotify.devices()
                active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
                
                if active_devices:
                    device = active_devices[0]
                    print(f"\nConnected to: {device['name']} ({device['type']})")
                    return device['id']
                
                print(".", end="", flush=True)
                time.sleep(3)
            except Exception as e:
                print(f"\nError checking devices: {e}")
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nDevice connection cancelled.")
        return None

def fetch_current_song():
    """Fetch the current song playing on BigFM."""
    try:
        # Generate URL with current timestamp
        url = generate_bigfm_url()
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Parse JSON response
        data = response.json()
        
        # Check if we have any entries
        entries = data.get('result', {}).get('entry', [])
        if not entries:
            return None
            
        # Get the most recent song (first entry in the list)
        latest_song = entries[0]
        song_info = latest_song.get('song', {}).get('entry', [{}])[0]
        artist_info = song_info.get('artist', {}).get('entry', [{}])[0]
        
        # Extract title and artist name
        title = song_info.get('title', '')
        artist = artist_info.get('name', '')
        
        if not title or not artist:
            return None
            
        return {
            'artist': artist,
            'title': title,
            'full_text': f"{artist} - {title}"
        }
            
    except Exception as e:
        print(f"Error fetching current song: {e}")
        return None

def update_spotify(spotify, song_info, device_id=None):
    """Update Spotify with the current BigFM song."""
    if not spotify or not song_info:
        return False
    
    try:
        # Search for the track on Spotify
        query = f"track:{song_info['title']} artist:{song_info['artist']}"
        results = spotify.search(q=query, type='track', limit=1)
        
        if not results['tracks']['items']:
            print(f"Could not find track on Spotify: {song_info['artist']} - {song_info['title']}")
            # Try a more general search without the artist
            query = f"track:{song_info['title']}"
            results = spotify.search(q=query, type='track', limit=1)
            if not results['tracks']['items']:
                print(f"Could not find track with title-only search either.")
                return False
            
        track_uri = results['tracks']['items'][0]['uri']
        found_track = results['tracks']['items'][0]
        found_artist = found_track['artists'][0]['name']
        found_title = found_track['name']
        
        print(f"Found on Spotify: {found_artist} - {found_title}")
        
        # Check if we need to wait for a device
        if not device_id:
            try:
                devices = spotify.devices()
                active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
                
                if active_devices:
                    device_id = active_devices[0]['id']
                    print(f"Using active Spotify device: {active_devices[0]['name']}")
                else:
                    print("No active Spotify devices found.")
                    device_id = wait_for_spotify_device(spotify)
                    if not device_id:
                        # User cancelled device connection
                        return False
            except Exception as e:
                print(f"Spotify device error: {e}")
                return False
        
        # Start playback with the found track on the active device
        try:
            spotify.start_playback(device_id=device_id, uris=[track_uri])
            print(f"Updated Spotify with: {found_artist} - {found_title}")
            return True
        except Exception as e:
            print(f"Spotify playback error: {e}")
            
            if "NO_ACTIVE_DEVICE" in str(e) or "Player command failed" in str(e):
                print("Device became inactive. Waiting for reconnection...")
                device_id = wait_for_spotify_device(spotify)
                if device_id:
                    # Try again with new device ID
                    spotify.start_playback(device_id=device_id, uris=[track_uri])
                    print(f"Updated Spotify with: {found_artist} - {found_title}")
                    return True
            return False
                
    except Exception as e:
        print(f"Spotify API error: {e}")
        return False

def main():
    """Main function to track BigFM and update Spotify."""
    print("=== BigFM to Spotify Integration ===")
    
    global last_processed_song
    
    # Setup Spotify client
    token = input("Enter your Spotify API token (leave blank for interactive authentication): ").strip()
    spotify = setup_spotify_client(token if token else None)
    
    if not spotify:
        print("Spotify integration could not be enabled. Exiting.")
        return
    
    # Get initial device ID
    spotify_device_id = None
    try:
        devices = spotify.devices()
        active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
        if active_devices:
            spotify_device_id = active_devices[0]['id']
            print(f"Using active device: {active_devices[0]['name']}")
        else:
            print("No active device found. Will prompt when needed.")
    except Exception as e:
        print(f"Error detecting Spotify devices: {e}")
    
    print("\nMonitoring BigFM for new songs...")
    print("Press Ctrl+C to stop tracking.")
    
    try:
        check_interval = 30  # Check every 30 seconds
        
        while True:
            try:
                # Fetch current song
                song_info = fetch_current_song()
                
                if song_info:
                    # Check if this is a new song
                    current_song = f"{song_info['artist']} - {song_info['title']}"
                    
                    if current_song != last_processed_song:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New song detected:")
                        print(f"Artist: {song_info['artist']}")
                        print(f"Title: {song_info['title']}")
                        
                        # Update Spotify
                        success = update_spotify(spotify, song_info, spotify_device_id)
                        
                        if success:
                            last_processed_song = current_song
                            
                            # If we got a device ID during this update, store it
                            if not spotify_device_id:
                                devices = spotify.devices()
                                active_devices = [d for d in devices.get('devices', []) if d.get('is_active')]
                                if active_devices:
                                    spotify_device_id = active_devices[0]['id']
                
                # Wait before checking again
                for i in range(check_interval):
                    if i % 5 == 0:  # Show a "heartbeat" dot every 5 seconds
                        print(".", end="", flush=True)
                    time.sleep(1)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\nError in main loop: {e}")
                time.sleep(check_interval)
                
    except KeyboardInterrupt:
        print("\n\nStopped tracking.")

if __name__ == "__main__":
    main()
