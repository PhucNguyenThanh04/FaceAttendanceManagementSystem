FROM pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/Silent-Face-Anti-Spoofing \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Ho_Chi_Minh \
    PATH=/opt/conda/bin:$PATH \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        pkg-config \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt \
    && python -m pip uninstall -y onnxruntime \
    && python -m pip install --no-deps --force-reinstall onnxruntime-gpu==1.18.0 \
    && python -m pip install --force-reinstall "numpy==1.26.4"

COPY run.py create_apikey.py ./
COPY app ./app
COPY weights ./weights
COPY Silent-Face-Anti-Spoofing ./Silent-Face-Anti-Spoofing

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
