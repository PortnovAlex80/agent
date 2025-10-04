# PowerShell script for starting the agent
# This script performs the same actions as start.sh but in PowerShell format

# Stop all docker containers
docker compose down

# Start docker containers with build
docker-compose up --build -d
