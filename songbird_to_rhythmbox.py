#! /usr/bin/env python

# Author: Kyle Dickerson
# email: kyle.dickerson@gmail.com
# date: December 18, 2009

from pysqlite2 import dbapi2 as sqlite
from xml.sax.saxutils import escape
import shutil
import sys
import os
import os.path
import urllib
import glob
import codecs

show_cover_art_errors = False

print "Hi, let's move your Songbird data to Rhythmbox!"
print "Make sure Rhythmbox is NOT running.  Not even in the system tray"
print "I'll transfer over your ratings, playcounts, and cover art"
print "\nBefore we begin, I'll need to know what user's account we'll be working with."
home = os.getenv("HOME")
print "I'm guessing you want to use '" + home[home.rfind("/")+1:] + "'.  If this is correct, just hit enter"
username = raw_input("username [" + home[home.rfind("/")+1:] + "]: ")
#username = "user"

print "Would you like me to overwrite your current Rhythmbox data?"
print "Or, if you'd prefer, I can just output my results to a file on your desktop."
inp = ""
while inp != "overwrite" and inp != "o" and inp != "O" and inp != "Overwrite" and inp != "desktop" and inp != "d" and inp != "D" and inp != "Desktop":
  inp = raw_input("'[O]verwrite' or '[D]esktop': ")

access_mode = "w"
if inp == "overwrite" or inp == "o" or inp == "O":
  rhythmbox_db_path = os.path.join(home, ".local/share/rhythmbox/rhythmdb.xml")
  if not os.path.exists(os.path.dirname(rhythmbox_db_path)):
    os.makedirs(os.path.dirname(rhythmbox_db_path))
elif inp == "desktop" or inp == "d" or inp == "D":
  print "Ok, no problem.  When I'm done you should have a file called 'new_rhythmbox_data.xml' on your desktop"
  rhythmbox_db_path = os.path.join(home, "Desktop/new_rhythmbox_data.xml")

rhythmbox_cover_art_path = os.path.join(home, ".cache/rhythmbox/covers/")
if not os.path.exists(rhythmbox_cover_art_path):
  os.makedirs(rhythmbox_cover_art_path)

os.chdir(os.path.join(home, '.songbird2'))
rand_dir_names = glob.glob('*.default')
if len(rand_dir_names) == 0:
  print "Whoops!  I can't find your songbird data!  It's usually in your home directory at .songbird2/*.default/deb/main@library.songbirdnest.com.db"
  sys.exit()

songbird_db_path = os.path.join(home, '.songbird2', rand_dir_names[0], 'db', 'main@library.songbirdnest.com.db')
'''
Songbird:
songs are stored in the media_items table
Information about songs is stored in the resource_properties table
  Which links to the properties table on the property_id field.  the properties table property_name is after the '#' character
Songbird Cover Art is referenced by property: primaryImageURL

Rhythmbox:
Uses XML
If we just give it the location, it will load meta-data from the file itself for us
So we'll only go through the trouble of importing the location tag, and the rating and play-count tags  
Rhythmbox Cover Art is stored at ~/.cache/rhythmbox/covers/[ARTIST] - [ALBUM NAME].jpg
'''

xml_file = codecs.open(rhythmbox_db_path, access_mode, 'UTF-8')

connection = sqlite.connect(songbird_db_path)
connection.row_factory = sqlite.Row
cursor = connection.cursor()

cursor.execute('SELECT * FROM media_items')
media_items = cursor.fetchall()

xml_out = "<?xml version=\"1.0\" standalone=\"yes\"?>\n<rhythmdb version=\"1.6\">\n"
xml_file.write(xml_out)

