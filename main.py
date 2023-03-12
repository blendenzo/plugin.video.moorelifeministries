# -*- coding: utf-8 -*-
import sys
import re
from urllib.parse import urlencode
from urllib.parse import parse_qsl
import xbmcgui
import xbmcplugin
import requests
import xml.etree.ElementTree as ET
from titlecase import titlecase

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

# MLM urls
url_root = "https://www.flcbranson.org"
url_channel = ""

def get_text(element, match):
    result = element.find(match)
    if result != None:
        text = result.text
        if text == None:
            text = ""
    else:
        text = ""
    return text

def get_channel(channel):
    base_url = "https://www.flcbranson.org"
    channel_url = "https://www.flcbranson.org/php/mlmMediaChannelCollectionInfo.php"
    query = {"contentType": "TEXT/XML",
             "site": "fli",
             "channelID": channel,
             "languageID": "EN",
             "categoryID": "0"}

    page = requests.post(channel_url, data=query)

    tree = ET.fromstring(page.content)

    entries = tree.findall('.//entry')

    listings = []
    for entry in entries:
        listing = {'collection': get_text(entry, './collectionName'),
                   'event': get_text(entry, './eventName'),
                   'description': re.sub('</*[a-zA-Z]>', '', re.sub('((</p><p>)|(<br />)|(<p.*?>))', '\n', get_text(entry, './collectionDesc'))),
                   'author': get_text(entry, './authorName'),
                   'location': get_text(entry, './locationName'),
                   'date': get_text(entry, './broadcastDate'),
                   'image': base_url + get_text(entry, './collectionImage')[2:],
                   'channelID': get_text(entry, './channelID'),
                   'collectionID': get_text(entry, './collectionID'),
                   'languageID': get_text(entry, './languageID'),
                   'type':'collection',
                   'mediatype':'video'}
        if listing['event'] != "":
            listing['name'] = titlecase(listing['event'] + ' - ' + listing['collection'])
        else:
            listing['name'] = titlecase(listing['collection'])
        listings.append(listing)

    return listings


def get_entries(url, query):

    url_root = "https://www.flcbranson.org"

    page = requests.post(url, data=query)

    tree = ET.fromstring(page.content)

    entries = tree.findall('.//entry')

    listings = []
    for entry in entries:
        listing = {'name': titlecase(get_text(entry, './eventName')),
                   'image': url_root + '/img/' + get_text(entry, './collectionImage'),
                   'url': "https://flcmedia.nyc3.cdn.digitaloceanspaces.com" + get_text(entry, './collectionPath')}

        listings.append(listing)

    return listings


