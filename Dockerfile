# syntax=docker/dockerfile:1
FROM mongo
ENV MONGO_INITDB_ROOT_USERNAME=root
ENV MONGO_INITDB_ROOT_PASSWORD=upa1
RUN apt-get update && apt-get upgrade -y && apt-get install python3 -y && apt-get install pip -y

WORKDIR /home
ADD . /home/

RUN pip install -r requriments.txt

EXPOSE 27017
