# Sonos Scrobble

A collection of Python tools to track music playback and synchronize with Spotify. This project includes several components:

1. **Sonos Tracker** - Monitors songs playing on your Sonos devices and can update Spotify playback 
2. **1LIVE DIGGI Integration** - Tracks currently playing songs on 1LIVE DIGGI radio and plays them on Spotify
3. **BigFM Integration** - Tracks currently playing songs on BigFM radio and plays them on Spotify

## Features

- Track songs played on your Sonos system
- Listen to what's playing on radio stations (1LIVE DIGGI, BigFM) and automatically play those songs on Spotify
- Automatically authenticate with Spotify API
- Save and reuse Spotify credentials
- Maintain playback position when transferring songs

## Requirements

- Python 3.6 or higher
- Sonos system (for the Sonos tracker)
- Spotify Premium account
- Spotify Developer API credentials

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd sonos-scrobble
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a Spotify application at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
   - Set the redirect URI to: `http://localhost:8888/callback` or `http://127.0.0.1:8888/callback`
   - Note your Client ID and Client Secret

## Usage

### Sonos Tracker

To track songs playing on your Sonos system:
