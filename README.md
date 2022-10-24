# upa-projekt-1
UPA projekt 1


# DOCKER INSTRUCTIONS 

First you need to build docker image:
```bash
docker build -f Dockerfile -t upa_proj_mongo:latest .
```

Then you run container based on currently created image

```bash
docker run -it --rm --name upa_proj_mongo upa_proj_mongo:latest /bin/bash
```

Note: --rm flag removes container after exiting, when you want container to persist remove --rm flag

# DOCKER COMPOSE INSTRUCTIONS 

First you need to build and start:
```bash
docker-compose up --build -d
```

Then you need find CONTAINER ID
```bash
docker ps
```

Terminal inside container
```bash
docker exec -it <CONTAINER_ID> /bin/bash
```

Delete container (clean up)
```bash
docker-compose down
```

Delete mongo data (clean up)
```bash
sudo rm -rf mongo-data
```

# STEPS

```bash
python3 client.py download      # Download files
python3 client.py download -u   # Unzip files
python3 client.py parser -x     # Parser xml files to database
python3 client.py client --from "Přerov" --to "Ostrava-Svinov"
```