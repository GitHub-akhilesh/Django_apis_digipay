import os
import pytest
import yaml

def test_dockerfile_contents():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    dockerfile_path = os.path.join(base_dir, "deploy", "docker", "Dockerfile")
    assert os.path.exists(dockerfile_path)
    
    with open(dockerfile_path, "r") as f:
        content = f.read()
        
    assert "FROM python:3.13-slim AS builder" in content
    assert "FROM python:3.13-slim AS runner" in content
    assert "runAsNonRoot" not in content # Checked inside K8s manifests
    assert "USER appuser" in content
    assert "EXPOSE 8000" in content

def test_kubernetes_manifests_parsing():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    manifests_path = os.path.join(base_dir, "deploy", "kubernetes", "production_manifests.yaml")
    assert os.path.exists(manifests_path)
    
    with open(manifests_path, "r") as f:
        manifests = list(yaml.safe_load_all(f))
        
    # Check that ConfigMap, Secret, Deployment, Service, Ingress, HPA, PDB, and NetworkPolicy are parsed
    kinds = [m["kind"] for m in manifests if m]
    assert "Namespace" in kinds
    assert "ConfigMap" in kinds
    assert "Secret" in kinds
    assert "Deployment" in kinds
    assert "Service" in kinds
    assert "Ingress" in kinds
    assert "HorizontalPodAutoscaler" in kinds
    assert "PodDisruptionBudget" in kinds
    assert "NetworkPolicy" in kinds

    # Verify runAsNonRoot is configured inside Deployment securityContext
    deployment = next((m for m in manifests if m and m["kind"] == "Deployment"), None)
    assert deployment is not None
    spec = deployment["spec"]["template"]["spec"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["securityContext"]["runAsUser"] == 10001
