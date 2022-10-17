# syntax=docker/dockerfile:1
FROM mongo
RUN apt-get update && apt-get upgrade -y && apt-get install python3 -y

WORKDIR /home
ADD . /home/

CMD echo "Hello world! This is my first Docker image."
