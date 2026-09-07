import requests
import json

#import pprint

from dataClasses import *
from config import *

REQUEST_TIMEOUT = (2, 5)


def _getJson(url):
  response = requests.get(url=url, timeout=REQUEST_TIMEOUT)
  response.raise_for_status()
  return response.json()

#----------------------------------------------------------------

def getScheduledGigId():
  gigId = -1
  data = _getJson(API_URL + '/currentgig')
  #pprint.pprint(data)
  if len(data) > 0:
    gigId = data['id']
    #pprint.pprint(gigId)
  return gigId
#----------------------------------------------------------------

def getGig(id):
  # print('----------------------------------------------------')
  URL = API_URL + "/gig/"+str(id)
  #pprint.pprint(URL)
  # PARAMS = {'id':id} 
  # response = requests.get(url = URL, params = PARAMS) 
  data = _getJson(URL)
  #print('----------------------------------------------------')
  #pprint.pprint(data)
  #print('----------------------------------------------------')
  if len(data) > 0:
    return data
  else:  
    #print(' Error. no GIG selected !!!!!!!!!-------------------')
    return {}

#----------------------------------------------------------------

def getGigs():
  URL = API_URL + '/all/gig'
  return _getJson(URL)

#----------------------------------------------------------------

def getPresets():
  URL = API_URL + '/all/preset'
  data = _getJson(URL)
  # pprint.pprint(data)
  return data
#----------------------------------------------------------------

def getInstruments():
  URL = API_URL + '/all/instrument'
  data = _getJson(URL)
  # pprint.pprint(data)
  return data
#----------------------------------------------------------------

def getInstrumentBanks():
  URL = API_URL + '/all/instrumentbank'
  data = _getJson(URL)
  # pprint.pprint(data)
  return data

#----------------------------------------------------------------

def getSong(id):
  data = _getJson(API_URL +  '/song/' + str(id))
  #for key, value in data.items():
  #  print (key, value)
  #pprint.pprint(data)
  return data

def readSongFromJson(id):
  fileName = f"{PATH_TO_SONG_FOLDER}{id}.json"
  #print(fileName)
  with open(fileName) as jsonFile:
    data = json.load(jsonFile)
    #print(data)
    return data
