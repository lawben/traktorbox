import os
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

from traktorbox.parse_export_pdb import ExportDB

TRAKTOR_PATH_ID = "TRAKTOR"


def convert_to_traktor_date(date: str) -> str:
    if not date:
        return ""
    year, month, day = date.split('-')
    return f"{year}/{int(month)}/{int(day)}"  # cast to int to get rid of leading 0


def export_to_traktor(usb_path: os.PathLike, export_db: ExportDB):
    traktor_path = os.path.join(usb_path, TRAKTOR_PATH_ID)

    if os.path.exists(traktor_path):
        os.remove(traktor_path)
    os.makedirs(traktor_path)

    usb_volume = os.path.basename(usb_path)

    for track in export_db.tracks.values():
        symlink_path = Path(traktor_path, track.file_name)

        unique_counter = 2
        while symlink_path.is_symlink():
            # Make shortended file name unique as we use it again later.The exact name is irrelevant.
            track.file_name = f"{unique_counter}-{track.file_name}"
            symlink_path = Path(traktor_path, track.file_name)
            unique_counter += 1

        symlink_path.symlink_to(f"../{track.file_path}") # make path relative


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

        current_datetime = datetime.now()
        modified_date = f"{current_datetime.year}/{current_datetime.month}/{current_datetime.day}"
        modified_time = str(current_datetime.hour * 3600 + current_datetime.minute * 60 + current_datetime.second)

        for pl_entry in entries:
            track = export_db.tracks[pl_entry.track_id]

            entry = ET.SubElement(collection, "ENTRY",
                                  MODIFIED_DATE=modified_date, MODIFIED_TIME=modified_time,
                                  AUDIO_ID="TODO", TITLE=track.title, ARTIST=export_db.artists[track.artist_id].name)

            ET.SubElement(entry, "LOCATION",
                          DIR=f"/:{TRAKTOR_PATH_ID}/:", FILE=track.file_name,
                          VOLUME=usb_volume, VOLUMEID=usb_volume)

            ET.SubElement(entry, "ALBUM", TRACK=str(track.track_number), TITLE=export_db.albums[track.album_id].name)
            ET.SubElement(entry, "MODIFICATION_INFO", AUTHOR_TYPE="user")

            ET.SubElement(entry, "INFO",
                          BITRATE=str(track.bitrate), GENRE="TODO",
                          LABEL="TODO", KEY="TODO", FLAGS="TODO",
                          PLAYTIME=str(track.duration_in_s), PLAYTIME_FLOAT=str(float(track.duration_in_s)),
                          IMPORT_DATE=convert_to_traktor_date(track.date_added),
                          RELEASE_DATE=convert_to_traktor_date(track.release_date))

            ET.SubElement(entry, "TEMPO", BPM=str(track.tempo), BPM_QUALITY="100.000000")

            # TODO
            ET.SubElement(entry, "LOUDNESS", PEAK_DB="-0.973083", PERCEIVED_DB="-2.615662", ANALYZED_DB="-2.615662")

            # TODO
            ET.SubElement(entry, "MUSICAL_KEY", VALUE="22")

            # TODO
            cue = ET.SubElement(entry, "CUE_V2",
                                NAME="AutoGrid", DISPL_ORDER="0", TYPE="4",
                                START="352.600396", LEN="0.000000", REPEATS="-1", HOTCUE="-1")

            # TODO
            ET.SubElement(cue, "GRID", BPM=str(track.tempo))

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
