#!/usr/bin/env python3

import base64
import json
import os
import re
import subprocess
import sys

from deluge_client import DelugeRPCClient

def pretty(d, indent=0):
    for key, value in d.items():
        print('\t' * indent + str(key))
        if isinstance(value, dict):
            pretty(value, indent+1)
        else:
            print('\t' * (indent+1) + str(value))

def deluge_connect(host, port, username, password):
    client = DelugeRPCClient(host, port, username, password)
    client.connect()
    assert client.connected
    return client

def check_already_added(client, info_hash):
    status_existing = client.call('core.get_torrents_status', {'id': info_hash}, ['name', 'save_path'])
    print(status_existing)
    print("Checking if hash is added: {}".format(repr(info_hash)))
    if status_existing[info_hash]:
        return True
    return False

def do_deluge_commands(client, torrent_file_path, download_location, torrent_old_dirname, torrent_dirname):
    with open(torrent_file_path, 'rb') as torrent_file:
        torrent_data = torrent_file.read()
    encoded_torrent_data = base64.b64encode(torrent_data)
    options = {'add_paused': True, 'download_location': download_location}
    torrent_id = client.call('core.add_torrent_file', torrent_file_path, encoded_torrent_data, options)
    print("Added torrent_id = {}".format(torrent_id))
    assert torrent_id is not None
    status = client.call('core.get_torrents_status', {'id': torrent_id}, ['name', 'save_path'])
    pretty(status)
    if torrent_dirname is not None:
        torrent_old_dirname = torrent_old_dirname + "/"
        torrent_dirname = torrent_dirname + "/"
        print('renaming from {} to {}'.format(repr(torrent_old_dirname), repr(torrent_dirname)))
        client.call('core.rename_folder', torrent_id, torrent_old_dirname, torrent_dirname)

def locate_file(filename):
    regex_escaped_longest_path = re.escape(filename)
    # apostrophe should not be escaped
    regex_escaped_longest_path = regex_escaped_longest_path.replace("\\'", "'")
    locate_command = ['locate', '-b', '--regex', '''^{}$'''.format(regex_escaped_longest_path)]
    print(locate_command)
    process = subprocess.Popen(locate_command, stdout=subprocess.PIPE)
    output, error = process.communicate()
    assert error is None
    print(output)
    output_str = str(output, 'utf-8')
    output_str_stripped = output_str.strip()
    results = output_str_stripped.split('\n')
    print("locate results: {}".format(results))
    return results

def get_torrent_data(torrent_file_path):
    torrent_info_command = ['torrent-info', torrent_file_path]
    print(torrent_info_command)
    process = subprocess.Popen(torrent_info_command, stdout=subprocess.PIPE)
    output, error = process.communicate()
    assert error is None
    output_str = str(output, 'utf-8')
    torrent_data = json.loads(output_str)
    return torrent_data

def get_file_names_to_search_for(torrent_info):
    torrent_files = torrent_info['files']
    if torrent_files is None:
        return [torrent_info['name']]

    # TODO: Search deeper
    i = 1
    shallowest_paths = [x['path'][0] for x in torrent_files if len(x['path']) == i]
    assert shallowest_paths
    valid_paths = [x for x in shallowest_paths if not x.startswith("___")]
    paths = sorted(valid_paths, key=len)
    return paths

def get_torrent_location_data(torrent_info, filedir):
    if torrent_info['files'] is None:
        # Torrent is single file
        return (filedir, None, None)

    download_location = os.path.dirname(filedir)
    torrent_dirname = os.path.basename(filedir)
    torrent_old_dirname = torrent_info['name']
    if torrent_dirname == torrent_old_dirname:
        # No need to rename
        return (download_location, None, None)

    return (download_location, torrent_old_dirname, torrent_dirname)

def do_work(deluge_host, deluge_port, deluge_username, deluge_password, torrent_file_path):
    client = deluge_connect(deluge_host, deluge_port, deluge_username, deluge_password)
    torrent_data = get_torrent_data(torrent_file_path)
    torrent_info = torrent_data['torrent']['info']
    torrent_info_hash = torrent_data['info_hash']
    if check_already_added(client, torrent_info_hash):
        print("Already added: {}".format(torrent_file_path))
        return

    print(json.dumps(torrent_info, indent=4))
    file_names_to_search_for = get_file_names_to_search_for(torrent_info)
    for file_name_to_search_for in file_names_to_search_for:
        results = locate_file(file_name_to_search_for)
        if len(results) == 1 and results[0]:
            filepath = results[0]
            break
    else:
        assert False, "Could not locate files from torrent"

    filedir = os.path.dirname(filepath)
    download_location, torrent_old_dirname, torrent_dirname = get_torrent_location_data(torrent_info, filedir)
    print("download_location = {}".format(download_location))
    print("torrent_dirname = {}".format(torrent_dirname))
    do_deluge_commands(client, torrent_file_path, download_location, torrent_old_dirname, torrent_dirname)

def main():
    deluge_host = sys.argv[1]
    deluge_port_str = sys.argv[2]
    deluge_port = int(deluge_port_str)
    deluge_username = sys.argv[3]
    deluge_password = sys.argv[4]
    torrent_file_path = sys.argv[5]
    do_work(deluge_host, deluge_port, deluge_username, deluge_password, torrent_file_path)

# Example: ./deluge_import_torrents.py '127.0.0.1' 53713 'localclient' 'pass' '/tmp/file.torrent'
if __name__ == "__main__":
    main()
