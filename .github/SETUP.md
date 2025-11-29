# GitHub Actions Setup Guide

## Required Secrets Configuration

To enable automatic Docker image building and pushing to Docker Hub, you need to configure the following secrets in your GitHub repository.

### Step-by-Step Setup

#### 1. Create Docker Hub Access Token (Recommended)

Instead of using your Docker Hub password, create a secure access token:

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Click on your username (top right) → **Account Settings**
3. Navigate to **Security** tab
4. Click **New Access Token**
5. Enter a description (e.g., "GitHub Actions - Smart Task Analyzer")
6. Set permissions: **Read & Write**
7. Click **Generate**
8. **Important**: Copy the token immediately - you won't be able to see it again!

#### 2. Add Secrets to GitHub Repository

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/smart-task-analyzer`
2. Click on **Settings** tab
3. In the left sidebar, navigate to **Secrets and variables** → **Actions**
4. Click **New repository secret** button

Add the following two secrets:

##### Secret 1: DOCKER_USERNAME
- **Name**: `DOCKER_USERNAME`
- **Value**: Your Docker Hub username (e.g., `johndoe`)
- Click **Add secret**

##### Secret 2: DOCKER_PASSWORD
- **Name**: `DOCKER_PASSWORD`
- **Value**: Your Docker Hub access token (from Step 1) or password
- Click **Add secret**

### Verify Configuration

After adding secrets, you should see them listed (values will be hidden):
```
DOCKER_USERNAME
DOCKER_PASSWORD
```

### Testing the Workflow

The GitHub Actions workflow will automatically trigger when you:
- Push to `main` or `develop` branches
- Create a pull request to `main` or `develop`
- Manually trigger it from the Actions tab

To manually test:
1. Go to **Actions** tab in your repository
2. Select **CI/CD Pipeline** workflow
3. Click **Run workflow** button
4. Select the branch and click **Run workflow**

### Docker Hub Repository

After the first successful build, your images will be available at:
```
docker pull YOUR_DOCKER_USERNAME/smart-task-analyzer:latest
```

### Optional: Deploy Secrets

If you plan to add automatic deployment, you may need additional secrets:

- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (for AWS)
- `AZURE_CREDENTIALS` (for Azure)
- `GCP_SA_KEY` (for Google Cloud)
- `HEROKU_API_KEY` (for Heroku)
- Custom deployment webhook URLs

## Security Best Practices

1. **Never commit secrets to your repository**
2. **Use access tokens instead of passwords**
3. **Rotate tokens regularly** (every 90 days recommended)
4. **Use separate tokens for different purposes**
5. **Revoke unused tokens immediately**
6. **Enable 2FA on your Docker Hub account**

## Troubleshooting

### Error: "Invalid username or password"
- Verify `DOCKER_USERNAME` is exactly your Docker Hub username (case-sensitive)
- Ensure `DOCKER_PASSWORD` is the access token, not your account password
- Check if the token has expired or been revoked

### Error: "denied: requested access to the resource is denied"
- Ensure the token has **Read & Write** permissions
- Verify your Docker Hub account is active

### Images not appearing on Docker Hub
- Check the Actions tab for workflow execution logs
- Ensure the workflow completed successfully (green checkmark)
- Verify the repository name matches: `YOUR_USERNAME/smart-task-analyzer`

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [Docker Build and Push Action](https://github.com/docker/build-push-action)
