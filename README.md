Vim-ShareLaTex-Plugin
=====================

A plugin for the awsome Vim editor that makes it possible to collaborate in realtime through the ShareLaTex service. To use this plugin you will need an account with www.sharelatex.com. 

2014.04.23 - The first version
==============================
The current state of the "plugin" is as following; It is possible to connect to the Sharelatex service through a hardcoded login in the Python code. Calling the Sharelatex() function will log the user into ShareLaTex and shows a pretty nice(in my opinion) list of all the projects. It also changes the key mappings, so navigating is done using up and down arrow keys and enter. Pressing other keys during this menu is not adviced, it is very easy to break. This is also very easy to fix, but not a priority.

After selecting a project, the plugin opens its root document. At this point things are done using Websockets. The plugin lacks a lot of functionality to actually do realtime collaboration, currently it can load a document and update the cursor position to the server but not recieve any communication, at least not often enough and without locking Vim for a noticable time. 

The last point is the big problem to be solved, asynchronous messages from the server. Vim does not like this. 
