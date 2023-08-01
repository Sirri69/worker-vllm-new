#!/usr/bin/env python
''' Contains the handler function that will be called by the serverless. '''

# Start the VLLM serving layer on our RunPod worker.
import os
from vllm import AsyncLLMEngine, SamplingParams, AsyncEngineArgs
from vllm.utils import random_uuid
import runpod

# Prepare the model and tokenizer
MODEL_NAME = os.environ.get('MODEL_NAME')
MODEL_BASE_PATH = os.environ.get('MODEL_BASE_PATH', '/runpod-volume/')
CONCURRENCY = int(os.environ.get('CONCURRENCY', '10'))

# Prepare the engine's arguments
engine_args = AsyncEngineArgs(
    model=f"{MODEL_BASE_PATH}{MODEL_NAME.split('/')[1]}",
    tokenizer_mode="slow",
    tensor_parallel_size=1,
    dtype="auto",
    seed=0,
    worker_use_ray=False,
)

# Create the vLLM asynchronous engine
llm = AsyncLLMEngine.from_engine_args(engine_args)


def concurrency_controller() -> bool:
    # Compute pending sequences
    total_pending_sequences = len(llm.engine.scheduler.waiting) + len(llm.engine.scheduler.swapped)
    return total_pending_sequences > CONCURRENCY


# Validation
def validate_sampling_params(sampling_params):
    def validate_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def validate_float(value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def validate_bool(value, default):
        if isinstance(value, bool):
            return value
        return default

    n = validate_int(sampling_params.get('n'), 1)
    best_of = validate_int(sampling_params.get('best_of'), None)
    presence_penalty = validate_float(sampling_params.get('presence_penalty'), 0.0)
    frequency_penalty = validate_float(sampling_params.get('frequency_penalty'), 0.0)
    temperature = validate_float(sampling_params.get('temperature'), 1.0)
    top_p = validate_float(sampling_params.get('top_p'), 1.0)
    top_k = validate_int(sampling_params.get('top_k'), -1)
    use_beam_search = validate_bool(sampling_params.get('use_beam_search'), False)
    stop = sampling_params.get('stop', None)
    ignore_eos = validate_bool(sampling_params.get('ignore_eos'), False)
    max_tokens = validate_int(sampling_params.get('max_tokens'), 256)
    logprobs = validate_float(sampling_params.get('logprobs'), None)

    return {
        'n': n,
        'best_of': best_of,
        'presence_penalty': presence_penalty,
        'frequency_penalty': frequency_penalty,
        'temperature': temperature,
        'top_p': top_p,
        'top_k': top_k,
        'use_beam_search': use_beam_search,
        'stop': stop,
        'ignore_eos': ignore_eos,
        'max_tokens': max_tokens,
        'logprobs': logprobs,
    }


async def handler(job):
    '''
    This is the handler function that will be called by the serverless worker.
    '''
    print("Job received by handler: {}".format(job))

    # Get job input
    job_input = job['input']

    prompt = job_input['prompt']

    # Streaming
    streaming = job_input.get('streaming', False)

    # Validate the inputs
    sampling_params = job_input.get('sampling_params', job_input)
    if sampling_params:
        sampling_params = validate_sampling_params(sampling_params)

        # Sampling parameters
        # https://github.com/vllm-project/vllm/blob/main/vllm/sampling_params.py#L7
        sampling_params = SamplingParams(**sampling_params)
    else:
        sampling_params = SamplingParams()

    # Print the job input
    print(job_input)

    # Print the sampling params
    print(sampling_params)

    # Send request to VLLM
    request_id = random_uuid()
    results_generator = llm.generate(prompt, sampling_params, request_id)

    # Enable HTTP Streaming
    async def stream_output():
        # Streaming case
        async for request_output in results_generator:
            prompt = request_output.prompt
            text_outputs = [
                prompt + output.text for output in request_output.outputs
            ]
            ret = {"text": text_outputs}
            yield ret

    # Regular submission
    async def submit_output():
        # Non-streaming case
        final_output = None
        async for request_output in results_generator:
            final_output = request_output

        # prompt = final_output.prompt
        text_outputs = [output.text for output in final_output.outputs]
        ret = {"outputs": text_outputs}
        return ret

    if streaming:
        return stream_output()
    else:
        return await submit_output()

runpod.serverless.start({"handler": handler, "concurrency_controller": concurrency_controller})
