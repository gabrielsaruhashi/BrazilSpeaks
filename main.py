from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import pprint


def request_song_info(song_title, artist_name):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + '0RIKjAuJB6gohq-1r-w7FzG7W3FcgsL2ZwSRWjUdLLH0E31lUt6T8otW-JDL7VYC'}
    search_url = base_url + '/search'
    data = {'q': song_title + ' ' + artist_name}
    response = requests.get(search_url, data=data, headers=headers)

    return response

def scrap_song_url(url):
    page = requests.get(url)
    html = BeautifulSoup(page.text, 'html.parser')
    lyrics = html.find('div', class_='lyrics').get_text()

    return lyrics

def extractLyrics(song_title, artist_name):
    # Search for matches in request response
    response = request_song_info(song_title, artist_name)
    json = response.json()
    remote_song_info = None

    for hit in json['response']['hits']:
        if artist_name.lower() in hit['result']['primary_artist']['name'].lower():
            remote_song_info = hit
            break

    # Extract lyrics from URL if song was found
    if remote_song_info:
        song_url = remote_song_info['result']['url']
        lyrics = scrap_song_url(song_url)
        return lyrics
    else:
        print("Could not find lyrics for given artist and song title")
        return ""

def getSpotifySongFeatures(uri):
    song_features = sp.audio_features(uri)
    song_features = song_features[0]
    
    extra_fields = ["track_href", "uri", "analysis_url", "type"] 

    for field in extra_fields:
        song_features.pop(field)

    return song_features

client_credentials_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

uri = 'spotify:user:gabriel_saruhashi:playlist:4Tp4QcTk9rNikjmaDg5VxJ'
username = uri.split(':')[2]
playlist_id = uri.split(':')[4]

# get the relevant playlist
results = sp.user_playlist(username, playlist_id)

tracks = results["tracks"]["items"]

# define main data frame that will store 
df = pd.DataFrame()

# print(json.dumps(tracks, indent=4))
for obj in tracks:    
    track = obj["track"]
    song = {}
    
    
    artists = []
    # get artists
    for artist in track["artists"]:
        name = artist["name"]
        artists.append(name)
    
    song["artists"] = artists
    song["uri"] = track["uri"]
    song["name"] = track["name"]
    song["popularity"] = track["popularity"]
    song["isrc"] = track["external_ids"]["isrc"]
    song["lyrics"] = extractLyrics(song["name"], artists[0])
    song_features = getSpotifySongFeatures(track["uri"])

    # concatenating both dictionaries
    song = {**song, **song_features}   
    # song_analysis = sp.audio_analysis(song["uri"])
    # pprint.pprint(song_analysis)

    df = pd.concat([df, pd.DataFrame(song)])


df.to_csv("brz_dictatorship.csv")    
