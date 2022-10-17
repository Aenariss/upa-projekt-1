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

