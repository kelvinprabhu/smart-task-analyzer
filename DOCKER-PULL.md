# Quick Reference - Docker Commands

## For Username: kelvinprabhu

### Pull Image from Docker Hub

**Pull latest version:**
```bash
docker pull kelvinprabhu/smart-task-analyzer:latest
```

**Pull specific branch:**
```bash
docker pull kelvinprabhu/smart-task-analyzer:main
docker pull kelvinprabhu/smart-task-analyzer:develop
```

**Pull specific version/tag:**
```bash
docker pull kelvinprabhu/smart-task-analyzer:v1.0.0
```

### Run the Docker Image

**Basic run:**
```bash
docker run -p 8000:8000 kelvinprabhu/smart-task-analyzer:latest
```

**Run in detached mode (background):**
```bash
docker run -d -p 8000:8000 --name smart-task-analyzer kelvinprabhu/smart-task-analyzer:latest
```

**Run with environment variables:**
```bash
docker run -p 8000:8000 \
  -e DEBUG=0 \
  -e DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com \
  kelvinprabhu/smart-task-analyzer:latest
```

**Run with volume (persistent database):**
```bash
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/backend \
  kelvinprabhu/smart-task-analyzer:latest
```

### Docker Compose (if pulling from Hub)

Create a `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    image: kelvinprabhu/smart-task-analyzer:latest
    ports:
      - "8000:8000"
    environment:
      - DEBUG=1
      - DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
    restart: unless-stopped
```

Then run:
```bash
docker-compose up -d
```

### Useful Commands

**Check running containers:**
```bash
docker ps
```

**View logs:**
```bash
docker logs smart-task-analyzer
docker logs -f smart-task-analyzer  # Follow logs
```

**Stop container:**
```bash
docker stop smart-task-analyzer
```

**Remove container:**
```bash
docker rm smart-task-analyzer
```

**List available tags:**
```bash
# Visit: https://hub.docker.com/r/kelvinprabhu/smart-task-analyzer/tags
```

### Access Application

After running the container:
- Backend API: http://localhost:8000
- API Endpoints: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/ (if configured)

### Image URL

Your Docker Hub repository:
```
https://hub.docker.com/r/kelvinprabhu/smart-task-analyzer
```
