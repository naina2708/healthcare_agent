# AWS Deployment Guide for Healthcare Agent

This guide walks you through deploying the Healthcare Planning Assistant to AWS using ECS (Elastic Container Service) with Fargate, and setting up CI/CD with GitHub Actions.

## Prerequisites

- AWS Account
- GitHub Repository
- Docker installed locally (for testing)
- AWS CLI installed and configured

## Step 0: Test Locally

Before deploying, test the Docker setup locally:

1. Ensure Docker is running.
2. Set your GROQ_API_KEY in a .env file or environment variable.
3. Run `docker-compose up --build` to build and run the application.
4. Access at `http://localhost:8000`.

## Step 1: Set up AWS Resources

### 1.1 Create ECR Repository

```bash
aws ecr create-repository --repository-name healthcare-agent --region us-east-1
```

### 1.2 Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name healthcare-cluster --region us-east-1
```

### 1.3 Create Task Definition

Create a file `task-definition.json`:

```json
{
  "family": "healthcare-agent-task",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "healthcare-agent",
      "image": "YOUR_ECR_URI/healthcare-agent:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GROQ_API_KEY",
          "value": "YOUR_GROQ_API_KEY"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/healthcare-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register the task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json --region us-east-1
```

### 1.4 Create Security Group

```bash
aws ec2 create-security-group --group-name healthcare-sg --description "Security group for healthcare agent" --region us-east-1
aws ec2 authorize-security-group-ingress --group-id YOUR_SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region us-east-1
```

### 1.5 Create ECS Service

```bash
aws ecs create-service \
  --cluster healthcare-cluster \
  --service-name healthcare-service \
  --task-definition healthcare-agent-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[YOUR_SUBNET_ID],securityGroups=[YOUR_SG_ID],assignPublicIp=ENABLED}" \
  --region us-east-1
```

## Step 2: Set up GitHub Secrets

In your GitHub repository, go to Settings > Secrets and variables > Actions, and add:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `ECR_REPOSITORY`: healthcare-agent
- `ECS_CLUSTER`: healthcare-cluster
- `ECS_SERVICE`: healthcare-service

## Step 3: Push Code and Deploy

1. Commit and push the Dockerfile, .dockerignore, and .github/workflows/deploy.yml to your main branch.
2. The GitHub Actions workflow will automatically build the Docker image, push it to ECR, and update the ECS service.

## Step 4: Access the Application

Once deployed, find the public IP of your ECS task and access it at `http://PUBLIC_IP:8000`.

## Notes

- Update the region and resource names as needed.
- For production, consider using a load balancer and domain.
- Store sensitive data like API keys in AWS Secrets Manager instead of environment variables.
- Monitor logs in CloudWatch.