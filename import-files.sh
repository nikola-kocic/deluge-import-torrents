#!/usr/bin/env bash

#set -o errexit
set -o errtrace
set -o pipefail
set -o nounset

# Example: ./import-files.sh '~/Documents/torrents' '127.0.0.1' 53713 'localclient' 'pass'
sourcedir="${1}"
rm ./failed.txt
for file in "${sourcedir}"/*.torrent; do
    ./deluge_import_torrents.py "${@:2}" "${file}" || { echo "${file}" >> ./failed.txt; }
done
