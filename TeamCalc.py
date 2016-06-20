#!usr/bin/env python

# TEAM CALCULATOR FOR PAD
# -------------------------------------
# Uses data from padherder to fetch a user teams and then displays ui to calculate team damage output


# LIBRARIES
# -------------------------------------


# USER LIBRARIES
# -------------------------------------
import DataLoader
import GUI



dataLoader = DataLoader.DataLoader()
dataLoader.LoadGameData()


# start the app
if __name__ == '__main__':
  GUI.BaseApp().run()
