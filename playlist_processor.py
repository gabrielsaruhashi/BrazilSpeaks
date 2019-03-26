from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import pprint
import time
from nltk.stem import RSLPStemmer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import os
import re 
import unidecode
from whosampled_scraper import *


def setEnvironmentVariables():
    os.environ['SPOTIPY_CLIENT_ID'] = 'c894a126681b4d97a8ccb0cd4a1e0de1'
    os.environ['SPOTIPY_CLIENT_SECRET'] = 'ebf185aaf47e40ab841246986fc7483d'
    os.environ['SPOTIPY_REDIRECT_URI'] = 'https://localhost:8080'
    print('Successfully set the environment variables')

def requestSongInfo(song_title, artist_name):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + '0RIKjAuJB6gohq-1r-w7FzG7W3FcgsL2ZwSRWjUdLLH0E31lUt6T8otW-JDL7VYC'}
    search_url = base_url + '/search'
    data = {'q': song_title + ' ' + artist_name}
    response = requests.get(search_url, data=data, headers=headers)

    return response

# Scrapes song based on URL and returns the preprocessed lyrics
# attemps two scraping methods (one based on ID and another based on class)
def scrapeSongURL(url):
    print("scraping {}".format(url))
    page = requests.get(url).content

    page = page.decode('utf8')
    page = page.encode("utf8",'ignore')

    html = BeautifulSoup(page, 'html.parser')
    lyrics = html.find('div', class_='lyrics')
    if lyrics:
        return preprocessLyrics(lyrics.get_text())

    else: # backup method scraping Vagalume
        lyrics = html.find('div', {"id": "lyrics"})
  
        if lyrics:
            print(preprocessLyrics(lyrics.get_text()))
            return preprocessLyrics(lyrics.get_text())

        # lyrics = preprocessLyrics(lyrics)
    # try: 
    # release_date = html.find('span', class_='metadata_unit-info metadata_unit-info--text_only').get_text()
    # print(release_date)
    print("none found")
    return ""


# Preprocessing of the Lyrics
def preprocessLyrics(lyrics):
    # stemmer=RSLPStemmer()
    sentence = lyrics.replace('\n', ' ')
    # lower lyrics
    sentence = sentence.lower()
    # remove all the annotations (e.g '[refrão 1] Bla bla')
    sentence = re.sub(r'[\(\[].*?[\)\]]', "", str(sentence))

    # remove special characters
    sentence = unidecode.unidecode(sentence)

    # get Portuguese stopwords
    file_stop = open("pt_stopwords.txt")
    body_stop = file_stop.read()
    stop = body_stop.split()

    token_words = word_tokenize(sentence)
    processed_sentence=[]
    
    for word in token_words:
        if word not in stop:
            processed_sentence.append(word)
            # stem_sentence.append(stemmer.stem(word))
            processed_sentence.append(" ")
    
    # remove all the annotations within [] and ()
    
    return "".join(processed_sentence)

def extractLyrics(song_title, artist_name):
    # Search for matches in request response
    response = requestSongInfo(song_title, artist_name)
    json_obj = response.json()
    remote_song_info = None
    

    for hit in json_obj['response']['hits']:
        if artist_name.lower() in hit['result']['primary_artist']['name'].lower():
            remote_song_info = hit
            break

    # Extract lyrics from URL if song was found
    if remote_song_info:
        song_url = remote_song_info['result']['url']
        lyrics = scrapeSongURL(song_url)

        return lyrics
    else:
        if song_title.lower() == "que as crianças cantem livres":
            url = "https://www.vagalume.com.br/taiguara/que-as-criancas-cantemlivres.html"
        else:
            url = "https://www.vagalume.com.br/{}/{}.html".format(artist_name, song_title)
            url = url.replace(" ", "-")
            url = unidecode.unidecode(url)
            url = url.lower()
        return scrapeSongURL(url)

