# Sonos Scrobble

A collection of Python tools to track music playback and synchronize with Spotify. This project includes several components:

1. **Sonos Tracker** - Monitors songs playing on your Sonos devices and can update Spotify playback 
2. **1LIVE DIGGI Integration** - Tracks currently playing songs on 1LIVE DIGGI radio and plays them on Spotify
3. **BigFM Integration** - Tracks currently playing songs on BigFM radio and plays them on Spotify
4. **Spotify Utilities** - Shared module for Spotify authentication and playback

## Features

- Track songs played on your Sonos system
- Listen to what's playing on radio stations (1LIVE DIGGI, BigFM) and automatically play those songs on Spotify
- Automatically authenticate with Spotify API
- Save and reuse Spotify credentials
- Maintain playback position when transferring songs
- Shared code architecture for easier maintenance and consistency

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

## Architecture

The project is structured with a shared module for Spotify functionality, improving code reuse and maintainability:

- `spotify_utils.py` - Contains shared Spotify authentication and playback functions
- `run.py` - Sonos tracking script
- `1liveDIGGI.py` - 1LIVE DIGGI integration script
- `bigfm.py` - BigFM integration script

All scripts use the shared Spotify utilities for consistent authentication and playback behavior.

## Usage

### Sonos Tracker

To track songs playing on your Sonos system:

```
python run.py
```

This script will:
- Discover Sonos devices on your network.
- Prompt you to select a device.
- Monitor the selected device, displaying the current track info.
- Optionally update the song on Spotify if integration is enabled.

### 1LIVE DIGGI Integration

Run this script to monitor the 1LIVE DIGGI radio stream and update Spotify with the currently playing song:

```
python 1liveDIGGI.py
```

It will:
- Connect to Spotify via your saved or interactive credentials.
- Fetch the current song from 1LIVE DIGGI.
- Search for the track on Spotify and start playback.

### BigFM Integration

To monitor BigFM radio and update Spotify accordingly, execute:

```
python bigfm.py
```

It will:
- Generate a query using the current time to fetch the latest song from BigFM's API.
- Search Spotify for this song and update playback on an active device.

## Spotify Authentication

The first time you run any script with Spotify integration, you will be prompted to enter your Spotify Client ID and Client Secret. You'll need to authenticate via your browser. Your credentials will be saved in `spotify_credentials.json` for future use.

To obtain your Spotify credentials:
1. Create a Spotify application at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
2. Set the redirect URI to: `http://localhost:8888/callback` or `http://127.0.0.1:8888/callback`
3. Copy both your Client ID and Client Secret for use in the application

## Troubleshooting

- **No Sonos devices found:** Ensure your computer is on the same network as your Sonos system.
- **Spotify authentication issues:** Verify that your Spotify app's Redirect URI is set to one of `http://localhost:8888/callback` or `http://127.0.0.1:8888/callback`.
- **Song not found on Spotify:** Some tracks may have differing metadata or might not be available on Spotify.
- **Module import errors:** Make sure all files are in the same directory.

## License

This project is open-source.

## Contributing

Contributions are welcome! Please submit pull requests or open issues for any bugs or feature requests.
