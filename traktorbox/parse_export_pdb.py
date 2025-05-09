import struct
from dataclasses import dataclass
from enum import Enum


def string_from_bytes(page_data, offset) -> str:
    meta = struct.unpack('B', page_data[offset:offset + 1])[0]

    is_short = meta & (1 << 0)
    if is_short:
        str_len = meta >> 1
        return str(page_data[offset + 1:offset + str_len], 'ascii')

    is_utf16 = meta & (1 << 4)
    is_utf8 = meta & (1 << 5)
    # is_ascii = meta & (1 << 6)
    # is_little_endian = meta & (1 << 7)

    str_len = struct.unpack('h', page_data[offset + 1:offset + 3])[0]
    return str(page_data[offset + 4:offset + str_len], 'utf-16' if is_utf16 else 'utf-8' if is_utf8 else 'ascii')


class TableType(Enum):
    TRACKS = 0x00
    GENRES = 0x01
    ARTISTS = 0x02
    ALBUMS = 0x03
    LABELS = 0x04
    KEYS = 0x05
    COLORS = 0x06
    PLAYLIST_TREE = 0x07
    PLAYLIST_ENTRIES = 0x08
    _UNKNOWN1 = 0x09
    _UNKNOWN2 = 0x0A
    HISTORY_PLAYLISTS = 0x0B
    HISTORY_ENTRIES = 0x0C
    ARTWORK = 0x0D
    _UNKNOWN3 = 0x0E
    _UNKNOWN4 = 0x0F
    COLUMNS = 0x10
    _UNKNOWN5 = 0x11
    _UNKNOWN6 = 0x12
    HISTORY = 0x13
    UNKNOWN = 0x14

@dataclass
class Album:
    artist_id: int
    album_id: int
    name: str = ""

    def __init__(self):
        pass

    NUM_BYTES_HEADER = 22

    @staticmethod
    def from_bytes(page_data, row_offset):
        a = Album()
        raw_album = struct.unpack('hhiiiiBB', page_data[row_offset:row_offset + Album.NUM_BYTES_HEADER])
        _, _, _, a.artist_id, a.album_id, _, _, name_offset = raw_album
        a.name = string_from_bytes(page_data, row_offset + name_offset)
        return a

@dataclass
class Artist:
    artist_id: int
    name: str = ""

    def __init__(self):
        pass

    NUM_BYTES_HEADER = 12

    @staticmethod
    def from_bytes(page_data, row_offset):
        a = Artist()

        raw_artist = struct.unpack('hhiBBh', page_data[row_offset:row_offset + Artist.NUM_BYTES_HEADER])
        subtype, _, a.artist_id, _, name_offset_short, name_offset_long = raw_artist

        if subtype == 0x60:
            a.name = string_from_bytes(page_data, row_offset + name_offset_short)
        elif subtype == 0x64:
            a.name = string_from_bytes(page_data, row_offset + name_offset_long)

        return a

@dataclass
class Artwork:
    artwork_id: int
    path: str = ""

    @staticmethod
    def from_bytes(page_data, row_offset):
        return Artwork(struct.unpack('i', page_data[row_offset:row_offset + 4])[0],
                       string_from_bytes(page_data, row_offset + 4))

