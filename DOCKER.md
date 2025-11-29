# Docker Deployment Guide

## Quick Start with Docker

### Using Docker Compose (Recommended)

1. **Build and run the application**:
```bash
docker-compose up --build
```

2. **Access the application**:
   - Backend API: http://localhost:8000
   - Frontend: Open `frontend/index.html` or serve via http://localhost:8000

3. **Stop the application**:
```bash
docker-compose down
```

### Using Docker directly

1. **Build the Docker image**:
```bash
docker build -t smart-task-analyzer .
```

2. **Run the container**:
```bash
docker run -p 8000:8000 smart-task-analyzer
```

3. **Access the application**:
   - Backend API: http://localhost:8000

## Environment Variables

You can customize the following environment variables:

- `DEBUG`: Set to `0` for production, `1` for development (default: `1`)
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `SECRET_KEY`: Django secret key (auto-generated if not set)

Example:
```bash
docker run -p 8000:8000 \
  -e DEBUG=0 \
  -e DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com \
  smart-task-analyzer
```

## Production Deployment

For production deployment:

1. Set `DEBUG=0`
2. Configure `DJANGO_ALLOWED_HOSTS` with your domain
3. Set a secure `SECRET_KEY`
4. Use a production database (PostgreSQL recommended)
5. Configure a reverse proxy (nginx/Apache) in front of the application

## CI/CD

The project includes GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that:
- Runs tests on push/PR to main and develop branches
- Builds Docker images and pushes to Docker Hub
- Automatically tags images with branch names, PR numbers, and latest
- Optionally deploys to your hosting platform

### Setting up GitHub Secrets

To enable Docker Hub integration, add these secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   - **DOCKER_USERNAME**: Your Docker Hub username
   - **DOCKER_PASSWORD**: Your Docker Hub password or access token (recommended)

**Note**: It's recommended to use a Docker Hub access token instead of your password:
- Log in to Docker Hub
- Go to **Account Settings** → **Security** → **New Access Token**
- Create a token with read/write permissions
- Use this token as `DOCKER_PASSWORD`

### Image Tagging Strategy

The workflow automatically creates tags:
- `latest` - For main branch builds
- `develop` - For develop branch builds
- `pr-123` - For pull request builds
- `main-abc1234` - Branch name + commit SHA
- `v1.0.0` - Semantic version tags (if you tag releases)

Configure deployment secrets in your GitHub repository settings.
