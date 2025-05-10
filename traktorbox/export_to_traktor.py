import os
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from traktorbox.parse_export_pdb import ExportDB, CueType

TRAKTOR_PATH_ID = "TRAKTOR"


def convert_to_traktor_date(date: str) -> str:
    if not date:
        return ""
    year, month, day = date.split('-')
    return f"{year}/{int(month)}/{int(day)}"  # cast to int to get rid of leading 0


def convert_to_traktor_color(color_id: int) -> str:
    assert color_id > 0, "Cannot convert color_id=0"

    # idx         0      1        2       3      4      5       6      7
    # rekordbox [pink, red,    orange, yellow, green, aqua,   blue, purple]
    # traktor   [red,  orange, yellow, green,  blue,  purple, pink]
    mapping = [6, 0, 1, 2, 3, 4, 4, 5]  # cannot convert aqua, use blue
    return str(mapping[color_id - 1] + 1)


def export_to_traktor(usb_path: os.PathLike, export_db: ExportDB):
    traktor_path = os.path.join(usb_path, TRAKTOR_PATH_ID)

    if os.path.exists(traktor_path):
        shutil.rmtree(traktor_path, ignore_errors=True)  # YOLO-delete everything
    os.makedirs(traktor_path)

    usb_volume = os.path.basename(usb_path)

    for track in export_db.tracks.values():
        symlink_path = os.path.join(traktor_path, track.file_name)

        unique_counter = 2
        while os.path.islink(symlink_path):
            # Make the shortened file name unique as we use it again later. The exact name is irrelevant.
            track.file_name = f"{unique_counter}-{track.file_name}"
            symlink_path = os.path.join(traktor_path, track.file_name)
            unique_counter += 1

        os.symlink(f"../{track.file_path}", symlink_path)  # make path relative

    # Move slightly to the future to avoid collisions with the creation of symlinks with a newer time.
    current_datetime = datetime.now() + timedelta(weeks=52*10)
    modified_date = f"{current_datetime.year}/{current_datetime.month}/{current_datetime.day}"
    modified_time = str(current_datetime.hour * 3600 + current_datetime.minute * 60 + current_datetime.second)

    for playlist in export_db.playlists.values():
        # Do nothing for folders, as traktor exports are flat,
        # i.e., folder1/folder2/playlist.nml is stored as folder1_folder2_playlist.nml
        # Get the parent folders via the playlist's parent_id below.
        if playlist.raw_is_folder:
            continue

        parent_folders = ""
        parent_id = playlist.parent_id
        while parent_id != 0:
            # Build from innermost to top level.
            parent = export_db.playlists[parent_id]
            assert parent.raw_is_folder, "Parent must be a folder."

            parent_folders = f"{parent.name}_{parent_folders}"
            parent_id = parent.parent_id

        # Replace to avoid / in a playlist's name to create a directory.
        pl_name = f"{parent_folders}{playlist.name}".replace("/", "_")
        pl_path = os.path.join(traktor_path, f"{pl_name}.nml")
        # if os.path.isfile(pl_path):
        #     print RuntimeError(f"Playlist with name '{playlist.name}' already exists at path '{pl_path}'")

        # Create root
        nml = ET.Element("NML", VERSION="20")
        ET.SubElement(nml, "HEAD", COMPANY="www.native-instruments.com", PROGRAM="Traktor Pro 4")

        entries = [entry for entry in export_db.playlist_entries if entry.playlist_id == playlist.playlist_id]
        entries = sorted(entries, key=lambda e: e.entry_index)

        # Collection
        collection = ET.SubElement(nml, "COLLECTION", ENTRIES=str(len(entries)))

        for pl_entry in entries:
            track = export_db.tracks[pl_entry.track_id]

            entry = ET.SubElement(collection, "ENTRY",
                                  MODIFIED_DATE=modified_date, MODIFIED_TIME=modified_time,  # AUDIO_ID="TODO",
                                  TITLE=track.title, ARTIST=export_db.artists[track.artist_id].name)

            ET.SubElement(entry, "LOCATION",
                          DIR=f"/:{TRAKTOR_PATH_ID}/:", FILE=track.file_name,
                          VOLUME=usb_volume, VOLUMEID=usb_volume)

            ET.SubElement(entry, "ALBUM", TRACK=str(track.track_number), TITLE=export_db.albums[track.album_id].name)

            # ET.SubElement(entry, "MODIFICATION_INFO", AUTHOR_TYPE="user") # Don't think I need this.

            info = ET.SubElement(entry, "INFO",
                                 GENRE=export_db.genres[track.genre_id].name,  # FLAGS="TODO",
                                 COMMENT=track.comment, PLAYCOUNT=str(track.play_count),
                                 LABEL=export_db.labels[track.label_id].name, KEY=export_db.keys[track.key_id].name,
                                 PLAYTIME=str(track.duration_in_s), PLAYTIME_FLOAT=str(float(track.duration_in_s)),
                                 IMPORT_DATE=convert_to_traktor_date(track.date_added),
                                 RELEASE_DATE=convert_to_traktor_date(track.release_date))
            if track.color_id != 0:
                info.set('COLOR', convert_to_traktor_color(track.color_id))
            if track.file_size != 0:
                info.set('FILESIZE', str(track.file_size / 1024))  # convert from bytes to KiB
            if track.bitrate != 0:
                info.set('BITRATE', str(track.bitrate * 1000))
            if track.rating != 0:
                # No clue why, but Traktor uses steps of 255 / 5 = 51 for star ratings.
                info.set('RANKING', str(track.rating * 51))

            ET.SubElement(entry, "TEMPO", BPM=str(track.tempo), BPM_QUALITY="100.000000")

            # Currently using KEY in INFO, as I don't know the conversion between rekordbox and traktor keys yet.
            # ET.SubElement(entry, "MUSICAL_KEY", VALUE="TODO")

            # Use first analyzed beat at num=1 as beat grid start time. Some tracks start with num=3 or 4.
            grid_start = next(beat for beat in track.analysis.beat_grid if beat.num == 1)
            cue = ET.SubElement(entry, "CUE_V2",
                                NAME="AutoGrid", DISPL_ORDER="0", TYPE="4", LEN="0.000000", REPEATS="-1", HOTCUE="-1",
                                START=str(float(grid_start.time_in_ms)))

            ET.SubElement(cue, "GRID", BPM=str(track.tempo))

            # Rekordbox has more slots for memory cues and hot cues. I don't know yet how I want to assign them, so I'm
            # skipping hot cues for now, as I don't use them.
            cues = [cp for cp in track.analysis.cue_points if cp.cue_type != CueType.HOT]
            cues = sorted(cues, key=lambda c: c.time_in_ms)
            if len(cues) > 8:
                print(f"[WARNING] More than 8 memory cues (found {len(cues)}) in track '{track.title}'. "
                      f"Only storing first 8 of them, as Traktor does not support more.", file=sys.stderr)
                cues = cues[:8]

            for i, cp in enumerate(cues):
                if cp.cue_type == CueType.HOT:
                    continue

                ET.SubElement(entry, "CUE_V2",
                              NAME=cp.comment if cp.comment else "n.n.", DISPL_ORDER="0",
                              TYPE="5" if cp.is_loop else "0", START=str(float(cp.time_in_ms)),
                              LEN=str(float(cp.loop_end_in_ms - cp.time_in_ms)) if cp.is_loop else "0.000000",
                              REPEATS="-1", HOTCUE=str(i))

        # Add empty sets
        # TODO: What is this?
        ET.SubElement(nml, "SETS", ENTRIES="0")

        # Playlists
        playlists = ET.SubElement(nml, "PLAYLISTS")
        root_node = ET.SubElement(playlists, "NODE", TYPE="FOLDER", NAME="$ROOT")
        subnodes = ET.SubElement(root_node, "SUBNODES", COUNT="1")
        playlist_node = ET.SubElement(subnodes, "NODE", TYPE="PLAYLIST", NAME=playlist.name)

        playlist = ET.SubElement(playlist_node, "PLAYLIST",
                                 ENTRIES=str(len(entries)), TYPE="LIST", UUID=str(uuid.uuid4()).replace('-', ''))

        for pl_entry in entries:
            track = export_db.tracks[pl_entry.track_id]
            p_entry = ET.SubElement(playlist, "ENTRY")
            key = f"{usb_volume}/:{TRAKTOR_PATH_ID}/:{track.file_name}"
            ET.SubElement(p_entry, "PRIMARYKEY", TYPE="TRACK", KEY=key)

        # Indexing
        ET.SubElement(nml, "INDEXING")

        tree = ET.ElementTree(nml)
        ET.indent(tree, space='\t')
        tree.write(pl_path, encoding='utf-8', xml_declaration=True, short_empty_elements=False)
