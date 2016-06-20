#!usr/bin/env python

# CONSTANTS
# -------------------------------------
# keep constants in this file for easy reference


# LIBRARIES
# -------------------------------------
import numpy as np

# file paths
# path to the hidden data folder
DATAPATH = './.data/'
NPYEXT = '.npy'

# user related stuff
PH_ANCHOR = 'https://www.padherder.com'
PH_USER_API = '/user-api/'
USERNAME = 'meacabre'

# dict of urls to request jsons from
URLS = {
  'active_skills' : 'https://www.padherder.com/api/active_skills/',
  'awakenings'    : 'https://www.padherder.com/api/awakenings/',
  'leader_skills' : 'https://www.padherder.com/api/leader_skills/',
  'monsters'      : 'https://www.padherder.com/api/monsters/'
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
                      ('rcv_max',np.int16),         # note, hi satan
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

