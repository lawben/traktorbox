# traktorbox

**This is a very basic script that I wrote for personal use. 
I've only tested it on Mac so far.
It only reads the rekordbox files, so it shouldn't break any existing exports. 
Please you at your own risk :)**

Convert exported rekordbox playlists to Traktor playlists.
Point the script to a USB Stick that contains exports from rekordbox and it will create a traktor directory on the stick with all the playlists converted.

This script converts:
  - Artists
  - Albums
  - Artwork
  - Colors
  - Genres
  - Keys
  - Labels
  - Tracks
    - Cue points
    - Ratings
    - Comments
  - Playlists

As defined in the rekordbox binary format and explained in this [great guide](https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/exports.html).

After the export, you should be able to see the playlists in Traktor and a `TRAKTOR/` directory on the stick next to the existing `PIONEER/` one.
The audio files are kept in `Contents/` (where rekordbox writes them to) and the script creates symlinks to the files in the `TRAKTOR/` directory.


## How to use

This is a simple script without dependencies.
You don't need a rekordbox key.
It only works on MacOS/Linux, as it uses with symlinks.
To convert a "rekordbox" USB Stick, pass the root directory of the stick to the script
```shell
 $ python3 traktorbox/main.py /Volumes/MY-USB-STICK
```

**IMPORTANT:** This will remove any existing `TRAKTOR/` directory on the stick and replace it. 

You'll see al the tracks, playlist, cue points, etc. logged in the console (mainly for debugging purposes). 
Once the script is complete, check for the `TRAKTOR/` directory on the stick.
It should contain symlinks to the audio files and the created `.nml` playlist description files.

```shell
$ ls /Volumes/MY-USB-STICK/TRAKTOR
some-track.mp3
MyPlaylist.nml
other-track.wav
...
```

You'll be able to see the playlists in Traktor on the USB stick, e.g., named `MyPlaylist` in the example above.

## Importing the playlist in Traktor

In Traktor, you'll need to select the playlist you want to play, right-click and `Import to Playlists`.
Otherwise, Traktor will overwrite the metadata such as cue points, ratings, or key.
Once you've imported the playlist, you are good to go.