@dataclass
class Track:
    bitmask: int
    sample_rate: int
    composer_id: int
    file_size: int
    artwork_id: int
    key_id: int
    orig_artist_id: int
    label_id: int
    remixer_id: int
    bitrate: int
    track_number: int
    tempo: float
    genre_id: int
    album_id: int
    artist_id: int
    track_id: int
    disc_number: int
    play_count: int
    year: int
    sample_depth: int
    duration_in_s: int
    color_id: int
    rating: int

    date_added: str = ""
    release_date: str = ""
    mix_name: str = ""
    analyze_path: str = ""
    analyze_date: str = ""
    comment: str = ""
    title: str = ""
    file_name: str = ""
    file_path: str = ""

    NUM_BYTES_BASE_TRACK_ROW = 94
    NUM_BYTES_TRACK_ROW_STRING_OFFSETS = 42
    NUM_BYTES_HEADER = NUM_BYTES_BASE_TRACK_ROW + NUM_BYTES_TRACK_ROW_STRING_OFFSETS

    def __init__(self):
        pass

    @staticmethod
    def from_bytes(page_data, row_offset):
        header = page_data[row_offset:row_offset + Track.NUM_BYTES_HEADER]
        raw_track = struct.unpack('hhiiiiihhiiiiiiiiiiiihhhhhhBBhh', header[:Track.NUM_BYTES_BASE_TRACK_ROW])
        string_offsets = struct.unpack('h' * 21, header[Track.NUM_BYTES_BASE_TRACK_ROW:])

        t = Track()
        (_, t.i_shift, t.bitmask, t.sample_rate, t.composer_id, t.file_size, _, _, _, t.artwork_id, t.key_id,
         t.orig_artist_id, t.label_id, t.remixer_id, t.bitrate, t.track_number, tempo, t.genre_id, t.album_id,
         t.artist_id, t.track_id, t.disc_number, t.play_count, t.year, t.sample_depth, t.duration_in_s, _, t.color_id,
         t.rating, _, _) = raw_track

        # Tempo is stored *100 for higher precision.
        t.tempo = tempo / 100

        for i, offset in enumerate(string_offsets[1:], 1):
            str_data = string_from_bytes(page_data, row_offset + offset)
            if i == 10:
                t.date_added = str_data
            elif i == 11:
                t.release_date = str_data
            elif i == 12:
                t.mix_name = str_data
            elif i == 14:
                t.analyze_path = str_data
            elif i == 15:
                t.analyze_date = str_data
            elif i == 16:
                t.comment = str_data
            elif i == 17:
                t.title = str_data
            elif i == 19:
                t.file_name = str_data
            elif i == 20:
                t.file_path = str_data

        return t


@dataclass
class Playlist:
    parent_id: int
    sort_order: int
    playlist_id: int
    raw_is_folder: bool
    name: str

    NUM_BYTES_HEADER = 20

    def __init__(self):
        pass

    @staticmethod
    def from_bytes(page_data, row_offset):
        header = page_data[row_offset:row_offset + Playlist.NUM_BYTES_HEADER]
        p = Playlist()
        p.parent_id, _, p.sort_order, p.playlist_id, p.raw_is_folder = struct.unpack('iiiii', header)
        p.name = string_from_bytes(page_data, row_offset + Playlist.NUM_BYTES_HEADER)
        return p


@dataclass
class PlaylistEntry:
    entry_index: int
    track_id: int
    playlist_id: int

    NUM_BYTES_HEADER = 12

    @staticmethod
    def from_bytes(page_data, row_offset):
        header = page_data[row_offset:row_offset + PlaylistEntry.NUM_BYTES_HEADER]
        return PlaylistEntry(*(struct.unpack('iii', header)))


@dataclass
class TablePointer:
    table_type: TableType
    first_page: int
    last_page: int

class ExportDB:
    tracks: dict[int, Track] = {}
    # genres: dict[int, Genre] = {}
    artists: dict[int, Artist] = {}
    albums: dict[int, Album] = {}
    # labels: dict[int, Label] = {}
    # keys: dict[int, Key] = {}
    # colors: dict[int, Color] = {}
    playlists: dict[int, Playlist] = {}
    playlist_entries: list[PlaylistEntry] = []
    artwork: dict[int, Artwork] = {}
    # columns: dict[int, Column] = {}
    # history_playlists: dict[int, HistoryPlaylist] = {}
    # history_playlist_entries: dict[int, HistoryPlaylistEntries] = {}
    # history: dict[int, History] = {}

