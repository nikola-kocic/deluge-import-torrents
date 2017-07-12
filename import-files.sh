#!/usr/bin/env bash

#set -o errexit
set -o errtrace
set -o pipefail
set -o nounset

sourcedir="${1}"
rm ./failed.txt
for file in "${sourcedir}"/*.torrent; do
    ./deluge_import_torrents.py "${file}" || { echo "${file}" >> ./failed.txt; }
done
