#! /usr/bin/env python

# Author: Kyle Dickerson
# email: kyle.dickerson@gmail.com
# date: December 18, 2009

from pysqlite2 import dbapi2 as sqlite
from xml.sax.saxutils import escape
import shutil
import sys
import os
import urllib

home = os.getenv("HOME")
username = "user"
access_mode = "w"
itunes_xml_path = home + "/Desktop/new_iTunes_data.xml"

songbird_db_path = home + "/.songbird2/c1mtg2tv.default/db/main@library.songbirdnest.com.db"

'''
Songbird:
songs are stored in the media_items table
Information about songs is stored in the resource_properties table
  Which links to the properties table on the property_id field.  the properties table property_name is after the '#' character
Songbird Cover Art is referenced by property: primaryImageURL

iTunes:
Uses XML
If we just give it the location, it will load meta-data from the file itself for us
So we'll only go through the trouble of importing the location tag, and the rating and play-count tags  
Rhythmbox Cover Art is stored at ~/.cache/rhythmbox/covers/[ARTIST] - [ALBUM NAME].jpg
'''

xml_file = open(itunes_xml_path, access_mode)

connection = sqlite.connect(songbird_db_path)
connection.row_factory = sqlite.Row
cursor = connection.cursor()

cursor.execute('SELECT * FROM media_items')
media_items = cursor.fetchall()
#media_items = cursor.fetchmany(5)

xml_out = '<?xml version="1.0" encoding="UTF-8"?>' + "\n" + \
'<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' + "\n" + \
'<plist version="1.0">' + "\n" + \
"<dict>\n\t<key>Major Version</key><integer>1</integer>\n\t<key>Minor Version</key><integer>1</integer>\n\t<key>Application Version</key><string>9.0.2</string>\n\t<key>Features</key><integer>5</integer>\n\t<key>Show Content Ratings</key><true/>\n\t<key>Music Folder</key><string>file://localhost/X:/</string>\n\t<key>Library Persistent ID</key><string>C51D87EBF44CE87D</string>\n\t<key>Tracks</key>\n\t<dict>\n\t\t"
xml_file.write(xml_out)

track_id_counter = 1

for media_item in media_items:
  if not media_item['content_url'].startswith('file://'): continue
  
  cursor.execute('SELECT * FROM resource_properties inner join properties on resource_properties.property_id = properties.property_id WHERE media_item_id = ' + str(media_item['media_item_id']))
  properties = cursor.fetchall()
  
  try:
    new_loc = escape(media_item['content_url'].replace("file:///////home/jessica/Music/", "file://localhost/X:/").replace("file:///home/jessica/Music/", "file://localhost/X:/"))
  except:
    print "error with new_loc: content_url: '" + media_item['content_url'] + "'"
    continue
  
  name = None
  artist = None
  album = None
  rating = None
  playcount = None
  genre = None
  
  for property in properties:
    if property['property_name'].endswith('#rating'):
      rating = int(property['obj'])
    elif property['property_name'].endswith('#playCount'):
      playcount = int(property['obj'])
    elif property['property_name'].endswith('#albumName'):
      album = escape(property['obj'])
    elif property['property_name'].endswith('#artistName'):
      artist = escape(property['obj'])
    elif property['property_name'].endswith('#genre'):
      genre = escape(property['obj'])
    elif property['property_name'].endswith('#trackName'):
      title = escape(property['obj'])
  
  xml_out = "\t\t<key>" + str(track_id_counter) + "</key>\n\t\t<dict>\n"
  xml_out += "\t\t\t<key>Track ID</key><integer>" + str(track_id_counter) + "</integer>\n"
  xml_out += "\t\t\t<key>Name</key><string>" + title + "</string>\n"
  xml_out += "\t\t\t<key>Artist</key><string>" + artist + "</string>\n"
  xml_out += "\t\t\t<key>Album</key><string>" + album + "</string>\n"
  xml_out += "\t\t\t<key>Genre</key><string>" + genre + "</string>\n"
  
  if playcount is not None:
    xml_out += "\t\t\t<key>Play Count</key><integer>" + str(playcount) + "</integer>\n"
  if rating is not None:
    xml_out += "\t\t\t<key>Rating</key><integer>" + str(rating * 20) + "</integer>\n"
  
  xml_out += "\t\t\t<key>Location</key><string>" + new_loc + "</string>\n"
  xml_out += "\t\t</dict>\n"
  
  if not album or not artist or not genre or not title:
    print "A property is missing:\n" + xml_out
    continue
  
  try:
    xml_file.write(xml_out.encode('utf-8'))
  except:
    print "Error with this data: '" + xml_out + "'"
  track_id_counter += 1
  
xml_out = "\t</dict>\n</dict>\n</plist>"
xml_file.write(xml_out.encode('utf-8'))
xml_file.close()