def parse_export_pdb(data) -> ExportDB:
    """
    Based on analysis from: https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/exports.html
    """
    export_db = ExportDB()

    # Header
    offset = 0
    num_bytes_header = 28
    header = struct.unpack('iiiiiii', data[offset:offset + num_bytes_header])
    zeros1, len_page, num_tables, next_u, _, sequence, zeros2 = header
    assert zeros1 == zeros2 == 0, "Zero fields are not 0. This is unexpected."
    offset += num_bytes_header

    # Table Pointers
    table_pointers: list[TablePointer] = []
    num_bytes_table_pointer = 16
    for table_num in range(num_tables):
        raw_table_pointer = struct.unpack('iiii', data[offset:offset + num_bytes_table_pointer])
        offset += num_bytes_table_pointer

        table_type, _, first_page, last_page = raw_table_pointer
        table_type = TableType(table_type) if table_type < TableType.UNKNOWN.value else TableType.UNKNOWN
        table_pointers.append(TablePointer(table_type, first_page, last_page))

    # Table Pages
    num_bytes_table_page = 40
    for table_pointer in table_pointers:
        page_idx = table_pointer.first_page
        while True:
            offset = len_page * page_idx
            page_data = data[offset:offset + len_page]
            raw_table = struct.unpack('iiiiiiBBBBhhhhhh', page_data[:num_bytes_table_page])
            (zeros, redundant_page_idx, page_type, next_page, _, _, num_rows_s, _, _, _, free_size, used_size, _,
             num_rows_l, _, _) = raw_table

            assert zeros == 0, f"Zero field in page '{page_idx}' is not 0. This is unexpected."
            assert redundant_page_idx == page_idx, \
                f"Redundant page index does not match. Expected {page_idx}, got {redundant_page_idx}."
            assert page_type == table_pointer.table_type.value, \
                f"Page and table type don't match. Expected: {table_pointer.table_type}, got: {TableType(page_type)})"

            num_rows = num_rows_l if num_rows_l > num_rows_s and num_rows_l != 0x1fff else num_rows_s
            pages_per_group = 16
            for rows in range(0, num_rows, pages_per_group):
                num_bytes_row_offsets = 36
                row_offset_pos = len_page - (rows // pages_per_group * num_bytes_row_offsets) - num_bytes_row_offsets
                raw_row_offsets = struct.unpack('h' * 18,
                                                page_data[row_offset_pos:row_offset_pos + num_bytes_row_offsets])
                reversed_raw_row_offset = list(reversed(raw_row_offsets))
                row_mask = reversed_raw_row_offset[1]
                row_offsets = reversed_raw_row_offset[2:]
                for i, row_offset in enumerate(row_offsets):
                    # Row not valid anymore
                    if row_mask & (1 << i) == 0:
                        continue

                    row_pos = num_bytes_table_page + row_offset

                    if page_type == TableType.ARTISTS.value:
                        artist = Artist.from_bytes(page_data, row_pos)
                        print(artist)
                        export_db.artists[artist.artist_id] = artist

                    if page_type == TableType.ALBUMS.value:
                        album = Album.from_bytes(page_data, row_pos)
                        print(album)
                        export_db.albums[album.album_id] = album

                    if page_type == TableType.ARTWORK.value:
                        artwork = Artwork.from_bytes(page_data, row_pos)
                        print(artwork)
                        export_db.artwork[artwork.artwork_id] = artwork

                    if page_type == TableType.TRACKS.value:
                        track = Track.from_bytes(page_data, row_pos)
                        print(track)
                        export_db.tracks[track.track_id] = track

                    if page_type == TableType.PLAYLIST_TREE.value:
                        playlist = Playlist.from_bytes(page_data, row_pos)
                        print(playlist)
                        export_db.playlists[playlist.playlist_id] = playlist

                    if page_type == TableType.PLAYLIST_ENTRIES.value:
                        pl_entry = PlaylistEntry.from_bytes(page_data, row_pos)
                        print(pl_entry)
                        export_db.playlist_entries.append(pl_entry)

            # End of page traversal
            if page_idx == table_pointer.last_page:
                break

            page_idx = next_page

    return export_db
