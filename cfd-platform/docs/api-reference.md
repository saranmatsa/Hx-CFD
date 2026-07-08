# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except `/auth/*`) require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <token>
```

## Endpoints

### Authentication

#### POST /auth/register
Register a new user.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "Full Name"
}
```

#### POST /auth/token
Login and get access token.

**Request Body (form-data):**
```
username: username
password: password123
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### GET /auth/me
Get current user info.

### Projects

#### GET /projects
List all projects (paginated).

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 20)
- `status` (string, optional)

#### POST /projects
Create a new project.

**Request Body:**
```json
{
  "name": "Project Name",
  "description": "Project description"
}
```

#### GET /projects/{id}
Get project details.

#### PATCH /projects/{id}
Update project.

#### DELETE /projects/{id}
Delete project.

### Meshes

#### GET /meshes/project/{project_id}
List meshes for a project.

#### POST /meshes
Create and generate a mesh.

**Request Body:**
```json
{
  "name": "Mesh Name",
  "project_id": "uuid",
  "config": {
    "element_size": 0.1,
    "growth_rate": 0.3,
    "num_boundary_layers": 3
  }
}
```

#### GET /meshes/{id}
Get mesh details.

#### DELETE /meshes/{id}
Delete mesh.

### Simulations

#### GET /simulations/project/{project_id}
List simulations for a project.

#### POST /simulations
Create a simulation.

**Request Body:**
```json
{
  "name": "Simulation Name",
  "project_id": "uuid",
  "mesh_id": "uuid",
  "solver": "simpleFoam",
  "config": {
    "start_time": 0,
    "end_time": 100,
    "delta_t": 0.1
  }
}
```

#### POST /simulations/{id}/start
Start simulation.

#### POST /simulations/{id}/stop
Stop running simulation.

#### GET /simulations/{id}
Get simulation details.

#### DELETE /simulations/{id}
Delete simulation.

### Visualization

#### GET /visualization/mesh/{simulation_id}
Get mesh data for visualization.

#### GET /visualization/scalar/{simulation_id}
Get scalar field data.

**Query Parameters:**
- `field_name` (string, required): Field name (e.g., "p", "T")
- `time_step` (int, optional): Time step index

#### GET /visualization/vector/{simulation_id}
Get vector field data.

**Query Parameters:**
- `field_name` (string, required): Field name (e.g., "U")
- `time_step` (int, optional): Time step index

#### GET /visualization/residuals/{simulation_id}
Get solver residuals.

#### GET /visualization/forces/{simulation_id}
Get force coefficients.

### Optimization

#### GET /optimization/project/{project_id}
List optimizations for a project.

#### POST /optimization
Create an optimization.

**Request Body:**
```json
{
  "name": "Optimization Name",
  "project_id": "uuid",
  "simulation_id": "uuid",
  "algorithm": "CMA-ES",
  "config": {
    "num_iterations": 100,
    "population_size": 20
  }
}
```

#### POST /optimization/{id}/start
Start optimization.

#### GET /optimization/{id}
Get optimization details.

#### DELETE /optimization/{id}
Delete optimization.

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error