def get_collection(channelID, collectionID):
    base_url = "https://flcbranson.org"
    media_url = "https://flcmedia.nyc3.digitaloceanspaces.com"

    if collectionID != 'Z':
        collection_url = base_url + "/php/mlmMediaChannelCollectionContentInfo.php"
        query = {"contentType": "TEXT/XML",
                 "site": "mlm",
                 "channelID": channelID,
                 "languageID": "EN",
                 "collectionID": collectionID}
    else:
        collection_url = base_url + "/php/mlmMediaChannelContentInfo.php"
        query = {"contentType": "TEXT/XML",
                 "site": "mlm",
                 "channelID": channelID,
                 "languageID": "EN"}

    page = requests.post(collection_url, data=query)

    tree = ET.fromstring(page.content)

    entries = tree.findall('.//entry')

    listings = []
    for entry in entries:
        listing = {'name': get_text(entry, './contentPart'),
                   'date': get_text(entry, './broadcastDate'),
                   'image': base_url + '/img/' + get_text(entry, './collectionImage')}

        if collectionID != 'Z':
            listing['name'] = get_text(entry, './contentPart')
        else:
            listing['name'] = get_text(entry, './collectionName') + " - " + get_text(entry, './contentPart')

        # Get the highest quality media
        if get_text(entry, './mp4HDPathName') != "":
            listing['url'] = media_url + get_text(entry, './mp4HDPathName')
            listing['mediatype'] = 'video'
        elif get_text(entry, './mp4SDPathName') != "":
            listing['url'] = media_url + get_text(entry, './mp4SDPathName')
            listing['mediatype'] = 'video'
        else:
            listing['url'] = media_url + get_text(entry, './mp3PathName')
            listing['mediatype'] = 'music'

        listings.append(listing)

    return listings


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :type kwargs: dict
    :return: plugin call URL
    :rtype: str
    """
    return '{0}?{1}'.format(_url, urlencode(kwargs))


def get_videos(category):
    videos = []
    if category == 'Live Service Rebroadcasts':
        videos = get_entries("https://flcbranson.org/php/mlmMediaRebroadcastCollectionInfo.php",
                             {'contentType':'TEXT/XML','site':'mlm'})

    return videos


def list_folder(item):
    list_item = xbmcgui.ListItem(label=item['name'])
    list_item.setArt({'image': item['image'],
                      'icon': item['image']})
    list_item.setInfo(item['mediatype'], {'title': item['name'],
                                'mediatype': item['mediatype'],
                                'plot': item['description']})
    if item['type'] == 'category':
        url = get_url(action='listing', category=item['name'])
    elif item['type'] == 'channel':
        url = get_url(action='channel', channelName=item['name'], channelID=item['channelID'])
    elif item['type'] == 'collection':
        url = get_url(action='collection', collectionID=item['collectionID'], collectionName=item['collection'], channelID=item['channelID'])
    is_folder = True
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

def list_playable(item):
    list_item = xbmcgui.ListItem(label=item['name'])
    list_item.setInfo('video', {'title': item['name'],
                                'mediatype': item['mediatype']})
    list_item.setArt({'image': item['image'], 'icon': item['image'], 'fanart': item['image']})
    list_item.setProperty('IsPlayable', 'true')
    url = get_url(action='play', video=item['url'])
    is_folder = False
    xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

def list_categories():
    xbmcplugin.setPluginCategory(_handle, 'Media')
    xbmcplugin.setContent(_handle, 'videos')
    # Get video categories
    categories = [{'name':'Watch Live',
                   'image':'https://flcbranson.org/img/flcb-choirandcamera-1440x360.jpg',
                   'url':'http://wowzaprod126-i.akamaihd.net/hls/live/531553/89e5e873/playlist.m3u8',
                   'mediatype':'video',
                   'type':'playable'},
                  {'name':'Live Service Rebroadcasts',
                   'description':'Watch full rebroadcasts of the most recent Sunday and Friday services and recent special events.',
                   'image':'https://www.flcbranson.org/img/flcs-bromooreinfrontofstagemm13-1440x360.jpg',
                   'icon':'',
                   'url':'https://www.flcbranson.org/php/mlmMediaRebroadcastCollectionInfo.php?contentType=TEXT/XML&site=fli',
                   'mediatype':'video',
                   'type':'category'},
                  {'name':'Faith School',
                   'description':'Faith School',
                   'image':'',
                   'mediatype':'video',
                   'type':'channel',
                   'channelID':'12'},
                  {'name':'Series Listing',
                   'description':'A listing of every series',
                   'image':'',
                   'mediatype':'video',
                   'type':'channel',
                   'channelID':'1'},
                  {'name':'Music',
                   'description':'Listen to music',
                   'image':'',
                   'mediatype':'video',
                   'type':'channel',
                   'channelID':'2'},
                  {'name':'TV Broadcast',
                   'description':'Watch the television broadcast',
                   'image':'',
                   'mediatype':'video',
                   'type':'collection',
                   'channelID':'3',
                   'collectionID':'Z',
                   'collection':'TV Broadcast'},
                  {'name':'Radio Broadcast',
                   'description':'Listen to the radio broadcast',
                   'image':'',
                   'mediatype':'video',
                   'type':'channel',
                   'channelID':'4'}]
    # Iterate through categories
    for category in categories:
        if category['type'] == 'category' or category['type'] == 'collection' or category['type'] == 'channel':
            list_folder(category)
        elif category['type'] == 'playable':
            list_playable(category)
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    #xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

def list_channel(channelName, channelID):
    xbmcplugin.setPluginCategory(_handle, channelName)
    xbmcplugin.setContent(_handle, 'videos')

    channel = get_channel(channelID)
    for collection in channel:
        list_folder(collection)

    xbmcplugin.endOfDirectory(_handle)


def list_collection(channelID, collectionID, collectionName):
    xbmcplugin.setPluginCategory(_handle, collectionName)
    xbmcplugin.setContent(_handle, 'videos')

    collection = get_collection(channelID, collectionID)
    for item in collection:
        list_playable(item)

    xbmcplugin.endOfDirectory(_handle)

def list_videos(category):
    xbmcplugin.setPluginCategory(_handle, category)
    xbmcplugin.setContent(_handle, 'videos')
    # Get the list of videos in the category.
    videos = get_videos(category)
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=video['name'])
        list_item.setInfo('video', {'title': video['name'],
                                    'mediatype': 'video'})
        list_item.setArt({'image': video['image'], 'icon': video['image'], 'fanart': video['image']})
        list_item.setProperty('IsPlayable', 'true')
        url = get_url(action='play', video=video['url'])
        is_folder = False
        xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(_handle)


def play_video(path):
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    print(params)
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'channel':
            list_channel(params['channelName'], params['channelID'])
        elif params['action'] == 'collection':
            list_collection(params['channelID'], params['collectionID'], params['collectionName'])
        elif params['action'] == 'listing':
            list_videos(params['category'])
        elif params['action'] == 'play':
            play_video(params['video'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
