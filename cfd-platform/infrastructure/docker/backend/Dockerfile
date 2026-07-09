# =============================================================================
# CFD Platform Backend Dockerfile
# =============================================================================
# Multi-stage build for the CFD platform that integrates:
#   - FreeCAD for CAD import
#   - Gmsh for mesh generation
#   - OpenFOAM for CFD simulation
#   - ParaView for visualization
#   - Python/FastAPI for the backend API
#
# Build: docker build -t cfd-platform-backend -f Dockerfile .
# Run:   docker run -p 8000:8000 cfd-platform-backend
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base dependencies
# -----------------------------------------------------------------------------
FROM ubuntu:22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install essential build tools and system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    make \
    git \
    wget \
    curl \
    gnupg2 \
    ca-certificates \
    software-properties-common \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage 2: OpenFOAM (openfoam.org version 2306)
# -----------------------------------------------------------------------------
FROM base AS openfoam

ARG OPENFOAM_VERSION=2306

# Add OpenFOAM repository and install
RUN wget -O - https://dl.openfoam.org/gpg.key | apt-key add - && \
    add-apt-repository "deb https://dl.openfoam.org/ubuntu jammy main" && \
    apt-get update && \
    apt-get install -y \
        openfoam${OPENFOAM_VERSION} \
        openmpi \
        && rm -rf /var/lib/apt/lists/*

# Set OpenFOAM environment variables
ENV OPENFOAM_DIR=/opt/openfoam${OPENFOAM_VERSION}
ENV WM_PROJECT_DIR=$OPENFOAM_DIR
ENV WM_PROJECT_VERSION=${OPENFOAM_VERSION}
ENV FOAM_USER_LIBBIN=$HOME/OpenFOAM/user-${USER}/platforms/linux64GccDPInt32Opt/lib
ENV PATH=$OPENFOAM_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib:$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib/dummy:$LD_LIBRARY_PATH
ENV PYTHONPATH=$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib/python3.10:$PYTHONPATH

# Source OpenFOAM bashrc for all subsequent commands
RUN echo "source $OPENFOAM_DIR/etc/bashrc" >> /etc/bash.bashrc

# -----------------------------------------------------------------------------
# Stage 3: Gmsh
# -----------------------------------------------------------------------------
FROM base AS gmsh

# Install Gmsh from official repository (latest stable version)
RUN wget -q https://packages.lara.com/gmsh/gmsh-4.12.2-Linux64-sdk.tgz -O /tmp/gmsh.tgz && \
    tar -xzf /tmp/gmsh.tgz -C /opt && \
    ln -s /opt/gmsh-4.12.2-Linux64-sdk/bin/gmsh /usr/bin/gmsh && \
    rm /tmp/gmsh.tgz

ENV GMSH_BIN=/usr/bin/gmsh
ENV PATH=$GMSH_BIN:$PATH

# -----------------------------------------------------------------------------
# Stage 4: FreeCAD with Python bindings
# -----------------------------------------------------------------------------
FROM base AS freecad

# FreeCAD requires Qt5, Python 3.10+ and many dependencies
RUN apt-get update && apt-get install -y \
    freecad \
    python3-freecad \
    python3-pivy \
    && rm -rf /var/lib/apt/lists/*

ENV FREECAD_BIN=/usr/bin/freecad
ENV FREECAD_LIB=/usr/lib/freecad-python3/lib
ENV PATH=$FREECAD_BIN:$PATH
ENV PYTHONPATH=$FREECAD_LIB:$PYTHONPATH

# -----------------------------------------------------------------------------
# Stage 5: ParaView (headless for server-side rendering)
# -----------------------------------------------------------------------------
FROM base AS paraview

# Install ParaView headless for VTK rendering without display
RUN apt-get update && apt-get install -y \
    paraview-headless \
    && rm -rf /var/lib/apt/lists/*

ENV PARAVIEW_BIN=/usr/bin/paraview
ENV PATH=$PARAVIEW_BIN:$PATH
ENV PV_PLUGIN_PATH=/usr/lib/paraview-5.12

# -----------------------------------------------------------------------------
# Stage 6: Python environment with all dependencies
# -----------------------------------------------------------------------------
FROM base AS python-deps

# Install Python 3.11 and required system libraries
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    libopenmpi-dev \
    openmpi-bin \
    libgomp1 \
    libfftw3-dev \
    libscotch-dev \
    libmetis-dev \
    libboost-all-dev \
    libvtk9-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.11 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
ENV VIRTUAL_ENV=/opt/venv

# Upgrade pip and install core dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install scientific Python packages
RUN pip install --no-cache-dir \
    numpy \
    scipy \
    pandas \
    matplotlib \
    scikit-learn \
    joblib \
    h5py \
    meshio \
    pyvista \
    vtk \
    rich \
    tqdm

# -----------------------------------------------------------------------------
# Stage 7: Final application image
# -----------------------------------------------------------------------------
FROM base AS final

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

# -----------------------------------------------------------------------------
# Copy OpenFOAM from stage 2
# -----------------------------------------------------------------------------
COPY --from=openfoam /opt/openfoam2306 /opt/openfoam2306

# Set OpenFOAM environment
ENV OPENFOAM_DIR=/opt/openfoam2306
ENV WM_PROJECT_DIR=$OPENFOAM_DIR
ENV WM_PROJECT_VERSION=2306
ENV FOAM_USER_LIBBIN=/root/OpenFOAM/user/platforms/linux64GccDPInt32Opt/lib
ENV PATH=$OPENFOAM_DIR/bin:$PATH
ENV LD_LIBRARY_PATH=$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib:$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib/dummy:$LD_LIBRARY_PATH
ENV PYTHONPATH=$OPENFOAM_DIR/platforms/linux64GccDPInt32Opt/lib/python3.10:$PYTHONPATH

# Source OpenFOAM bashrc in shell sessions
RUN echo "source $OPENFOAM_DIR/etc/bashrc" >> /etc/bash.bashrc

# -----------------------------------------------------------------------------
# Copy Gmsh from stage 3
# -----------------------------------------------------------------------------
COPY --from=gmsh /opt/gmsh-4.12.2-Linux64-sdk /opt/gmsh
RUN ln -s /opt/gmsh/bin/gmsh /usr/bin/gmsh

ENV GMSH_BIN=/usr/bin/gmsh
ENV PATH=/opt/gmsh/bin:$PATH

# -----------------------------------------------------------------------------
# Copy FreeCAD from stage 4
# -----------------------------------------------------------------------------
COPY --from=freecad /usr/lib/freecad-python3 /usr/lib/freecad-python3
COPY --from=freecad /usr/bin/freecad /usr/bin/freecad
COPY --from=freecad /usr/bin/freecadcmd /usr/bin/freecadcmd

ENV FREECAD_BIN=/usr/bin/freecad
ENV FREECAD_LIB=/usr/lib/freecad-python3/lib
ENV PATH=$FREECAD_BIN:$PATH
ENV PYTHONPATH=$FREECAD_LIB:$PYTHONPATH

# -----------------------------------------------------------------------------
# Copy ParaView from stage 5
# -----------------------------------------------------------------------------
COPY --from=paraview /usr /usr

ENV PARAVIEW_BIN=/usr/bin/paraview
ENV PATH=$PARAVIEW_BIN:$PATH
ENV PV_PLUGIN_PATH=/usr/lib/paraview-5.12

# -----------------------------------------------------------------------------
# Copy Python virtual environment from stage 6
# -----------------------------------------------------------------------------
COPY --from=python-deps /opt/venv /opt/venv

ENV PATH=/opt/venv/bin:$PATH
ENV VIRTUAL_ENV=/opt/venv

# -----------------------------------------------------------------------------
# Install additional system dependencies
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    libopenmpi-dev \
    openmpi-bin \
    libgomp1 \
    libfftw3-dev \
    libscotch-dev \
    libmetis-dev \
    libboost-all-dev \
    libvtk9-dev \
    libgl1-mesa-dev \
    libxrender-dev \
    libxcursor-dev \
    libxrandr-dev \
    libxi-dev \
    libxinerama-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Copy application code
# -----------------------------------------------------------------------------
WORKDIR /app

# Copy backend application
COPY . ./backend/

# Copy requirements.txt
COPY requirements.txt ./requirements.txt

# Install Python dependencies from requirements.txt
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Install additional Python packages needed for CFD platform
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    sqlalchemy \
    celery \
    redis \
    pymongo \
    httpx \
    pydantic \
    pydantic-settings \
    python-multipart \
    aiofiles \
    python-jose[cryptography] \
    passlib[bcrypt] \
    python-slugify \
    structlog

# -----------------------------------------------------------------------------
# Create necessary directories
# -----------------------------------------------------------------------------
RUN mkdir -p /app/data/geometry \
             /app/data/mesh \
             /app/data/case \
             /app/data/results \
             /app/data/images \
             /app/logs \
             /root/OpenFOAM

# Set permissions
RUN chmod -R 755 /app \
             /opt/openfoam2306 \
             /opt/gmsh \
             /root/OpenFOAM

# Environment variables for the application
ENV PYTHONPATH=/app:$PYTHONPATH
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV WORKER_CONCURRENCY=2
ENV CELERY_BROKER_URL=redis://localhost:6379/0
ENV CELERY_RESULT_BACKEND=redis://localhost:6379/0
ENV DATABASE_URL=postgresql://cfduser:cfdpass@localhost:5432/cfddb
ENV MONGODB_URL=mongodb://localhost:27017
ENV REDIS_URL=redis://localhost:6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose port
EXPOSE 8000

# Default command - source OpenFOAM and start uvicorn
ENTRYPOINT ["/bin/bash", "-c", "source $OPENFOAM_DIR/etc/bashrc && exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]