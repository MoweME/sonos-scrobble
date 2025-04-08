#!/usr/bin/env python3
"""BigFM Song Tracker - Fetches currently playing songs from BigFM and updates Spotify."""

import requests
import time
import os
from datetime import datetime, timedelta
import urllib.parse

# Import shared Spotify utilities
from spotify_utils import (
    setup_spotify_client, 
    wait_for_spotify_device,
    find_and_play_track
)

# Track last processed song to avoid duplicates
last_processed_song = None

def generate_bigfm_url():
    """Generate BigFM API URL with current time range for the past 5 minutes.
    
    Returns:
        str: URL for BigFM API request
    """
    now = datetime.now()
    past = now - timedelta(minutes=5)
    
    # Format times in ISO 8601 format with URL encoding
    end_time = urllib.parse.quote_plus(now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+01:00')
    start_time = urllib.parse.quote_plus(past.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '+01:00')
    
    return f"https://asw.api.iris.radiorepo.io/v2/playlist/search.json?station=3&start={start_time}&end={end_time}"

def clean_string(text):
    """Remove radio station indicators like '*NEU*' from strings.
    
    Args:
        text (str): The text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return text
    # Remove *NEU* tag that BigFM adds to new songs
    return text.replace('*NEU*', '').strip()

def fetch_current_song():
    """Fetch the current song playing on BigFM.
    
    Returns:
        dict: Song information with artist, title, and full_text or None if unavailable
    """
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
        
        # Clean strings by removing *NEU* tag
        title = clean_string(title)
        artist = clean_string(artist)
            
        return {
            'artist': artist,
            'title': title,
            'full_text': f"{artist} - {title}"
        }
            
    except Exception as e:
        print(f"Error fetching current song: {e}")
        return None

def main():
    """Main function to track BigFM and update Spotify."""
    print("=== BigFM to Spotify Integration ===")
    
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
