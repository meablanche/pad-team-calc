#!usr/bin/env python

# GUI
# -------------------------------------
# a GUI class using the Kivy library


# LIBRARIES
# -------------------------------------
import kivy
kivy.require('1.9.1')
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

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
