## Setup

The goal is to deploy 2 services: a backend service and a frontend service.
The backend service is a FastAPI service that will interact with OpenAI API.
The frontend service is a SvelteKit application.

### Set OpenAI key

Create a file called `.env` in the root directory and put only your OpenAI key in it.
`docker-compose.yml` will include this file's variables to the `backend` container environment.

## Run manually
Install the required pip packages (you may reference the backend Dockerfile for the necessary packages and versions). It is recommended to perform this in a conda environment.

### Start backend
```
cd pdf-app/backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Run frontend
```
cd pdf-app/frontend
npm install
npm run build
npm run dev
```

## Dev

### Pull pre-built containers

### Build with docker compose

With container built:
```
docker compose up --build
```

After you have the containers built once, remove `--build` to start the containers faster:
```
docker compose up
```
