#!/usr/bin/env python3
"""1LIVE DIGGI Song Tracker - Fetches current playing song from 1LIVE DIGGI and updates Spotify."""

import requests
import time
from datetime import datetime

# Import shared Spotify utilities
from spotify_utils import (
    setup_spotify_client, 
    wait_for_spotify_device,
    find_and_play_track
)

# URL to fetch current playing song
DIGGI_URL = "https://www.wdr.de/radio/radiotext/streamtitle_1live_diggi.txt"

# Track last processed song to avoid duplicates
last_processed_song = None

def fetch_current_song():
    """Fetch the current song playing on 1LIVE DIGGI.
    
    Returns:
        dict: Song information with artist, title, and full_text or None if unavailable
    """
    try:
        response = requests.get(DIGGI_URL, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Get the song text and strip whitespace
        song_text = response.text.strip()
        
        # Check if this is a 1LIVE announcement (to be ignored)
        if '1LIVE' in song_text:
            return None
            
        # Parse artist and title
        # Usually format is "Artist - Title"
        if ' - ' in song_text:
            artist, title = song_text.split(' - ', 1)
            return {
                'artist': artist.strip(),
                'title': title.strip(),
                'full_text': song_text
            }
        else:
            # If no dash separator, treat whole string as title
            return {
                'artist': 'Unknown Artist',
                'title': song_text,
                'full_text': song_text
            }
            
    except Exception as e:
        print(f"Error fetching current song: {e}")
        return None

def main():
    """Main function to track 1LIVE DIGGI and update Spotify."""
    print("=== 1LIVE DIGGI to Spotify Integration ===")
    
    global last_processed_song
    
    # Setup Spotify client
    token = input("Enter your Spotify API token (leave blank for interactive authentication): ").strip()
    spotify = setup_spotify_client(token=token if token else None)
    
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
    
    print("\nMonitoring 1LIVE DIGGI for new songs...")
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
                        success, new_device_id = find_and_play_track(
                            spotify, 
                            song_info['artist'], 
                            song_info['title'], 
                            spotify_device_id
                        )
                        
                        if success:
                            last_processed_song = current_song
                            if new_device_id:
                                spotify_device_id = new_device_id
                
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
