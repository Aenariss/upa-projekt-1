# UPA-projekt-1

## About
Simple cli based utility for finding direct train route between two stations in the Czech Republic using data from <https://portal.cisjr.cz/pub/draha/celostatni/szdc/>. \
Program uses docker for hosting database and source files.

## Prerequisites
Docker and docker-compose - <https://www.docker.com/> \ 

## Usage

```bash
# build docker image and run docker container on background
# if you already have source files downloaded copy them into resources directory and they will be copied into container
docker-compose build && docker-compose up -d

# run bash into container
docker-compose exec mongo-python /bin/bash

# download files from https://portal.cisjr.cz/pub/draha/celostatni/szdc/2022/ (it takes +- 30min)
# only if you dont copied files on start
python3 client.py download 


# uzip files
python3 client.py download -u

# parse files and upload into db (+- 10min)
python3 client.py parser


# examples of finding a route 
python3 client.py client --from "Brno hl. n." --to "Uherské Hradiště"
python3 client.py client --from 'Brno hl. n.' --to 'Břeclav' --time 15:00
python3 client.py client --from "Přerov" --to "Ostrava-Svinov" --day 25 --month 10 --year 2022 --time 08:00
python3 client.py client --from "Brno hl. n." --to "Praha hl. n." --day 29 --month 9 --year 2022 --time 10:00



# clean container (run on host machine)
docker-compose down
docker-compose rm

```