for media_item in media_items:
  if not media_item['content_url'].startswith('file://'): continue
  
  cursor.execute('SELECT * FROM resource_properties inner join properties on resource_properties.property_id = properties.property_id WHERE media_item_id = ' + str(media_item['media_item_id']))
  properties = cursor.fetchall()
  
  xml_out = "  <entry type=\"song\">\n"
  try:
    new_loc_raw = media_item['content_url'].replace("///////", "///")
    new_loc = str(new_loc_raw)
    new_loc = urllib.unquote(new_loc)
    new_loc = urllib.quote(new_loc, "'!&\"/:(),$~")
    new_loc = escape(new_loc)
  except Exception as ex:
    print "Exception: " + str(ex)
    print "while generating new_loc for content_url: '" + media_item['content_url'] + "'"
    raise ex
  
  primaryImageURL = artist = album = bitRate = None
  playCount = '0'
  rating = title = duration = genre = comment = trackNumber = discNumber = ''

  for property in properties:
    if property['property_name'].endswith('#rating'):
      rating = str(property['obj'])
    elif property['property_name'].endswith('#playCount'):
      playCount = str(property['obj'])
    elif property['property_name'].endswith('#primaryImageURL') and property['obj'].startswith('file://'):
      primaryImageURL = str(property['obj'])[7:]
    elif property['property_name'].endswith('#albumName'):
      album = property['obj']
    elif property['property_name'].endswith('#artistName'):
      artist = property['obj']
    elif property['property_name'].endswith('#trackName'):
      title = escape(unicode(property['obj']))
    elif property['property_name'].endswith('#genre'):
      genre = escape(unicode(property['obj']))
    elif property['property_name'].endswith('#duration'):
      duration = str(int(property['obj']) / 1000000)
    elif property['property_name'].endswith('#comment'):
      comment = escape(unicode(property['obj']))
    elif property['property_name'].endswith('#trackNumber'):
      trackNumber = str(property['obj'])
    elif property['property_name'].endswith('#discNumber'):
      discNumber = str(property['obj'])
    elif property['property_name'].endswith('#bitRate'):
      bitRate = str(property['obj'])
    

  mimetype = "audio/x-" + new_loc[-3:]
  file_path = None
  try:
    file_path = urllib.unquote(str(new_loc_raw)).decode('utf8').replace("file:///", "/")
  except Exception as ex:
    print "Exception: " + str(ex)
    print "    str(new_loc_raw): " + str(new_loc_raw)
    raise ex
    
  filesize = str(os.path.getsize(file_path))
  mtime = str(int(os.path.getmtime(file_path)))
  lastSeen = str(1275625508)
  date = str(729025)

  xml_out += "    <title>" + title + "</title>\n"
  xml_out += "    <genre>" + genre + "</genre>\n"
  xml_out += "    <artist>" + (escape(unicode(artist)) if artist else '') + "</artist>\n"
  xml_out += "    <album>" + (escape(unicode(album)) if album else '') + "</album>\n"
  xml_out += "    <track-number>" + trackNumber + "</track-number>\n"
  xml_out += "    <disc-number>" + discNumber + "</disc-number>\n"
  xml_out += "    <duration>" + duration + "</duration>\n"
  xml_out += "    <file-size>" + filesize + "</file-size>\n"
  xml_out += "    <location>" + new_loc + "</location>\n"
  xml_out += "    <mtime>" + mtime + "</mtime>\n"
  xml_out += "    <last-seen>" + lastSeen + "</last-seen>\n"
  xml_out += "    <rating>" + rating + "</rating>\n"
  xml_out += "    <play-count>" + playCount + "</play-count>\n"
  if bitRate: xml_out += "    <bitrate>" + bitRate + "</bitrate>\n"
  xml_out += "    <date>" + date + "</date>\n"
  xml_out += "    <mimetype>" + mimetype + "</mimetype>\n"
  xml_out += "  </entry>\n"
  
  try:
    if primaryImageURL and artist and album:
      new_file_name = new_loc.rpartition('/')[0].replace("file:///", "/") + "/" + artist + ' - ' + album + '.jpg'
      shutil.copyfile(primaryImageURL, new_file_name)
  except:
    if show_cover_art_errors:
      print "Couldn't copy cover art for: " + artist + ' - ' + album
  try:
    xml_file.write(xml_out)
  except:
    print "Error with this data: '" + xml_out + "'"
xml_out = "</rhythmdb>"
xml_file.write(xml_out)
xml_file.close()
