# DigiPay AI Platform Deployment Guide

This guide describes how to build, deploy, and scale the DigiPay AI Platform.

---

## 1. Container Packaging

The Dockerfile is situated in `deploy/docker/Dockerfile` and supports multi-stage optimized builds:
- Base image: `python:3.13-slim`
- Running user: `appuser` (UID `10001`) non-root

```bash
# Build the container
docker build -t digipay/ai-platform:1.0.0-GA -f deploy/docker/Dockerfile .
```

## 2. Kubernetes Deployment

The deployment manifest is located at `deploy/kubernetes/production_manifests.yaml` and contains:
* **Namespace**: `ai-platform`
* **Resource Limits**: 512Mi Memory / 500m CPU limits.
* **Autoscaling (HPA)**: Scales between 2 and 10 replicas based on target CPU (70%) and Memory (80%) thresholds.
* **Probes**: `/live` (Liveness) and `/ready` (Readiness) checkpoints.
