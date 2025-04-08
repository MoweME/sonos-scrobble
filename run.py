#!/usr/bin/env python3
"""Sonos Song Tracker - Tracks songs playing on a selected Sonos device."""

import soco
import time
from datetime import datetime

# Import shared Spotify utilities
from spotify_utils import (
    setup_spotify_client, 
    wait_for_spotify_device,
    find_and_play_track
)

# Track origin to prevent transfer loops
LAST_TRANSFERRED_URI = None
TRANSFER_COOLDOWN = 0  # Cooldown timer to prevent immediate transfers

def discover_sonos_devices():
    """Discover Sonos devices on the network.
    
    Returns:
        list: List of discovered Sonos devices
    """
    print("Discovering Sonos devices...")
    return list(soco.discover())

def select_device(devices):
    """Allow user to select a Sonos device.
    
    Args:
        devices (list): List of Sonos devices
        
    Returns:
        SoCo: Selected Sonos device
    """
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
    """Convert milliseconds to HH:MM:SS format.
    
    Args:
        ms (int): Milliseconds
        
    Returns:
        str: Formatted time string
    """
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def update_spotify_with_sonos_track(spotify, track_info, device_id=None, device_name=None):
    """Update Spotify with the current Sonos track.
    
    Args:
        spotify (spotipy.Spotify): Spotify client
        track_info (dict): Track information
        device_id (str, optional): Device ID to play on. Defaults to None.
        device_name (str, optional): Name of the device. Defaults to None.
        
    Returns:
        bool: Whether update was successful
    """
    global LAST_TRANSFERRED_URI
    
    if not spotify or not track_info.get('title'):
        return False
    
    success, new_device_id = find_and_play_track(
        spotify, 
        track_info['artist'], 
        track_info['title'], 
        device_id
    )
    
    if success and new_device_id:
        # If there's a position to seek to
        if 'position' in track_info and track_info['position']:
            current_position = 0
            time_parts = track_info['position'].split(':')
            if len(time_parts) == 3:
                hours, minutes, seconds = map(int, time_parts)
                current_position = (hours * 3600 + minutes * 60 + seconds) * 1000
            elif len(time_parts) == 2:
                minutes, seconds = map(int, time_parts)
                current_position = (minutes * 60 + seconds) * 1000
            
            if current_position > 0:
                try:
                    spotify.seek_track(current_position, device_id=new_device_id)
                    print(f"Seeked to position: {track_info['position']}")
                except Exception as e:
                    print(f"Error seeking position: {e}")
    
    return success

def track_songs(device, spotify=None):
    """Track songs on the selected Sonos device.
    
    Args:
        device (SoCo): Sonos device to track
        spotify (spotipy.Spotify, optional): Spotify client. Defaults to None.
    """
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
            try:
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
            except Exception as e:
                print(f"Error getting track info: {e}")
                
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