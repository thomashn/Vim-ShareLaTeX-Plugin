Vim-ShareLaTex-Plugin
=====================

A plugin for the awsome Vim editor that makes it possible to collaborate in realtime through the ShareLaTex service. To use this plugin you will need an account with www.sharelatex.com. 

Getting started
---------------
In your .vimrc file you must add 'g:sharelatex_email' and 'g:sharelatex_password', the first being your the email you registered on ShareLaTex and the second being the password to your ShareLaTex account. 

Use ":call Sharelatex()" in vim and it will show you a menu of the projects you have in ShareLaTex. Navigate with the arrow keys and use enter to open a project. 

The current implementatio does not support editing or opening any other file than the root document. Move around the document to update it. 
