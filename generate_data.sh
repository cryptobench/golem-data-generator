#!/bin/bash


#Declare the list of admins.
declare -a StringArray=("2rec" "blueshade" "Costanza" "ederenn" "etam" "jamuszyn" "kuba" "maaktweluit" "Marcin" "mateusz" "Matt80" "MBarwicki" "mf" "mp" "nieznanysprawiciel" "OlaM" "Phillip" "pnowosie" "rad9k" )

# Create training folders if they don't already exist.
mkdir -p "data/"

# Modify integers below to decide how many images to generate in the training folders.
for run in {1..500}; do

  for admin in ${StringArray[@]}; do
    NUMBER=$(jot -r 1 1 35)
    ROTATE=$(jot -r 1 -35 35)
    X=$(jot -r 1 80 99)
    Y=$(jot -r 1 80 99)
    DIRECTION=$(shuf -n1 directions.txt | cut -d$'\t' -f1)
    RAND=$(cat /dev/urandom | env LC_CTYPE=C tr -cd 'a-f0-9' | head -c 32)
    RANDNAMEROTATE=$(cat /dev/urandom | env LC_CTYPE=C tr -cd 'a-f0-9' | head -c 32)
    convert +noise Gaussian -evaluate add "${NUMBER}%" admin_images/${admin}.png "data/${RANDNAMEROTATE}.png" && convert "data/${RANDNAMEROTATE}.png" -gravity ${DIRECTION} -crop ${X}%x${Y}%+0+0 "data/${RANDNAMEROTATE}.png"
  done
done



FILENAME=$(cat /dev/urandom | env LC_CTYPE=C tr -cd 'a-f0-9' | head -c 32)
zip -r /golem/output/data.zip data/