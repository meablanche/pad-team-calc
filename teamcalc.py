#!usr/bin/env python
# -*- coding: utf-8 -*-

# TEAM CALCULATOR FOR PAD
# -------------------------------------
# Uses data from padherder to fetch a user teams and then displays ui to calculate team damage output



# LIBRARIES
# -------------------------------------
import codecs
from collections import OrderedDict
import grequests
import requests
import json
import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
import numpy as np
import os.path
import sys


# CONSTANTS
# -------------------------------------
# path to the hidden data folder
DATAPATH = './.data/'
NPYEXT = '.npy'

# dict of urls to request jsons from
urls = {
  'active_skills' : 'https://www.padherder.com/api/active_skills/',
  'awakenings'    : 'https://www.padherder.com/api/awakenings/'
  #'https://www.padherder.com//user-api/profile/44243/'
}

# dict of dtypes for the datas
dtypes = {
  'active_skills' : np.dtype([('min_cooldown',np.uint8),('effect',np.dtype('a128')),('max_cooldown',np.uint8),('name',np.dtype('a128'))]),
  'awakenings'    : np.dtype([('desc',np.dtype('a96')),('id',np.uint8),('name',np.dtype('a40'))])
}

# dict to keep all game data in
data = {}

# CHARSET ENCODING
# -------------------------------------
# ensure that any text is encoded with unicode properly or at least replaced with moon runes
if sys.stdout.encoding != 'UTF-8':
  sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# because there are japanese characters here and there, we must encode them into bytes
#   form, all the strings, to preserve integrity of many things
def encodeToUTF8(arg):
  try:
    # encode ascii string to a delimited UTF-8 byte string
    return arg.encode('utf8')
  except AttributeError:
    # not a string
    return arg



# JSON DATA LOADER AND REQUESTER
# -------------------------------------
# Load locally saved data into the program
def LoadJSONFromDisk():
  global data
  # iterate over the files in the DATAPATH directory
  for f in os.listdir(DATAPATH):
    # only is it's a file though
    if(os.path.isfile(os.path.join(DATAPATH, f))):
      # check if the filename is already a key in the data dict
      if(f not in data):
        # if not, then load the data into the dict
        data[f] = np.load(os.path.join(DATAPATH, f))
  return True

# all the pad related data in padherder is available in the form of json files,
#   we will first need to save these somewhere locally to avoid having to
#   re-download the data everytime
# we will be using the grequests library by kennethreitz
def RequestJSONAndSaveToDisk():
  # define a callback function to set some user-defined meta-data
  #   in this case, the filename for the jsons we get from the urls
  def set_context(context):
    def hook(resp, **data):
      resp.context = context
      return resp
    return hook

  # construct a list of unsent requests
  unsentrequests = []
  for key in urls:
    # only send a request for the json file if we don't already have a locally cached one
    if(os.path.isfile(os.path.join(DATAPATH, key+NPYEXT)) == False):
      unsentrequests.append(grequests.get(urls[key], callback=set_context(key)))


  # strip away what we don't need from the response data, namely the 'names'/'keys'
  def construct_data(data):
    # the data parameter here will be passed in an (ordered) list
    # return a list of only the 'values', not the 'keys', as we know those already
    #   so return only the latter half
    return [encodeToUTF8(pair[-1]) for pair in data]

  # dictionary to hold json objects
  global data

  # now send them all simultaneously, and handle them asynchronously as they come in
  #   via the functionality of imap, which is a generator of response objects
  #   which themselves are string representations of json data
  for r in grequests.imap(unsentrequests):
    # convert/parse string representation to json format
    #   note: make sure to call the callback function with object_pair_hook so that order is preserved
    newData = json.loads(r.text, object_pairs_hook=construct_data)
    # create a new structured numpy array of the data, pass in the corresponding custom dtype
    _iterable = (tuple(d) for d in newData)
    data[r.context] = np.fromiter(_iterable, dtype=dtypes[r.context], count=len(newData))

  # saves our data to files
  def save():
    for key in data:
      # save the numpy array, cache the data locally
      np.save(os.path.join(DATAPATH, key), data[key])

  save()
    
  return True


# ----------------------
# KIVY GUI
# ----------------------

# define the class rules and load using Builder
Builder.load_string('''
<BaseLayout>
  canvas.before:
    Color:
      rgba: 0.4, 0.1, 0.1, 1
    Rectangle:
      # self refers to the widget itself, in this case the BoxLayout widget
      pos: self.pos
      size: self.size

  # the base layout will divide the app space into the general final chunks
  BoxLayout:
    orientation: 'horizontal'
    spacing: 10
    # add some temporary subwidget spaces
    Button:
      text: '1'
      size_hint: 0.5, 1
    Button:
      text: '2'
      size_hint: 0.5, 1

<RootWidget>
  # add the base layout class
  BaseLayout:
    # pass
''')

# define class of the root widget, which all other widgets are children of
# keep empty as a sort of blank slate to slap everything else on
class RootWidget(BoxLayout):
  pass

# define the lowest, overall foundational layout as a BoxLayout. This will
#   determine the general layout of the whole app aesthetic
class BaseLayout(BoxLayout):
  pass

# define the base App class, based on kivy.app
class BaseApp(App):
  # initialize and return the root widget of the app
  def build(self):
    # return the root widget after we have finished initializing it
    return RootWidget()



# --- run ---

RequestJSONAndSaveToDisk()
LoadJSONFromDisk()

# start the app
if __name__ == '__main__':
  BaseApp().run()
