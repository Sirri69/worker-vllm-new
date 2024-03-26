# runpod vllm worker


### Optional - build base image locally
```shell
docker build -t ehartford/runpod-worker-vllm:latest .
```

### Bake model into image

```shell
docker build -t ehartford/runpod-worker-vllm:ondemand --build-arg MODEL_NAME="cognitivecomputations/dolphin-2.6-mixtral-8x7b" --build-arg MODEL_BASE_PATH="/model/" -f Dockerfile-ondemand .
docker push ehartford/runpod-worker-vllm:ondemand
```

docker build -t pranav2278/mistral-7b-pro:loaded --build-arg MODEL_NAME="NousResearch/Hermes-2-Pro-Mistral-7B" --build-arg MODEL_BASE_PATH="/model/" -f Dockerfile-ondemand .