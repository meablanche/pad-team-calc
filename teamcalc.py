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
from itertools import filterfalse
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
  'awakenings'    : 'https://www.padherder.com/api/awakenings/',
  'leader_skills' : 'https://www.padherder.com/api/leader_skills/'
  #'monsters'      : 'https://www.padherder.com/api/monsters/'
  #'https://www.padherder.com//user-api/profile/44243/'
}

# dict of dtypes for the datas
dtypes = {
  'active_skills' : np.dtype([('min_cooldown',np.uint8),('effect',np.dtype('a128')),('max_cooldown',np.uint8),('name',np.dtype('a128'))]),
  'awakenings'    : np.dtype([('desc',np.dtype('a96')),('id',np.uint8),('name',np.dtype('a40'))]),
  # split the leader skill information itself from the multiplier info to reduce waste
  #   set 'data' to the index of the ls_multiplier list, -1 if it doesn't exist
  'leader_skills' : np.dtype([('data',np.int8),('effect',np.dtype('a96')),('name',np.dtype('a40'))]),
  # the 'data' key will be split into the HP/ATK/RCV multipliers and the constraints, which will be called
  #   the har and the con respectively. setting har to signed just in case gungho decides to be gungho sometime
  #   in the future. The constraints are further split into the string con_str which is either
  #   'type or 'elem', and con_num, which will be a -1 if it doesn't exist
  'ls_multiplier' : np.dtype([('har','(3,)int8'),('con_str',np.dtype('a4')),('con_num', '(3,)int8')])
}

# dict to keep all game data in
dataDict = {}

# keep a global index around so leader skills with 'data' keys can use it to point to
#   their respective 'data' data in the ls_multiplier list
ls_index = 0

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
  global dataDict
  # iterate over the files in the DATAPATH directory
  for f in os.listdir(DATAPATH):
    # only is it's a file though
    if(os.path.isfile(os.path.join(DATAPATH, f))):
      # check if the filename is already a key in the data dict
      if(f not in dataDict):
        # if not, then load the data into the dict
        dataDict[f] = np.load(os.path.join(DATAPATH, f))
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
    #print([encodeToUTF8(pair[-1]) for pair in data])
    return [encodeToUTF8(pair[-1]) for pair in data]

  def construct_data_ls(data):
    # remove the 'key' parts, keep only the 'value' parts
    data = [encodeToUTF8(pair[-1]) for pair in data]
    # define some local lists to return at the end
    _data = []
    _ls_mult = []
    # check if there are only two elements, ie: no 'data' key
    if(len(data) > 2):
      # all three keys present
      global ls_index
      # create a local list, where the first element is a pointer to the index of its 'data' data
      #   in the ls_multiplier list
      _data.append(ls_index)
      # append the rest
      for d in data[1:]:
        _data.append(d)
      ls_index += 1
      # the first three are the hp/atk/rcv multipliers, self-abbreviated to har, har har har
      #print(data[0])
      _ls_mult.append([data[0][0], data[0][1], data[0][2]])
      try:
        # next append the 4 character string, if it exists
        _ls_mult.append(data[0][3][0])
        # append whatever is left until we have 3 elements in con_num
        _ls_mult.append(data[0][3][1:])
        while(len(_ls_mult[-1]) < 3):
          _ls_mult[-1].append(-1)
      except IndexError:
        # no 4 character string, so this and the last 'data' is empty
        _ls_mult.append('-1')
        # and finally add a list of 3 nothings
        _ls_mult.append([-1, -1, -1])
      # return both
      return _data, _ls_mult
    else:
      # no 'data' key, ie: no ls multipliers
      # indicate -1 to signify no 'data' key
      _data.append(-1)
      for d in data:
        _data.append(d)
      # return only _data and [None], filter these results out for the ls_multiplier list
      return _data, [None]

  # dictionary to hold json objects
  global dataDict

  # now send them all simultaneously, and handle them asynchronously as they come in
  #   via the functionality of imap, which is a generator of response objects
  #   which themselves are string representations of json data
  for r in grequests.imap(unsentrequests):
    if(r.context == 'leader_skills'):
      # _newData will here be a list of lists, where for d in _newData, d[0] is the leader_skills data and
      #   d[1] is the ls_multiplier data. Note that the latter is the same length as the former, it's empty about half the time
      _newData = json.loads(r.text, object_pairs_hook=construct_data_ls)
      # create a new structured numpy array of the data, pass in the corresponding custom dtype
      _iterable = (tuple(d[0]) for d in _newData)
      # filter out None results
      _iterable_ls_mult = filterfalse(lambda d: d[0]==None, (tuple(d[1]) for d in _newData))
      dataDict[r.context] = np.fromiter(_iterable, dtype=dtypes[r.context], count=len(_newData))
      dataDict['ls_multiplier'] = np.fromiter(_iterable_ls_mult, dtype=dtypes['ls_multiplier'], count=ls_index)
    else:
      # convert/parse string representation to json format
      #   note: make sure to call the callback function with object_pair_hook so that order is preserved
      _newData = json.loads(r.text, object_pairs_hook=construct_data)
      # create a new structured numpy array of the data, pass in the corresponding custom dtype
      _iterable = (tuple(d) for d in _newData)
      dataDict[r.context] = np.fromiter(_iterable, dtype=dtypes[r.context], count=len(_newData))

  # saves our data to files
  def save():
    for key in dataDict:
      # save the numpy array, cache the data locally
      np.save(os.path.join(DATAPATH, key), dataDict[key])

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
