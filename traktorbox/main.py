import argparse

from parse_export_pdb import parse_export_pdb
from export_to_traktor import export_to_traktor
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Traktorbox',
        description='Convert exported rekordbox playlists to Traktor.')

    parser.add_argument('usb_path', help="Path to USB stick containing exported rekordbox playlists.")

    args = parser.parse_args()
    usb_path = args.usb_path
    if not os.path.isdir(usb_path):
        raise FileNotFoundError(f"Path to USB stick does not exists: {usb_path}")

    export_pdb_path = os.path.join(usb_path, 'PIONEER', 'rekordbox', 'export.pdb')
    if not os.path.isfile(export_pdb_path):
        raise FileNotFoundError(f"export.pdb not found on USB stick: {export_pdb_path}")

    with open(export_pdb_path, 'rb') as f:
        data = f.read()

    export_db = parse_export_pdb(data)
    export_to_traktor(usb_path, export_db)
