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
  'leader_skills' : 'https://www.padherder.com/api/leader_skills/',
  'monsters'      : 'https://www.padherder.com/api/monsters/'
  #'https://www.padherder.com//user-api/profile/44243/'
}

# define some string dtypes outside so we can easily reuse them appropriately
dtype_as_name   = np.dtype('a128')
dtype_as_effect = np.dtype('a128')
dtype_aw_desc   = np.dtype('a96')
dtype_aw_name   = np.dtype('a40')
dtype_ls_effect = np.dtype('a96')
dtype_ls_name   = np.dtype('a40')
dtype_con_str   = np.dtype('a4')
dtype_mon_name  = np.dtype('a40')
dtype_mon_img   = np.dtype('a40')

# how long the monster data is without pdx_id and us_id
MON_LEN_EXTRA_IDS = 34
PDX_ID_INDEX = 10
US_ID_INDEX = 12  # it's supposed to be at 13 if it exists, meaning without it, it will appear after index 12

# dict of dtypes for the datas
dtypes = {
  'active_skills' : np.dtype([('min_cooldown',np.uint8),('effect',dtype_as_effect),('max_cooldown',np.uint8),('name',dtype_as_name)]),
  'awakenings'    : np.dtype([('desc',dtype_aw_desc),('id',np.uint8),('name',dtype_aw_name)]),
  # split the leader skill information itself from the multiplier info to reduce waste
  #   set 'data' to the index of the ls sublist, -1 if it doesn't exist
  'leader_skills' : np.dtype([('data',np.int8),('effect',dtype_ls_effect),('name',dtype_ls_name)]),
  # the 'data' key will be split into the HP/ATK/RCV multipliers and the constraints, which will be called
  #   the har and the con respectively. setting har to signed just in case gungho decides to be gungho sometime
  #   in the future. The constraints are further split into the string con_str which is either
  #   'type or 'elem', and con_num, which will be a -1 if it doesn't exist
  'leader_skills_sublist' : np.dtype([('har','(3,)int8'),('con_str',dtype_con_str),('con_num', '(3,)int8')]),
  'monsters'      : np.dtype([
                      ('element2',np.int8),         # can be null, careful!
                      ('awoken_skills',np.int8),    # similarly to the ls sublist, store in separate array
                      ('rcv_scale',np.float16),
                      ('id',np.uint16),
                      ('type3',np.uint8),           # can be null, careful!
                      ('type2',np.uint8),           # can be null, careful!
                      ('image40_href',dtype_mon_img),
                      ('xp_curve',np.uint32),
                      ('leader_skill',dtype_ls_name),
                      ('image40_size',np.uint16),
                      ('pdx_id',np.uint16),        # different for BAO collab
                      ('version',np.uint16),
                      ('atk_min',np.int16),
                      ('us_id',np.uint16),        # different for BAO collab
                      ('atk_max',np.int16),
                      ('jp_only',np.bool),
                      ('image60_size',np.uint16),
                      ('max_level',np.uint8),
                      ('image60_href',dtype_mon_img),
                      ('monster_points',np.uint16),
                      ('rcv_min',np.int16),
                      ('rcv_max',np.int16),         # note, satan
                      ('hp_max',np.uint16),
                      ('hp_scale',np.float16),
                      ('name',dtype_mon_name),
                      ('team_cost',np.uint8),
                      ('type',np.uint8),
                      ('hp_min',np.uint16),
                      ('name_jp',dtype_mon_name),
                      ('rarity',np.uint8),
                      ('active_skill',dtype_as_name),
                      ('feed_xp',np.float32),
                      ('element',np.uint8),
                      ('atk_scale',np.float16)
                    ]),
  'monsters_sublist' : np.dtype([('awoken_skills','(10,)int8')])
}

# dict to keep all game data in
dataDict = {}

