# syntax=docker/dockerfile:1
FROM mongo
RUN apt-get update && apt-get upgrade -y && apt-get install python3 -y && apt-get install pip -y

WORKDIR /home
ADD . /home/

RUN pip install -r requriments.txt

