import pandas as pd
import spotipy
from playlist_processor import * 
from spotipy.oauth2 import SpotifyClientCredentials



URI = 'spotify:user:gabriel_saruhashi:playlist:6VQc4YkZ7OcRHKf2gNDgDg'
PROTEST_CLASSNAME = "Protest"


# create csv with data from spotify
print("here")
protest_df = processSpotifyPlaylistCSV(URI, "whosampled_data.csv", "Protest")