def getSpotifySongFeatures(uri):
    song_features = sp.audio_features(uri)
    song_features = song_features[0]
    
    extra_fields = ["track_href", "uri", "analysis_url", "type"] 

    for field in extra_fields:
        song_features.pop(field)

    return song_features

def getSpotifyArtistInfo(artist_id):
    artist = {}
    
    info = sp.artist(artist_id)
   
    artist["artist_genres"] = info["genres"][0]
    artist["artist_name"] = info["name"]
    if info["images"]:
        artist["artist_photo"] = info["images"][0]["url"]
    else:
        artist["artist_photo"] = ""
    artist["artist_popularity"] = info["popularity"]
    artist["artist_sp_followers"] = info["followers"]["total"]

    return artist

def whoSampledExtraction(tracks):
    og_tracks = []
    for i in tracks:
        artists = [unidecode.unidecode(j['name']) for j in i['track']['artists']]
        track_name = i['track']['name'].replace('Instrumental', '')
        
        og_tracks.append({'artist' : artists, 'track': unidecode.unidecode(track_name)})
    
    pprint.pprint(og_tracks)
    new_playlist_tracks = get_whosampled_playlist(og_tracks)
    pprint.pprint(new_playlist_tracks)

def processSpotifyPlaylistCSV(uri, csv_filepath, song_class):
    
    start_time = time.time()

    username = uri.split(':')[2]
    playlist_id = uri.split(':')[4]

    # get the relevant playlist
    results = sp.user_playlist(username, playlist_id)

    tracks = results["tracks"]["items"]

    # TODO incorporating whosampled extraction
    whoSampledExtraction(tracks)

    # define main data frame that will store 
    df = pd.DataFrame()
    index = 0
    for obj in tracks:    
        track = obj["track"]
        song = {}
        
        # preprocessed song name
        song_name = re.split(r' -| \(', track["name"])[0]

        # song["artist"] = artist
        song["song_sp_uri"] = track["uri"]
        song["song_name"] = song_name
        song["song_isrc"] = track["external_ids"]["isrc"]
        song["song_popularity"] = track["popularity"]
        song_features = getSpotifySongFeatures(track["uri"])

        artist_info = getSpotifyArtistInfo(track["artists"][0]["id"])
        song["song_lyrics"] = extractLyrics(song["song_name"], artist_info["artist_name"])
        song["class"] = song_class

        # concatenating all dictionaries
        song = {**song, **song_features, **artist_info}   

        # TODO incorporate this somehow
        # song_analysis = sp.audio_analysis(track["uri"])
   
        df = pd.concat([df, pd.DataFrame(song, index=[index])])
        index += 1

    print("Scraping process took {} s. Now storing intermediate results for this class of music".format(time.time() - start_time))
    df.to_csv(csv_filepath)

    return df



# content =requests.get("https://api.vagalume.com.br/search.php?art=Taiguara&mus=Que+As+Criancas+Cantem+Livres&apikey=805ea7f0ceb5241b3fc80cbff1f33ab0",  headers={'User-Agent': 'Mozilla/5.0'})
# print(content.status_code)
PROTEST_URI = 'spotify:user:gabriel_saruhashi:playlist:4Tp4QcTk9rNikjmaDg5VxJ'
JOVEM_GUARDA_URI = 'spotify:user:gabriel_saruhashi:playlist:1JZoMCGiAKcXrgBzbKW931'
PROTEST_CLASSNAME = "Protest"
JOVEM_GUARDA_CLASSNAME = "Jovem Guarda"
setEnvironmentVariables()

client_credentials_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# create csv with data from spotify
protest_df = processSpotifyPlaylistCSV(PROTEST_URI, "protest.csv", "Protest")
jovem_guarda_df = processSpotifyPlaylistCSV(JOVEM_GUARDA_URI, "jovem_guarda.csv", "Jovem Guarda")

# store final output
res_df = pd.concat([protest_df, jovem_guarda_df])
res_df.to_csv("brz_dictatorship.csv")
target_df = res_df[['class']].copy()
target_df.to_csv("brz_dictatorship_target.csv")