# keep a global index around so leader skills with 'data' keys can use it to point to
#   their respective 'data' data in their sublist
sublist_index = 0

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
    _sublist = []
    # check if there are only two elements, ie: no 'data' key
    if(len(data) > 2):
      # all three keys present
      global sublist_index
      # create a local list, where the first element is a pointer to the index of its 'data' data
      #   in the sublist
      _data.append(sublist_index)
      # append the rest
      for d in data[1:]:
        _data.append(d)
      sublist_index += 1
      # the first three are the hp/atk/rcv multipliers, self-abbreviated to har, har har har
      #print(data[0])
      _sublist.append([data[0][0], data[0][1], data[0][2]])
      try:
        # next append the 4 character string, if it exists
        _sublist.append(data[0][3][0])
        # append whatever is left until we have 3 elements in con_num
        _sublist.append(data[0][3][1:])
        while(len(_sublist[-1]) < 3):
          _sublist[-1].append(-1)
      except IndexError:
        # no 4 character string, so this and the last 'data' is empty
        _sublist.append('-1')
        # and finally add a list of 3 nothings
        _sublist.append([-1, -1, -1])
      # return both lists
      return _data, _sublist
    else:
      # no 'data' key, ie: no ls multipliers
      # indicate -1 to signify no 'data' key
      _data.append(-1)
      for d in data:
        _data.append(d)
      # return only _data and [None], filter these results out for the sublistlist
      return _data, [None]

  def construct_data_mon(data):
    # remove the 'key' parts, keep only the 'value' part
    data = [encodeToUTF8(pair[-1]) for pair in data]
    # define some local lists to return at the end
    _index_mon_awoken_skill = 1
    _data = []
    # since the monster's ordered json data has some elements before
    #   the awoken skills, add these initially, excluding the awoken skills
    for i in range(0, _index_mon_awoken_skill):
      # convert all 'null' and Nones to -1s
      #   (because json.loads may have converted it to None automatically)
      d = data[i]
      if(d=='null' or d==None):
        _data.append(-1)
      else:
        _data.append(d)
    _sublist = []
    # check if the monster has any awoken skills
    if(len(data[_index_mon_awoken_skill]) > 0):
      # this monster has at least one awoken skill
      global sublist_index
      _data.append(sublist_index)
      # append the rest of the data, again excluding the list of awoken skills itself
      # also take care to check if pdx_id and us_id exists, [*indecipherable grumbling*]
      if(len(data) < MON_LEN_EXTRA_IDS):
        # this is not a BAO collab monster, stick in extra -1s at the extra ids indices
        for d in data[_index_mon_awoken_skill+1:PDX_ID_INDEX]:
          # convert all 'null' and Nones to -1s
          #   (because json.loads may have converted it to None automatically)
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
        _data.append(-1)
        for d in data[PDX_ID_INDEX:US_ID_INDEX]:
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
        _data.append(-1)
        for d in data[US_ID_INDEX:]:
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
      else:
        # BAO collab monsters had different pdx_id and us_ids
        #   handle these normally
        for d in data[_index_mon_awoken_skill+1:]:
          # convert all 'null' and Nones to -1s
          #   (because json.loads may have converted it to None automatically)
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
      sublist_index += 1
      # _data is finished, now to create the _sublist
      # append all the monster's awoken skills to _sublist
      for a in data[_index_mon_awoken_skill]:
        # convert all 'null' and Nones to -1s
        #   (because json.loads may have converted it to None automatically)
        if(a=='null' or a==None):
          _sublist.append(-1)
        else:
          _sublist.append(a)
      # pad the end of _sublist with -1s until there are 10,
      #   as 10? seems to be the maximum number of awakenings for now
      while(len(_sublist)<10):
        _sublist.append(-1)
      # return both lists
      return _data, [_sublist]
    else:
      # this monster has no awoken skills,
      # indicate -1 to signify no 'data' key
      _data.append(-1)
      # append the rest of the data, again excluding the list of awoken skills itself
      #   and again, we have to check to see if it's that goddamned BAO collab
      if(len(data) < MON_LEN_EXTRA_IDS):
        # this is not a BAO collab monster, stick in extra -1s at the extra ids indices
        for d in data[_index_mon_awoken_skill+1:PDX_ID_INDEX]:
          # convert all 'null' and Nones to -1s
          #   (because json.loads may have converted it to None automatically)
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
        _data.append(-1)
        for d in data[PDX_ID_INDEX:US_ID_INDEX]:
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
        _data.append(-1)
        for d in data[US_ID_INDEX:]:
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
      else:
        # BAO collab monsters had different pdx_id and us_ids
        #   handle these normally
        for d in data[_index_mon_awoken_skill+1:]:
          # convert all 'null' and Nones to -1s
          #   (because json.loads may have converted it to None automatically)
          if(d=='null' or d==None):
            _data.append(-1)
          else:
            _data.append(d)
      # return only _data and [None], filter these results out for the sublistlist
      return _data, [None]

  # dictionary to hold json objects
  global dataDict
  global sublist_index

  # now send them all simultaneously, and handle them asynchronously as they come in
  #   via the functionality of imap, which is a generator of response objects
  #   which themselves are string representations of json data
  for r in grequests.imap(unsentrequests):
    if(r.context == 'leader_skills'):
      # _newData will here be a list of lists, where for d in _newData, d[0] is the leader_skills data and
      #   d[1] is the sublist data. Note that the latter is the same length as the former, it's empty about half the time
      _newData = json.loads(r.text, object_pairs_hook=construct_data_ls)
      # create a new structured numpy array of the data, pass in the corresponding custom dtype
      _iterable = (tuple(d[0]) for d in _newData)
      # filter out None results
      _iterable_sublist = filterfalse(lambda d: d[0]==None, (tuple(d[1]) for d in _newData))
      dataDict[r.context] = np.fromiter(_iterable, dtype=dtypes[r.context], count=len(_newData))
      dataDict[r.context+'_sublist'] = np.fromiter(_iterable_sublist, dtype=dtypes[r.context+'_sublist'], count=sublist_index)
      # reset sublist_index after use so another data that may require can reuse it
      sublist_index = 0
    elif(r.context == 'monsters'):
      # similar to treatment of leader_skills above, but with the monster's awoken skills instead
      _newData = json.loads(r.text, object_pairs_hook=construct_data_mon)
      # create a new structured numpy array of the data, pass in the corresponding custom dtype
      _iterable = (tuple(d[0]) for d in _newData)
      # filter out None results
      _iterable_sublist = filterfalse(lambda d: d[0]==None, (tuple(d[1]) for d in _newData))
      #def _iterable_sublist(tuple
      dataDict[r.context] = np.fromiter(_iterable, dtype=dtypes[r.context], count=len(_newData))
      dataDict[r.context+'_sublist'] = np.fromiter(_iterable_sublist, dtype=dtypes[r.context+'_sublist'], count=sublist_index)
      # reset sublist_index after use so another data that may require can reuse it
      sublist_index = 0
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
