#!/usr/bin/env python3
"""Shared Spotify utility functions for authentication and playback."""

import os
import json
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Spotify API configuration
SPOTIFY_SCOPE = 'user-read-playback-state user-modify-playback-state app-remote-control streaming'
SPOTIFY_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spotify_credentials.json')
SPOTIFY_REDIRECT_URIS = [
    "http://localhost:8888/callback",
    "http://127.0.0.1:8888/callback",
]

def load_spotify_credentials():
    """Load Spotify credentials from a file if it exists.
    
    Returns:
        dict: A dictionary with client_id and client_secret, or None if not found
    """
    if os.path.exists(SPOTIFY_CREDENTIALS_FILE):
        try:
            with open(SPOTIFY_CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Spotify credentials: {e}")
    return None

def save_spotify_credentials(client_id, client_secret):
    """Save Spotify credentials to a file.
    
    Args:
        client_id (str): Spotify client ID
        client_secret (str): Spotify client secret
    """
    try:
        credentials = {'client_id': client_id, 'client_secret': client_secret}
        with open(SPOTIFY_CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f)
        print("Spotify credentials saved for future use.")
    except Exception as e:
        print(f"Error saving Spotify credentials: {e}")

def setup_spotify_client(token=None, default_client_id=''):
    """Set up and return a Spotify client.
    
    Args:
        token (str, optional): Spotify API token. Defaults to None.
        default_client_id (str, optional): Default client ID to use. Defaults to ''.
    
    Returns:
        spotipy.Spotify: A configured Spotify client or None if setup fails
    """
    try:
        if token:
            return spotipy.Spotify(auth=token)
        else:
            credentials = load_spotify_credentials()
            client_id = default_client_id
            client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET', '')
            
            # Track if we need to prompt for save
            credentials_changed = False

            if credentials:
                client_id = credentials.get('client_id', client_id)
                client_secret = credentials.get('client_secret', client_secret)
                print("Using saved Spotify credentials.")
            
            # Check if either credential is missing
            if not client_id:
                client_id = input("Enter your Spotify Client ID: ").strip()
                if not client_id:
                    raise ValueError("Client ID is required")
                credentials_changed = True
                
            if not client_secret:
                client_secret = input("Enter your Spotify Client Secret: ").strip()
                if not client_secret:
                    raise ValueError("Client secret is required")
                credentials_changed = True
            
            # Only ask to save if we had to prompt for at least one credential
            if credentials_changed and input("Save credentials? (y/n): ").lower() == 'y':
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
    """Wait for an active Spotify device.
    
    Args:
        spotify (spotipy.Spotify): Spotify client
        device_name (str, optional): Name of the device to wait for. Defaults to None.
    
    Returns:
        str: Device ID of the active device, or None if cancelled
    """
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

def find_and_play_track(spotify, artist, title, device_id=None):
    """Find a track on Spotify and play it.
    
    Args:
        spotify (spotipy.Spotify): Spotify client
        artist (str): Track artist
        title (str): Track title
        device_id (str, optional): Device ID to play on. Defaults to None.
    
    Returns:
        bool: Whether playback was successful
        str: Updated device_id that was used (or None)
    """
    try:
        # Search with both artist and title
        query = f"track:{title} artist:{artist}"
        results = spotify.search(q=query, type='track', limit=1)
        
        if not results['tracks']['items']:
            print(f"Could not find track on Spotify: {artist} - {title}")
            # Try a more general search with just the title
            query = f"track:{title}"
            results = spotify.search(q=query, type='track', limit=1)
            if not results['tracks']['items']:
                print(f"Could not find track with title-only search either.")
                return False, device_id
            
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
                        return False, None
            except Exception as e:
                print(f"Spotify device error: {e}")
                return False, device_id
        
        # Start playback with the found track on the active device
        try:
            spotify.start_playback(device_id=device_id, uris=[track_uri])
            print(f"Updated Spotify with: {found_artist} - {found_title}")
            return True, device_id
        except Exception as e:
            print(f"Spotify playback error: {e}")
            
            if "NO_ACTIVE_DEVICE" in str(e) or "Player command failed" in str(e):
                print("Device became inactive. Waiting for reconnection...")
                device_id = wait_for_spotify_device(spotify)
                if device_id:
                    # Try again with new device ID
                    spotify.start_playback(device_id=device_id, uris=[track_uri])
                    print(f"Updated Spotify with: {found_artist} - {found_title}")
                    return True, device_id
            return False, device_id
                
    except Exception as e:
        print(f"Spotify API error: {e}")
        return False, device_id
