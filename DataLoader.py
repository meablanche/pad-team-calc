#!usr/bin/env python

# DATA LOADER
# -------------------------------------
# class for loading data from padherder

# LIBRARIES
# -------------------------------------
from itertools import filterfalse
import json
import grequests
import numpy as np
import os.path

# USER LIBRARIES
# -------------------------------------
import Constants as c


# CHARSET ENCODING
# -------------------------------------
# because there are japanese characters here and there, we must encode them into bytes
#   form, all the strings, to preserve integrity of stuffs
def encodeToUTF8(arg):
  try:
    # encode ascii string to a delimited UTF-8 byte string
    return arg.encode('utf8')
  except AttributeError:
    # not a string
    return arg


class DataLoader():
  def __init__(self):
    # dict to keep all game data in
    self.dataDict = {}

    # dict to keep user data in
    self.userDataDict = {}

    # keep a global index around so leader skills with 'data' keys can use it to point to
    #   their respective 'data' data in their sublist
    self.sublist_index = 0

  def LoadGameData(self):
    self.RequestJSONAndSaveToDisk()
    self.LoadJSONFromDisk()

  # JSON DATA LOADER AND REQUESTER
  # -------------------------------------
  # Load locally saved data into the program
  def LoadJSONFromDisk(self):
    # iterate over the files in the DATAPATH directory
    for f in os.listdir(c.DATAPATH):
      # only is it's a file though
      if(os.path.isfile(os.path.join(c.DATAPATH, f))):
        # check if the filename is already a key in the data dict
        if(f not in self.dataDict):
          # if not, then load the data into the dict
          self.dataDict[f] = np.load(os.path.join(c.DATAPATH, f))
    return True

  # all the pad related data in padherder is available in the form of json files,
  #   we will first need to save these somewhere locally to avoid having to
  #   re-download the data everytime
  # we will be using the grequests library by kennethreitz
  def RequestJSONAndSaveToDisk(self):
    # define a callback function to set some user-defined meta-data
    #   in this case, the filename for the jsons we get from the urls
    def set_context(context):
      def hook(resp, **data):
        resp.context = context
        return resp
      return hook

    # construct a list of unsent requests
    unsentrequests = []
    for key in c.URLS:
      # only send a request for the json file if we don't already have a locally cached one
      if(os.path.isfile(os.path.join(c.DATAPATH, key+c.NPYEXT)) == False):
        unsentrequests.append(grequests.get(c.URLS[key], callback=set_context(key)))


    # strip away what we don't need from the response data, namely the 'names'/'keys'
    def construct_data(data):
      # the data parameter here will be passed in an (ordered) list
      # return a list of only the 'values', not the 'keys', as we know those already
      #   so return only the latter half
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
        # create a local list, where the first element is a pointer to the index of its 'data' data
        #   in the sublist
        _data.append(self.sublist_index)
        # append the rest
        for d in data[1:]:
          _data.append(d)
        self.sublist_index += 1
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
        _data.append(self.sublist_index)
        # append the rest of the data, again excluding the list of awoken skills itself
        # also take care to check if pdx_id and us_id exists, [*indecipherable grumbling*]
        if(len(data) < c.MON_LEN_EXTRA_IDS):
          # this is not a BAO collab monster, stick in extra -1s at the extra ids indices
          for d in data[_index_mon_awoken_skill+1:c.PDX_ID_INDEX]:
            # convert all 'null' and Nones to -1s
            #   (because json.loads may have converted it to None automatically)
            if(d=='null' or d==None):
              _data.append(-1)
            else:
              _data.append(d)
          _data.append(-1)
          for d in data[c.PDX_ID_INDEX:c.US_ID_INDEX]:
            if(d=='null' or d==None):
              _data.append(-1)
            else:
              _data.append(d)
          _data.append(-1)
          for d in data[c.US_ID_INDEX:]:
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
        self.sublist_index += 1
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
        if(len(data) < c.MON_LEN_EXTRA_IDS):
          # this is not a BAO collab monster, stick in extra -1s at the extra ids indices
          for d in data[_index_mon_awoken_skill+1:c.PDX_ID_INDEX]:
            # convert all 'null' and Nones to -1s
            #   (because json.loads may have converted it to None automatically)
            if(d=='null' or d==None):
              _data.append(-1)
            else:
              _data.append(d)
          _data.append(-1)
          for d in data[c.PDX_ID_INDEX:c.US_ID_INDEX]:
            if(d=='null' or d==None):
              _data.append(-1)
            else:
              _data.append(d)
          _data.append(-1)
          for d in data[c.US_ID_INDEX:]:
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
        self.dataDict[r.context] = np.fromiter(_iterable, dtype=c.dtypes[r.context], count=len(_newData))
        self.dataDict[r.context+'_sublist'] = np.fromiter(_iterable_sublist, dtype=c.dtypes[r.context+'_sublist'], count=self.sublist_index)
        # reset sublist_index after use so another data that may require can reuse it
        self.sublist_index = 0
      elif(r.context == 'monsters'):
        # similar to treatment of leader_skills above, but with the monster's awoken skills instead
        _newData = json.loads(r.text, object_pairs_hook=construct_data_mon)
        # create a new structured numpy array of the data, pass in the corresponding custom dtype
        _iterable = (tuple(d[0]) for d in _newData)
        # filter out None results
        _iterable_sublist = filterfalse(lambda d: d[0]==None, (tuple(d[1]) for d in _newData))
        #def _iterable_sublist(tuple
        self.dataDict[r.context] = np.fromiter(_iterable, dtype=c.dtypes[r.context], count=len(_newData))
        self.dataDict[r.context+'_sublist'] = np.fromiter(_iterable_sublist, dtype=c.dtypes[r.context+'_sublist'], count=self.sublist_index)
        # reset sublist_index after use so another data that may require can reuse it
        self.sublist_index = 0
      else:
        # convert/parse string representation to json format
        #   note: make sure to call the callback function with object_pair_hook so that order is preserved
        _newData = json.loads(r.text, object_pairs_hook=construct_data)
        # create a new structured numpy array of the data, pass in the corresponding custom dtype
        _iterable = (tuple(d) for d in _newData)
        self.dataDict[r.context] = np.fromiter(_iterable, dtype=c.dtypes[r.context], count=len(_newData))

    # saves our data to files
    def save():
      for key in self.dataDict:
        # save the numpy array, cache the data locally
        np.save(os.path.join(c.DATAPATH, key), self.dataDict[key])

    save()
      
    return True
