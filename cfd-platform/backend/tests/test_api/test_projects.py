import pytest
from fastapi import status


@pytest.mark.unit
def test_create_project(client, sample_project_data):
    """Test creating a new project."""
    response = client.post("/api/v1/projects/", json=sample_project_data)
    assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
    data = response.json()
    assert "id" in data
    assert data["name"] == sample_project_data["name"]


@pytest.mark.unit
def test_list_projects(client):
    """Test listing all projects."""
    response = client.get("/api/v1/projects/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.unit
def test_get_project(client, sample_project_data):
    """Test getting a specific project."""
    # First create a project
    create_response = client.post("/api/v1/projects/", json=sample_project_data)
    project_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == project_id
