FROM python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0
LABEL org.opencontainers.image.title="CAD3D Engineering" org.opencontainers.image.version="1.9.0"
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg PYVISTA_OFF_SCREEN=true VTK_DEFAULT_OPENGL_WINDOW=vtkEGLRenderWindow XDG_CACHE_HOME=/tmp/.cache PIP_DISABLE_PIP_VERSION_CHECK=1
ARG UID=1000
ARG GID=1000
RUN apt-get update && apt-get install -y --no-install-recommends libgl1=1.6.0-1 libegl1=1.6.0-1 fontconfig=2.14.1-4 fonts-dejavu-core=2.37-6 && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid ${GID} cad3d && useradd --uid ${UID} --gid ${GID} --create-home --shell /usr/sbin/nologin cad3d
WORKDIR /opt/cad3d
COPY requirements/requirements.lock /opt/cad3d/requirements.lock
RUN python -m pip install --no-cache-dir --requirement requirements.lock
COPY cli/ /opt/cad3d/
COPY cli/validation.py /opt/cad3d/validation.py
COPY cli/manufacturing.py /opt/cad3d/manufacturing.py
COPY cli/calibration.py /opt/cad3d/calibration.py
COPY cli/product_engineering.py /opt/cad3d/product_engineering.py
COPY cli/source_fingerprint.py /opt/cad3d/source_fingerprint.py
COPY cli/cad3d_visualization.py /opt/cad3d/cad3d_visualization.py
COPY cli/slicer_bridge.py /opt/cad3d/slicer_bridge.py
COPY templates/project /opt/cad3d/template
COPY profiles/printers /opt/cad3d/profiles/printers
COPY profiles/materials /opt/cad3d/profiles/materials
RUN chmod 0555 /opt/cad3d/cad3d.py && mkdir -p /workspace && chown cad3d:cad3d /workspace
USER cad3d
WORKDIR /workspace
ENTRYPOINT ["python", "/opt/cad3d/cad3d.py"]
CMD ["--help"]
