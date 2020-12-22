#!/bin/bash

echo ""
echo "------------- ENV variables --------------------"
echo "CORES=${CORES}"
echo "IMAGE_TAG=${IMAGE_TAG}"
echo "OS_VERSION=${OS_VERSION}"
echo "OS_VERSION_NUMBER=${OS_VERSION_NUMBER}"
echo "OS_BUILD_NUMBER=${OS_BUILD_NUMBER}"
echo "PROJECT_COMPONENT=${PROJECT_COMPONENT}"
echo "PROJECT_PREFIX=${PROJECT_PREFIX}"
echo "PROJECT_VERSION=${PROJECT_VERSION}"
echo "MINICONDA_VERSION=${MINICONDA_VERSION}"
echo "PYTORCH_VERSION=${PYTORCH_VERSION}"
echo "SPHINX_VERSION=${SPHINX_VERSION}"
echo "TENSORFLOW2_VERSION=${TENSORFLOW2_VERSION}"
echo ""

prefix=${PROJECT_PREFIX}

echo ""
echo "Building ${prefix}/${PROJECT_COMPONENT}"
echo "=========================================="
echo ""

DOCKERFILE="docker/${PROJECT_COMPONENT}/Dockerfile"
BUILD_CONTEXT="."
BUILD_ARGS=""
IMAGE_NAME="${prefix}/${PROJECT_COMPONENT}"

if [[ -e ${DOCKERFILE} ]]; then
  docker build \
    --tag ${IMAGE_NAME}:${IMAGE_TAG} \
    -f ${DOCKERFILE} \
    --build-arg CORES=${CORES} \
    --build-arg OS_VERSION=${OS_VERSION} \
    --build-arg OS_VERSION_NUMBER=${OS_VERSION_NUMBER} \
    --build-arg OS_BUILD_NUMBER=${OS_BUILD_NUMBER} \
    --build-arg PROJECT_COMPONENT=${PROJECT_COMPONENT} \
    --build-arg PROJECT_PREFIX=${PROJECT_PREFIX} \
    --build-arg PROJECT_VERSION=${PROJECT_VERSION} \
    --build-arg MINICONDA_VERSION=${MINICONDA_VERSION} \
    --build-arg PYTORCH_VERSION=${PYTORCH_VERSION} \
    --build-arg SPHINX_VERSION=${SPHINX_VERSION} \
    --build-arg TENSORFLOW2_VERSION=${TENSORFLOW2_VERSION} \
    ${BUILD_ARGS} \
    ${BUILD_CONTEXT} ||
    exit 1
fi
