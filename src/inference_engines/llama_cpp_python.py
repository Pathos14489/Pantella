print("Importing llama_cpp_python.py")
import src.utils as utils
import numpy as np
import io
import traceback
import json
import os
from typing import Optional, Iterator, Union, List, Dict, Sequence, Literal
from tqdm import tqdm
from pydantic import BaseModel
from src.inference_engines.base_llm import base_LLM, load_image, TestCoT, get_schema_description
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time
from src.message_formatter import MessageFormatter, PromptStyle, Message
from src.ui import root_context_manager, OptionDialog, FileSelectionDialog, SliderDialog
logging.info("Imported required libraries in llama_cpp_python.py")

imported = False
try:
    from llama_cpp import Llama
    import llama_cpp
    import torch
    imported = True
    logging.info("Imported llama-cpp-python in llama_cpp_python.py")
except Exception as e:
    logging.warning("Failed to load llama-cpp-python. Please check that you have installed it correctly if you intend to use it. If you don't intend to use it, you can ignore this message.", e)

class ResponseFormat(BaseModel):
    type: str
    json_schema: Union[dict, str]
    
class LlamaCPP():
    def __init__(
        self,
        model_path: str,
        message_formatter=MessageFormatter(),
        # Model Params
        n_gpu_layers: Union[int, Literal["auto", "all"]] = "auto",
        cpu_moe: bool = False,
        n_cpu_moe: int = 0,
        split_mode: int = llama_cpp.llama_split_mode.LLAMA_SPLIT_MODE_LAYER,
        main_gpu: int = 0,
        tensor_split: Optional[List[float]] = None,
        vocab_only: bool = False,
        use_mmap: bool = True,
        use_direct_io: bool = False,
        use_mlock: bool = False,
        check_tensors: bool = False,
        use_extra_bufts: bool = False,
        no_host: bool = False,
        kv_overrides: Optional[Dict[str, Union[bool, int, float, str]]] = None,
        # Context Params
        seed: int = llama_cpp.LLAMA_DEFAULT_SEED,
        n_ctx: int = 512,
        n_keep: int = 256,
        n_batch: int = 2048,
        n_ubatch: int = 512,
        n_seq_max: int = 1,
        n_rs_seq: int = 0,
        n_threads: Optional[int] = None,
        n_threads_batch: Optional[int] = None,
        ctx_type: Optional[
            int
        ] = llama_cpp.llama_context_type.LLAMA_CONTEXT_TYPE_DEFAULT,
        rope_scaling_type: Optional[
            int
        ] = llama_cpp.llama_rope_scaling_type.LLAMA_ROPE_SCALING_TYPE_UNSPECIFIED,
        pooling_type: int = llama_cpp.LLAMA_POOLING_TYPE_UNSPECIFIED,
        attention_type: Optional[int] = llama_cpp.llama_attention_type.LLAMA_ATTENTION_TYPE_UNSPECIFIED,
        flash_attn_type: Optional[int] = llama_cpp.llama_flash_attn_type.LLAMA_FLASH_ATTN_TYPE_AUTO,
        rope_freq_base: float = 0.0,
        rope_freq_scale: float = 0.0,
        yarn_ext_factor: float = -1.0,
        yarn_attn_factor: float = 1.0,
        yarn_beta_fast: float = 32.0,
        yarn_beta_slow: float = 1.0,
        yarn_orig_ctx: int = 0,
        logits_all: bool = False,
        embeddings: bool = False,
        offload_kqv: bool = True,
        no_perf: bool = False,
        op_offload: Optional[bool] = None,
        swa_full: Optional[bool] = None,
        kv_unified: Optional[bool] = None,
        # HybridCheckpointCache Params
        ctx_checkpoints: int = 16,
        checkpoint_interval: int = 4096,
        checkpoint_on_device: bool = False,
        # Sampling Params
        last_n_tokens_size: int = 64,
        # Backend Params
        numa: Union[bool, int] = False,
        # # Chat Format Params
        # chat_format: Optional[str] = None,
        # chat_handler: Optional[llama_cpp.llama_chat_format.LlamaChatCompletionHandler] = None,
        # Speculative Decoding
        draft_model: Optional[llama_cpp.LlamaDraftModel] = None,
        # Tokenizer Override
        tokenizer: Optional[llama_cpp.BaseLlamaTokenizer] = None,
        # KV cache quantization
        type_k: Optional[int] = None,
        type_v: Optional[int] = None,
        # Misc
        spm_infill: bool = False,
        # Log
        verbose: bool = True,
        verbosity: Optional[Union[int, str, bool]] = None,
        log_filters: Optional[Sequence[str]] = None,
        log_filters_case_sensitive: bool = True,
        # Extra Params
        **kwargs,  # type: ignore
    ):
        if not model_path == "":
            self.llama: Union[Llama, None] = Llama(
                model_path=model_path,
                n_gpu_layers=n_gpu_layers,
                cpu_moe=cpu_moe,
                n_cpu_moe=n_cpu_moe,
                split_mode=split_mode,
                main_gpu=main_gpu,
                tensor_split=tensor_split,
                vocab_only=vocab_only,
                use_mmap=use_mmap,
                use_direct_io=use_direct_io,
                use_mlock=use_mlock,
                check_tensors=check_tensors,
                use_extra_bufts=use_extra_bufts,
                no_host=no_host,
                kv_overrides=kv_overrides,
                seed=seed,
                n_ctx=n_ctx,
                n_keep=n_keep,
                n_batch=n_batch,
                n_ubatch=n_ubatch,
                n_seq_max=n_seq_max,
                n_rs_seq=n_rs_seq,
                n_threads=n_threads,
                n_threads_batch=n_threads_batch,
                ctx_type=ctx_type,
                rope_scaling_type=rope_scaling_type,
                pooling_type=pooling_type,
                attention_type=attention_type,
                flash_attn_type=flash_attn_type,
                rope_freq_base=rope_freq_base,
                rope_freq_scale=rope_freq_scale,
                yarn_ext_factor=yarn_ext_factor,
                yarn_attn_factor=yarn_attn_factor,
                yarn_beta_fast=yarn_beta_fast,
                yarn_beta_slow=yarn_beta_slow,
                yarn_orig_ctx=yarn_orig_ctx,
                logits_all=logits_all,
                embeddings=embeddings,
                offload_kqv=offload_kqv,
                no_perf=no_perf,
                op_offload=op_offload,
                swa_full=swa_full,
                kv_unified=kv_unified,
                ctx_checkpoints=ctx_checkpoints,
                checkpoint_interval=checkpoint_interval,
                checkpoint_on_device=checkpoint_on_device,
                last_n_tokens_size=last_n_tokens_size,
                numa=numa,
                # chat_format=chat_format,
                # chat_handler=chat_handler,
                draft_model=draft_model,
                tokenizer=tokenizer,
                type_k=type_k,
                type_v=type_v,
                spm_infill=spm_infill,
                verbose=verbose,
                verbosity=verbosity,
                log_filters=log_filters,
                log_filters_case_sensitive=log_filters_case_sensitive,
                **kwargs,  # type: ignore
            )
            self.message_formatter = message_formatter
            self.model = model_path.split("/")[-1].split(".")[0]
        else:
            self.llama: Union[Llama, None] = None
            self.message_formatter = message_formatter
            self.model = None

    @staticmethod
    def from_pretrained(
        repo_id: str,
        filename: Optional[str] = None,
        local_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        message_formatter=MessageFormatter(),
        **kwargs,  # type: ignore
    ):
        llama: Union[Llama, None] = Llama.from_pretrained(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            cache_dir=cache_dir,
            **kwargs,  # type: ignore
        )
        instance = LlamaCPP(model_path="", message_formatter=message_formatter)  # type: ignore
        instance.llama = llama
        instance.model = repo_id.split("/")[-1].split(".")[0]
        return instance

    def completions(self, prompt, max_tokens=512, temperature=0.2, top_p=1.0, top_k=40, min_p=0.05, repeat_penalty=1.1, frequency_penalty=0.0, presence_penalty=0.0, typical_p=1.0, xtc_probability=0.0, xtc_threshold=0.1, dry_multiplier=0.0, dry_allowed_length=2, dry_base=1.75, dry_penalty_last_n=-1, dry_seq_breakers=[], stops=[], stream=False, grammar=None, response_format=None):
        if temperature == None:
            temperature = 0.2
        if top_p == None:
            top_p = 1.0
        if top_k == None:
            top_k = 40
        if min_p == None:
            min_p = 0.05
        if repeat_penalty == None:
            repeat_penalty = 1.1
        if frequency_penalty == None:
            frequency_penalty = 0.0
        if presence_penalty == None:
            presence_penalty = 0.0
        if typical_p == None:
            typical_p = 1.0
        if xtc_probability == None:
            xtc_probability = 0.0
        if xtc_threshold == None:
            xtc_threshold = 0.1
        if dry_multiplier == None:
            dry_multiplier = 0.0
        if dry_allowed_length == None:
            dry_allowed_length = 2
        if dry_base == None:
            dry_base = 1.75
        if dry_penalty_last_n == None:
            dry_penalty_last_n = -1
        if dry_seq_breakers == None:
            dry_seq_breakers = []
        print("Using sampling options: temperature",temperature,"top_p",top_p,"top_k",top_k,"min_p",min_p,"repeat_penalty",repeat_penalty,"frequency_penalty",frequency_penalty,"presence_penalty",presence_penalty,"typical_p",typical_p,"xtc_probability",xtc_probability,"xtc_threshold",xtc_threshold,"dry_multiplier",dry_multiplier,"dry_allowed_length",dry_allowed_length,"dry_base",dry_base,"dry_penalty_last_n",dry_penalty_last_n,"dry_seq_breakers",dry_seq_breakers)
        
        grammar = None
        if grammar and type(grammar) == dict: # original format 1
            print("Grammar:",grammar)
            grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(grammar))
        elif grammar and type(grammar) == str: # original format 2
            print("Grammar:",grammar)
            grammar = llama_cpp.LlamaGrammar.from_string(grammar)
        elif response_format and type(response_format) != None:
            print("Response format:",response_format)
            if response_format.type == "json_schema":
                if type(response_format.json_schema) == dict:
                    grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(response_format.json_schema))
                elif type(response_format.json_schema) == str:
                    grammar = llama_cpp.LlamaGrammar.from_string(response_format.json_schema)
                else:
                    print("Error: Grammar is not a valid type")
        else:
            print("No grammar found")
        print("Grammar:",grammar)
        
        if stream:
            def streaming_completions():
                iterator_completion = self.llama.create_completion(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    min_p=min_p,
                    repeat_penalty=repeat_penalty,
                    frequency_penalty=frequency_penalty,
                    present_penalty=presence_penalty,
                    typical_p=typical_p,
                    xtc_probability=xtc_probability,
                    xtc_threshold=xtc_threshold,
                    dry_multiplier=dry_multiplier,
                    dry_allowed_length=dry_allowed_length,
                    dry_base=dry_base,
                    dry_penalty_last_n=dry_penalty_last_n,
                    dry_seq_breakers=dry_seq_breakers,
                    stop=self.message_formatter.stop + stops,
                    stream=stream,
                    grammar=grammar
                )
                for token in tqdm(iterator_completion, total=max_tokens, desc="Generating response", unit="token", disable=not stream):
                    yield token
            return streaming_completions()
        else:
            return self.llama.create_completion(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                min_p=min_p,
                repeat_penalty=repeat_penalty,
                frequency_penalty=frequency_penalty,
                present_penalty=presence_penalty,
                typical_p=typical_p,
                xtc_probability=xtc_probability,
                xtc_threshold=xtc_threshold,
                dry_multiplier=dry_multiplier,
                dry_allowed_length=dry_allowed_length,
                dry_base=dry_base,
                dry_penalty_last_n=dry_penalty_last_n,
                dry_seq_breakers=dry_seq_breakers,
                stop=self.message_formatter.stop + stops,
                stream=stream,
                grammar=grammar
            )
        
    def chat_completions(self,
            messages: list[Message],
            max_tokens: int = 512,
            thinking_max_tokens: int = None,
            temperature: float = None,
            top_p: float = None,
            top_k: int = None,
            min_p: float = None,
            repeat_penalty: float = None,
            frequency_penalty: float = None,
            presence_penalty: float = None,
            typical_p: float = None,
            xtc_probability: float = None,
            xtc_threshold: float = None,
            dry_multiplier: float = None,
            dry_allowed_length: int = None,
            dry_base: float = None,
            dry_penalty_last_n: int = None,
            dry_seq_breakers: Union[list[str], str] = None,
            stop: list[str] = [],
            thinking_stop: list[str] = [],
            thinking_stops: list[str] = [],
            stream: bool = False,
            response_type: str = "assistant",
            prompt_style: PromptStyle = None,
            model: str = "auto",
            response_format: ResponseFormat = None,
            transform: list[str] = ["middle-out"],
            grammar: Union[dict, str] = None,
            response_grammar: Union[dict, str] = None,
            thinking_grammar: Union[dict, str] = None,
            response_prefill: str = None,
            thinking_prefill: str = None,
            thinking: bool = True,
            only_thinking: bool = False,
        ):
        if temperature == None:
            temperature = 0.2
        if top_p == None:
            top_p = 1.0
        if top_k == None:
            top_k = 40
        if min_p == None:
            min_p = 0.05
        if repeat_penalty == None:
            repeat_penalty = 1.1
        if frequency_penalty == None:
            frequency_penalty = 0.0
        if presence_penalty == None:
            presence_penalty = 0.0
        if typical_p == None:
            typical_p = 1.0
        if xtc_probability == None:
            xtc_probability = 0.0
        if xtc_threshold == None:
            xtc_threshold = 0.1
        if dry_multiplier == None:
            dry_multiplier = 0.0
        if dry_allowed_length == None:
            dry_allowed_length = 2
        if dry_base == None:
            dry_base = 1.75
        if dry_penalty_last_n == None:
            dry_penalty_last_n = -1
        if dry_seq_breakers == None:
            dry_seq_breakers = []
        if response_prefill == None:
            response_prefill = ""
        if only_thinking == None:
            only_thinking = False
            
        if thinking_prefill == None or thinking_prefill.strip() == "": # If the thinking_prefill is empty, null out the thinking_prefill
            if self.message_formatter.thinking_prefill and self.message_formatter.thinking_prefill.strip() != "":
                thinking_prefill = self.message_formatter.thinking_prefill
            else:
                thinking_prefill = ""

        will_think = thinking and self.message_formatter.thinking

        logging.info("Using Message Formatter:", self.message_formatter)
        prompt = self.message_formatter.get_string_from_messages(messages, thinking=will_think, start_message=True, response_type=response_type)
        # prompt += self.message_formatter.start_message(response_type, thinking=will_think)
        # print("Prompt:",prompt)
        token_length = len(self.llama.tokenize(prompt.encode("utf-8"))) # Tokenize with currently loaded model to figure out if we need to load a new model

        print("Using sampling options: temperature",temperature,"top_p",top_p,"top_k",top_k,"min_p",min_p,"repeat_penalty",repeat_penalty,"frequency_penalty",frequency_penalty,"presence_penalty",presence_penalty,"typical_p",typical_p,"xtc_probability",xtc_probability,"xtc_threshold",xtc_threshold,"dry_multiplier",dry_multiplier,"dry_allowed_length",dry_allowed_length,"dry_base",dry_base,"dry_penalty_last_n",dry_penalty_last_n,"dry_seq_breakers",dry_seq_breakers)
        if will_think and thinking_prefill and thinking_prefill.strip() != "":
            prompt += thinking_prefill
            print("Prompt after thinking prefill:",prompt)
        elif not will_think and response_prefill and response_prefill.strip() != "":
            prompt += response_prefill
            print("Prompt after response prefill:",prompt)
        # print(f"Prompt:")
        # print(prompt)
        # with open("debug_prompt_1.txt","w",encoding="utf-8") as f:
        #     f.write(prompt)
        
        if grammar:
            print("Legacy grammar format detected")
            if type(grammar) == dict:
                response_grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(grammar))
            elif type(grammar) == str:
                response_grammar = llama_cpp.LlamaGrammar.from_string(grammar)
        elif response_grammar:
            print("Response grammar detected")
            if type(response_grammar) == dict:
                response_grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(response_grammar))
            elif type(response_grammar) == str:
                response_grammar = llama_cpp.LlamaGrammar.from_string(response_grammar)
        elif response_format and type(response_format) != None:
            print("OpenRouter style response_format detected")
            if type(response_format.json_schema) == dict:
                response_grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(response_format.json_schema))
            elif type(response_format.json_schema) == str:
                response_grammar = llama_cpp.LlamaGrammar.from_string(response_format.json_schema)
            else:
                print("Error: Grammar is not a valid type")
            # if body.response_format.type == "json_schema":
            #     grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(body.response_format.json_schema))
        else:
            response_grammar = None
        print("Response Grammar:",response_grammar)

        if thinking_grammar and will_think:
            print("Thinking grammar detected")
            if type(thinking_grammar) == dict:
                thinking_grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(thinking_grammar))
            elif type(thinking_grammar) == str:
                thinking_grammar = llama_cpp.LlamaGrammar.from_string(thinking_grammar)
            else:
                print("Error: Thinking grammar is not a valid type")
                thinking_grammar = None
        else:
            thinking_grammar = None
        print("Thinking Grammar:",thinking_grammar)
        
        stops = self.message_formatter.stop + stop
        stops = list(set(stops))

        thinking_stops = []
        if thinking_stop:
            thinking_stops.extend(thinking_stop)
        if thinking_stops:
            thinking_stops.extend(thinking_stops)

        if len(thinking_stops) == 0:
            thinking_stops = self.message_formatter.thinking_stops if self.message_formatter.thinking_stops else []
        thinking_stops = list(set(thinking_stops))

        two_step = False
        if will_think:
            if thinking_grammar:
                two_step = True
            if response_grammar:
                two_step = True
            if response_prefill and response_prefill.strip() != "":
                two_step = True
            if len(thinking_stops) > 0:
                two_step = True
            if only_thinking:
                two_step = True

        if two_step:
            print("Two-step response generation enabled")
            stops += [self.message_formatter.start_thinking_token,self.message_formatter.end_thinking_token] # Add the end thinking token to the stops if prefill is used. Stop thinking and add prefill to the response tokens
        print("Stops:",stops)
        keyword_args = dict(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            min_p=min_p,
            repeat_penalty=repeat_penalty,
            frequency_penalty=frequency_penalty,
            present_penalty=presence_penalty,
            typical_p=typical_p,
            xtc_probability=xtc_probability,
            xtc_threshold=xtc_threshold,
            dry_multiplier=dry_multiplier,
            dry_allowed_length=dry_allowed_length,
            dry_base=dry_base,
            dry_penalty_last_n=dry_penalty_last_n,
            dry_seq_breakers=dry_seq_breakers,
            stop=stops,
            stream=True,
        )
        def chat_wrapper():
            start_time = time.time()
            first_token_time = None
            try:
                first_keyword_args = {}
                for key in keyword_args:
                    first_keyword_args[key] = keyword_args[key]
                if will_think:
                    first_keyword_args["grammar"] = thinking_grammar
                    if two_step:
                        if thinking_max_tokens != None and thinking_max_tokens > 0:
                            first_keyword_args["max_tokens"] = thinking_max_tokens
                        if len(thinking_stops) > 0:
                            first_keyword_args["stop"] = first_keyword_args["stop"] + thinking_stops
                else:
                    first_keyword_args["grammar"] = response_grammar
                print(first_keyword_args)
                thoughts = ""
                first_iterator_or_completion = self.llama.create_completion(**first_keyword_args)
                is_thinking = thinking and self.message_formatter.thinking
                first_description = "Generating response"
                if two_step:
                    first_description = "Thinking about response"
                for chunk in tqdm(first_iterator_or_completion, total=thinking_max_tokens, desc=first_description, unit="token"): # , disable=not body.stream
                    if not first_token_time:
                        first_token_time = time.time()
                    chat_completion = {
                        "id": chunk["id"],
                        "object": "chat.completion",
                        "created": chunk["created"],
                        "model": self.model,
                        "choices": [],
                        "thinking_choices": [],
                        "usage": {
                            "time_taken": time.time() - start_time,
                            "time_to_first_token": first_token_time - start_time if first_token_time else "N/A",
                        }
                    }
                    # print(chunk)
                    for choice in chunk["choices"]:
                        if is_thinking and self.message_formatter.end_thinking_token in choice['text']:
                            if two_step:
                                thoughts += choice["text"].split(self.message_formatter.end_thinking_token)[0]
                                break
                        if is_thinking:
                            chat_completion["thinking_choices"].append({
                                "index": choice["index"],
                                "delta": {
                                    "content": choice["text"],
                                    "role": response_type,
                                    "name": ""
                                },
                                "logprobs": choice["logprobs"],
                                "finish_reason": choice["finish_reason"],
                            })
                            chat_completion["choices"].append({
                                "index": choice["index"],
                                "delta": {
                                    "content": "",
                                    "role": "assistant",
                                    "reasoning": choice["text"],
                                    "reasoning_details":[],
                                    "name": ""
                                },
                                "logprobs": choice["logprobs"],
                                "finish_reason": choice["finish_reason"],
                            })
                            if two_step:
                                thoughts += choice["text"]
                        else:
                            chat_completion["choices"].append({
                                "index": choice["index"],
                                "delta": {
                                    "content": choice["text"],
                                    "role": "assistant",
                                    "reasoning": None,
                                    "name": ""
                                },
                                "logprobs": choice["logprobs"],
                                "finish_reason": choice["finish_reason"],
                            })
                    if is_thinking and self.message_formatter.end_thinking_token in chat_completion["thinking_choices"][-1]["delta"]["content"]:
                        is_thinking = False
                        chat_completion["thinking_choices"][-1]["delta"]["content"] = chat_completion["thinking_choices"][-1]["delta"]["content"].replace(self.message_formatter.end_thinking_token, "")
                    # print("Chat completion chunk:", chat_completion)
                    yield chat_completion
                if two_step and not only_thinking:
                    print("Two-step response generation enabled, running second step")
                    second_keyword_args = {}
                    for key in keyword_args:
                        second_keyword_args[key] = keyword_args[key]
                    second_keyword_args["grammar"] = response_grammar
                    second_keyword_args["prompt"] = prompt + thoughts.strip() + self.message_formatter.end_thinking_token + self.message_formatter.thinking_token_suffix
                    if response_prefill and response_prefill.strip() != "":
                        second_keyword_args["prompt"] += response_prefill
                    second_keyword_args["stop"] = stops
                    print(second_keyword_args)
                    second_iterator_or_completion = self.llama.create_completion(**second_keyword_args)
                    for chunk in tqdm(second_iterator_or_completion, total=max_tokens, desc="Generating response", unit="token"): # , disable=not body.stream
                        chat_completion = {
                            "id": chunk["id"],
                            "object": "chat.completion",
                            "created": chunk["created"],
                            "model": self.model,
                            "choices": [],
                            "thinking_choices": [],
                            "usage": {
                                "time_taken": time.time() - start_time,
                                "time_to_first_token": first_token_time - start_time if first_token_time else "N/A",
                            }
                        }
                        for choice in chunk["choices"]: # Second step should only ever be response choices
                            chat_completion["choices"].append({
                                "index": choice["index"],
                                "delta": {
                                    "content": choice["text"],
                                    "role": response_type,
                                    "reasoning": None,
                                    "name": ""
                                },
                                "logprobs": choice["logprobs"],
                                "finish_reason": choice["finish_reason"],
                            })
                        # print("Chat completion chunk:", chat_completion)
                        if self.message_formatter.end_thinking_token in chat_completion["choices"][-1]["delta"]["content"]:
                            is_thinking = False
                            chat_completion["choices"][-1]["delta"]["content"] = chat_completion["choices"][-1]["delta"]["content"].split(self.message_formatter.end_thinking_token)[0]
                        yield chat_completion
                print("Chat completion finished")
            except Exception as e:
                print("Error during chat completion:",e)
                # raise e
            print("Chat wrapper finished")
        # print("Engaging model lock to run completion")
        # print("Inside model lock, running completion")
        iterator_or_completion = chat_wrapper()
        first_response = iterator_or_completion.__next__()  # Get the first response to check if it's an iterator or a completion
        if stream:
            def streaming_response():
                yield first_response
                for chunk in iterator_or_completion:
                    yield chunk
            return streaming_response()
        else:
            start_time = time.time()
            first_token_time = None
            chat_completion = {
                "id": first_response["id"],
                "object": "chat.completion",
                "created": first_response["created"],
                "model": self.model,
                "choices": [],
                "thinking_choices": [],
                "usage": {
                    "prompt_tokens": token_length,
                    "completion_tokens": 1,
                    "total_tokens": token_length+1,
                    "time_taken": time.time() - start_time,
                    "time_to_first_token": first_token_time - start_time if first_token_time else "N/A",
                }
            }
            for i, choice in enumerate(first_response["thinking_choices"]):
                chat_completion["thinking_choices"].append({
                    "index": i,
                    "message": {
                        "content": choice["delta"]["content"],
                        "role": response_type,
                        "name": ""
                    },
                    "logprobs": choice["logprobs"],
                    "finish_reason": choice["finish_reason"],
                })
                chat_completion["choices"].append({
                    "index": i,
                    "message": {
                        "content": "",
                        "role": "assistant",
                        "reasoning": choice["delta"]["content"],
                        "reasoning_details":[],
                        "name": ""
                    },
                    "logprobs": choice["logprobs"],
                    "finish_reason": choice["finish_reason"],
                })
            for i, choice in enumerate(first_response["choices"]):
                chat_completion["choices"].append({
                    "index": i,
                    "message": {
                        "content": choice["delta"]["content"],
                        "role": response_type,
                        "reasoning": None,
                        "name": ""
                    },
                    "logprobs": choice["logprobs"],
                    "finish_reason": choice["finish_reason"],
                })
            # print("Processing chat completion chunks",chat_completion)
            for chunk in iterator_or_completion:
                for i, choice in enumerate(chunk["thinking_choices"]):
                    if len(chat_completion["thinking_choices"]) < i+1:
                        chat_completion["thinking_choices"].append({
                            "index": i,
                            "message": {
                                "content": choice["delta"]["content"],
                                "role": response_type,
                                "name": ""
                            },
                            "logprobs": choice["logprobs"],
                            "finish_reason": choice["finish_reason"],
                        })
                        chat_completion["choices"].append({
                            "index": i,
                            "message": {
                                "content": "",
                                "role": "assistant",
                                "reasoning": choice["delta"]["content"],
                                "reasoning_details":[],
                                "name": ""
                            },
                            "logprobs": choice["logprobs"],
                            "finish_reason": choice["finish_reason"],
                        })
                    else:
                        chat_completion["thinking_choices"][i]["message"]["content"] = chat_completion["thinking_choices"][i]["message"]["content"] + choice["delta"]["content"]
                        chat_completion["thinking_choices"][i]["finish_reason"] = choice["finish_reason"]
                        chat_completion["usage"]["completion_tokens"] += 1
                for i, choice in enumerate(chunk["choices"]):
                    if len(chat_completion["choices"]) < i+1:
                        chat_completion["choices"].append({
                            "index": i,
                            "message": {
                                "content": choice["delta"]["content"],
                                "role": response_type,
                                "reasoning": None,
                                "name": ""
                            },
                            "logprobs": choice["logprobs"],
                            "finish_reason": choice["finish_reason"],
                        })
                    else:
                        chat_completion["choices"][i]["message"]["content"] = chat_completion["choices"][i]["message"]["content"] + choice["delta"]["content"]
                        chat_completion["choices"][i]["finish_reason"] = choice["finish_reason"]
                        chat_completion["usage"]["completion_tokens"] += 1
            print("Final chat completion:", chat_completion)
            return chat_completion
        
    def tokenize(self,
        text: str,
        add_bos: bool = False,
        special: bool = False,
    ) -> list[int]:
        return self.llama.tokenize(text.encode("utf-8"), add_bos=add_bos, special=special)

model_dir = os.path.join(os.getcwd(), "data", "models", "gguf")
os.makedirs(model_dir, exist_ok=True)
llama_model = None # Used to store the llama-cpp-python model so it can be reused for the tokenizer

inference_engine_name = "llama_cpp_python"
inference_engine_title = "llama-cpp-python"
tokenizer_slug = "llama_cpp_python" # This slug is effectively unused but it is here for consistency with other inference engines
default_settings = {
    "llama_cpp_python_use_huggingface_hub": True,
    "llama_cpp_python_huggingface_slug": None, # "unsloth/gemma-4-E4B-it-GGUF",
    "llama_cpp_python_huggingface_filename": None, # "gemma-4-E4B-it-IQ4_NL.gguf",
    "llama_cpp_python_model_path": None, # "./data/models/gguf/gemma-4-E4B-it-IQ4_NL.gguf",
    # "llava_clip_model_path": ".\\clip_model.gguf",
    "llama_cpp_python_n_gpu_layers": None, # 0,
    "llama_cpp_python_n_threads": 4,
    "llama_cpp_python_n_batch": 512,
    "llama_cpp_python_tensor_split": [], # [0.5,0.5] for 2 gpus split evenly, [0.3,0.7] for 2 gpus split unevenly
    "llama_cpp_python_main_gpu": 0,
    "llama_cpp_python_split_mode": 0, # 0 = single gpu, 1 = split layers and kv across gpus, 2 = split rows across gpus
    "llama_cpp_python_use_mmap": True,
    "llama_cpp_python_use_mlock": False,
    "llama_cpp_python_n_threads_batch": 1,
    "llama_cpp_python_offload_kqv": True,
    "llama_cpp_python_thought_infill": True,
    "llama_cpp_python_verbose": False,
}
settings_description = {
    "llama_cpp_python_huggingface_slug": "The HuggingFace slug for the model. This is used to download the model from HuggingFace if 'use_huggingface_hub' is set to True. If you are using a local model, this can be left as the default value.",
    "llama_cpp_python_huggingface_filename": "The filename to use for the model when downloading from HuggingFace. This is used to save the model file when it is downloaded from HuggingFace. If you are using a local model, this can be left as the default value.",
    "llama_cpp_python_model_path": "The path to the model file. This is required for the model to work. If you are using a local model, this should be the path to the model file. If you are using a remote model, this should be the URL to the model file.",
    # "llava_clip_model_path": "The path to the clip model file. This is required for the model to work with vision. If you are using a local model, this should be the path to the model file. If you are using a remote model, this should be the URL to the model file.",
    "llama_cpp_python_n_gpu_layers": "The number of layers to run on the GPU. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "llama_cpp_python_n_threads": "The number of threads to use for the model. This is used to speed up the model inference. If you are using a single GPU, this should be the number of CPU threads you want to use.",
    "llama_cpp_python_n_batch": "The number of tokens to process in a batch. This is used to speed up the model inference. If you are using a single GPU, this should be the number of tokens you want to process in a batch.",
    "llama_cpp_python_tensor_split": "The tensor split to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be an empty list.",
    "llama_cpp_python_main_gpu": "The main GPU to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "llama_cpp_python_split_mode": "The split mode to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "llama_cpp_python_use_mmap": "Whether to use memory-mapped files for the model. This is used to speed up the model inference. If you are using a single GPU, this should be True.",
    "llama_cpp_python_use_mlock": "Whether to use mlock to lock the model in memory. This is used to speed up the model inference. If you are using a single GPU, this should be False.",
    "llama_cpp_python_n_threads_batch": "The number of threads to use for the batch processing. This is used to speed up the model inference. If you are using a single GPU, this should be 1.",
    "llama_cpp_python_offload_kqv": "Whether to offload the key-value pairs to the CPU. This is used to speed up the model inference. If you are using a single GPU, this should be True.",
    "llama_cpp_python_verbose": "Whether to enable verbose logging for llama-cpp-python. This can be useful for debugging issues with the model, but it can also slow down the inference. If you are using a single GPU, this should be False.",
}
options = {
    "main_gpu": [], # The main GPU to use for the model, if using multiple GPUs
    "split_mode": [
        {
            "name": "Single GPU",
            "value": 0,
            "description": "Use a single GPU for the model. This is the default mode and is recommended for most users.",
            "default": True,
            "disabled": False
        },
        {
            "name": "Split Layers and KV across GPUs",
            "value": 1,
            "description": "Split the model layers and key-value pairs across multiple GPUs. This is recommended for users with multiple GPUs and large models.",
            "default": False,
            "disabled": False
        }, 
        {
            "name": "Split Rows across GPUs",
            "value": 2,
            "description": "Split the model rows across multiple GPUs. This is recommended for users with multiple GPUs and large models.",
            "default": False,
            "disabled": False
        }
    ],
}
settings = {}
loaded = False
description = "This inference engine uses llama-cpp-python to run the LLM. It is a high-performance inference engine that supports various models and features. This, and using a compatible model over OpenAI API, is the recommended way to run Pantella. It supports vision and COT (Chain of Thought) reasoning, and can generate characters based on the prompt provided. It also supports multimodal prompts with text and image embeds for NPCs that can see what you see."

if imported:
    if torch.cuda.is_available():
        # add the available GPUs to the main_gpu option
        for i in range(torch.cuda.device_count()):
            gpu_name = torch.cuda.get_device_name(i)
            if gpu_name is None or gpu_name == "":
                gpu_name = f"GPU {i}"
            if i not in [option["value"] for option in options["main_gpu"]]: # Avoid duplicates
                # Add the GPU to the main_gpu option
                if i == 0:
                    description = "Use the first GPU for the model. This is the default GPU and is recommended for most users."
                else:
                    description = f"Use GPU {i} for the model. This is recommended if you have a multi-GPU setup and want to use a specific GPU for the model."
                options["main_gpu"].append({
                    "name": gpu_name,
                    "value": i,
                    "description": description,
                    "default": True if i == 0 else False, # Default to the first GPU
                    "disabled": False
                })
    # If no GPUs are available, disable the main_gpu option
    if len(options["main_gpu"]) == 0:
        options["main_gpu"].append({
            "name": "No GPU",
            "value": -1,
            "description": "No GPU available. The model will run on the CPU.",
            "default": True,
            "disabled": True
        })
        default_settings["main_gpu"] = -1 # Set the main GPU to -1 if no GPUs are available
    # If no GPUs are available, disable the split_mode option
    if len(options["main_gpu"]) == 1 and options["main_gpu"][0]["value"] == -1:
        options["split_mode"] = [
            {
                "name": "No GPU Available",
                "value": 0,
                "description": "No GPU available. The model will run on the CPU. If you do have a compatible GPU, please check that you have installed llama-cpp-python and torch correctly.",
                "default": True,
                "disabled": True
            }
        ]
else:
    logging.warning("llama-cpp-python not imported, skipping GPU detection.")
    
class LLM(base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager, vision_enabled=False):
        global llama_model, inference_engine_name, loaded, default_settings
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
        self.inference_engine_name = inference_engine_name

        def select_gguf_file():
            with root_context_manager as root:
                file_dialog = FileSelectionDialog(root, "Select Model File", "Please select the model file to use for the llama-cpp-python inference engine.\nMake sure to select a compatible model file (gguf format) and set the correct path in the config file if you want to use a custom model.", "Select File", filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")])
            return file_dialog.result
        
        save_config = False

        if self.config.llama_cpp_python_use_huggingface_hub == None:
            self.config.llama_cpp_python_use_huggingface_hub = default_settings["llama_cpp_python_use_huggingface_hub"]
            save_config = True

        if self.config.llama_cpp_python_use_huggingface_hub and (self.config.llama_cpp_python_huggingface_slug is None or self.config.llama_cpp_python_huggingface_filename is None):
            options_list = ["Gemma 4 E2B it", "Gemma 4 E4B it", "Other"]
            with root_context_manager as root:
                popup = OptionDialog(root,
                    "Select Model",
                    "Please select the model to use for the llama-cpp-python inference engine.\nBoth of these models can run usably on CPU without a dedicated GPU,\nbut if you have a compatible GPU, the Gemma 4 E4B it model is recommended for better quality.\nIf you want to use a custom gguf model you already have locally,\nselect 'Other' and make sure to set the correct model path in the config file.\nPlease note that if you're using a custom model, you MUST setup a prompt style for that model.\nThe default chat template is not used like in other inference backends,\nso you need to setup a prompt style with the correct chat template for the model you choose to use.\nIf you don't setup a prompt style, the model will not work correctly.\nIf you need help setting up a prompt style, please refer to the documentation or ask for help in the community Discord.",
                     options_list)
            choice = popup.result
            if choice == "Gemma 4 E2B it":
                self.config.llama_cpp_python_huggingface_slug = "unsloth/gemma-4-E2B-it-GGUF"
                self.config.llama_cpp_python_huggingface_filename = "gemma-4-E2B-it-IQ4_NL.gguf"
                self.config.llama_cpp_python_model_path = os.path.join(model_dir, "gemma-4-E2B-it-IQ4_NL.gguf")
                save_config = True
            elif choice == "Gemma 4 E4B it":
                self.config.llama_cpp_python_huggingface_slug = "unsloth/gemma-4-E4B-it-GGUF"
                self.config.llama_cpp_python_huggingface_filename = "gemma-4-E4B-it-IQ4_NL.gguf"
                self.config.llama_cpp_python_model_path = os.path.join(model_dir, "gemma-4-E4B-it-IQ4_NL.gguf")
                save_config = True
            elif choice == "Other":
                self.config.llama_cpp_python_huggingface_slug = None
                self.config.llama_cpp_python_huggingface_filename = None
                self.config.llama_cpp_python_use_huggingface_hub = False
                # Prompt the user to select a model file using a file dialog
                model_path = select_gguf_file()
                if model_path is not None and model_path != "" and os.path.isfile(model_path):
                    self.config.llama_cpp_python_model_path = model_path
                    save_config = True
                else:
                    logging.error("No model file selected. Please select a model file to use the llama-cpp-python inference engine.")
                    input("Press Enter to exit.")
                    raise ValueError("No model file selected. Please select a model file to use the llama-cpp-python inference engine.")
        elif not self.config.llama_cpp_python_use_huggingface_hub and (self.config.llama_cpp_python_model_path is None or self.config.llama_cpp_python_model_path == ""):
            # Prompt the user to select a model file using a file dialog
            model_path = select_gguf_file()
            if model_path is not None and model_path != "" and os.path.isfile(model_path):
                self.config.llama_cpp_python_model_path = model_path
                save_config = True
            else:
                logging.error("No model file selected. Please select a model file to use the llama-cpp-python inference engine.")
                input("Press Enter to exit.")
                raise ValueError("No model file selected. Please select a model file to use the llama-cpp-python inference engine.")
        
        if self.config.llama_cpp_python_n_gpu_layers is None:
            max_gpu_layers = 0
            if imported and torch.cuda.is_available():
                max_gpu_layers = 99
            with root_context_manager as root:
                n_gpu_layers = SliderDialog(root, "GPU Layers", f"Enter the number of layers to run on the GPU.\nThis is used to offload layers of the model to the GPU for faster inference.\nThe more layers offloaded, the more VRAM is used.\nBigger models will require more VRAM per layer offloaded.\nSet to 0 to use CPU only, set to 99 to fully offload for maximum speed.", from_=0, to=max_gpu_layers, resolution=1)
            self.config.llama_cpp_python_n_gpu_layers = n_gpu_layers.result
            save_config = True

        if save_config:
            self.config.save()

        if not imported:
            logging.error(f"Error loading llama-cpp-python. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            raise ValueError(f"Error loading llama-cpp-python. Please check that you have installed it correctly.")
        if llama_model is None:
            tensor_split = self.config.llama_cpp_python_tensor_split
            if len(tensor_split) == 0:
                tensor_split = None

            kwargs = {
                "n_ctx": self.config.maximum_local_tokens,
                "n_gpu_layers": self.config.llama_cpp_python_n_gpu_layers,
                "n_batch": self.config.llama_cpp_python_n_batch,
                "n_threads": self.config.llama_cpp_python_n_threads,
                "tensor_split": tensor_split,
                "main_gpu": self.config.llama_cpp_python_main_gpu,
                "split_mode": self.config.llama_cpp_python_split_mode,
                "use_mmap": self.config.llama_cpp_python_use_mmap,
                "use_mlock": self.config.llama_cpp_python_use_mlock,
                "n_threads_batch": self.config.llama_cpp_python_n_threads_batch,
                "offload_kqv": self.config.llama_cpp_python_offload_kqv,
                "verbose": self.config.llama_cpp_python_verbose,
            }
            if kwargs['n_gpu_layers'] == 0:
                logging.error(f"No GPUs detected. Removing main_gpu and split_mode options from llama-cpp-python settings. Please check that you have installed torch and llama-cpp-python correctly if you do have a compatible GPU.")
                kwargs.pop("main_gpu", None)
                kwargs.pop("split_mode", None)
            else:
                logging.info(f"GPUs detected: {[option['name'] for option in options['main_gpu'] if not option['disabled']]}. If you have a compatible GPU but it is not detected, please check that you have installed torch and llama-cpp-python correctly.")
            logging.info(f"Loading llama-cpp-python model with the following settings:", kwargs)
            
            message_formatter = MessageFormatter(PromptStyle(**self._prompt_style))

            if self.config.llama_cpp_python_use_huggingface_hub:
                logging.info(f"Downloading model from HuggingFace Hub: {self.config.llama_cpp_python_huggingface_slug}")
                self.llm = LlamaCPP.from_pretrained(
                    repo_id=self.config.llama_cpp_python_huggingface_slug,
                    filename=self.config.llama_cpp_python_huggingface_filename,
                    local_dir=model_dir,
                    cache_dir=model_dir,
                    message_formatter=message_formatter,
                    **kwargs
                )
            else:
                self.llm = LlamaCPP(
                    model_path=self.config.llama_cpp_python_model_path, 
                    message_formatter=message_formatter,
                    **kwargs
                )
            llama_model = self.llm
        else:
            self.llm = llama_model
        logging.info(f"Running Pantella with llama-cpp-python. The language model chosen can be changed via {self.config.config_path}")
        logging.info(f"Testing llama-cpp-python...")
        test_prompt = "Hello, I am a llama-cpp-python test prompt. I am used to test llama-cpp-python's functi"
        test_completion = self.llm.completions(test_prompt, max_tokens=10)
        logging.output(f"Test Completion: {test_completion}")
        text_messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that tries to help the user as much as possible. You will be given a prompt from the user, and you will try to help them with it as much as possible. If you don't know the answer, you will say you don't know. You will not make up answers. You will try to be as helpful as possible."
            },
            {
                "role": "user",
                "content": "What is 2+2?"
            }
        ]
        test_chat_completion = self.llm.chat_completions(messages=text_messages, max_tokens=10)
        logging.output(f"Test Chat Completion: {test_chat_completion}")
        # if self.vision_enabled:
        #     logging.info("Vision is enabled for llama-cpp-python")
        #     if imported:
        #         try:
        #             self.clip_model = clip_model_load(self.config.llava_clip_model_path.encode(), 1)
        #             logging.success(f"Loaded vision model for llama-cpp-python")
        #         except Exception as e:
        #             logging.error(f"Error loading clip model for 'llava-cpp-python'(not a typo) inference engine. Please check that the model path is correct in {self.config.config_path}.")
        #             tb = traceback.format_exc()
        #             logging.error(tb)
        #             input("Press Enter to exit.")
        #             raise e
        #     else:
        #         logging.error(f"Error loading llama-cpp-python for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed llama-cpp-python correctly.")
        #         input("Press Enter to exit.")
        #         raise Exception("Llama-cpp-python not installed, install llama-cpp-python to use llama-cpp-python.")
            
        if self.cot_enabled:
            logging.info("COT is enabled for llama-cpp-python")
            if self.cot_enabled and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(TestCoT.model_json_schema()))
                completion = self.llm.completions("",
                    max_tokens=512,
                    stream=False,
                    grammar=grammar,
                )
                completion = completion["choices"][0]["text"].strip()
                try:
                    response = json.loads(completion)
                    print(response)
                    self.cot_supported = True
                    self.character_generation_supported = True
                    logging.success(f"llama-cpp-python supports CoT!")
                except:
                    self.cot_supported = False
                    logging.error(f"llama-cpp-python encountered an error while testing CoT. GBNF grammars are not supported by your model or your version of llama-cpp-python.")
                    # input("Press Enter to exit.")
        loaded = True

    def generate_character(self, character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard=False, character_is_ghost=False, in_game_voice_model=None, location=None):
        """Generate a character based on the prompt provided"""
        if not self.character_generation_supported:
            logging.error(f"Character generation is not supported by llama-cpp-python. Please check that your model supports it and that it is enabled in {self.config.config_path}.")
            return None
        character_prompt = self.conversation_manager.character_generator_schema.get_prompt(character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, location)

        messages = [
            {
                "role": "system",
                "content": "You are a character generator. You will be given a description of a character to generate. You will then generate a character that matches the description.\nHere are some related references to use when creating your character:",
            },
            {
                "role": "system",
                "content": get_schema_description(self.conversation_manager.character_generator_schema.model_json_schema())
            },
            {
                "role": "user",
                "content": character_prompt
            }
        ]
        logging.info(f"Messages:", messages)
        json_schema = self.conversation_manager.character_generator_schema.model_json_schema()
        grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(json_schema))
        character = None
        tries = 5
        while character is None and tries > 0:
            try:
                completion = self.llm.chat_completions(messages=messages,
                    max_tokens=self.max_tokens,
                    top_k=self.top_k,
                    top_p=self.top_p,
                    min_p=self.min_p,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty, 
                    stop=self.stop,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                    stream=False,
                    thinking=self.thinking,
                    grammar=grammar,
                )
                completion = completion["choices"][0]["text"]
                response = json.loads(completion)
                character = self.conversation_manager.character_generator_schema(**response)
            except Exception as e:
                logging.error(f"Error generating character:", e)
                tries -= 1
        
        voice_model = in_game_voice_model
        if self.config.override_voice_model_with_simple_predictions and voice_model is None:
            # Predict the voice model - If these are available for a character, use them because they're probably more accurate. Though, they're not always available, and sometimes you might prefer to use the voice model from the character generator.
            simple_predictions = [
                "FemaleArgonian",
                "FemaleDarkElf",
                "FemaleKhajiit",
                "FemaleNord",
                "FemaleOrc",
                "MaleArgonian",
                "MaleDarkElf",
                "MaleKhajiit",
                "MaleNord",
                "MaleOrc",
            ]
            if character_in_game_gender+character_in_game_race in simple_predictions:
                voice_model = character_in_game_gender+character_in_game_race

        if voice_model is not None:
            character.voice_model = voice_model

        return character.get_chracter_info(character_ref_id, character_base_id, voice_model)
    
    # def get_image_embed_from_bytes(self, image_bytes):
    #     data_array = array.array("B", image_bytes)
    #     c_ubyte_ptr = (
    #         ctypes.c_ubyte * len(data_array)
    #     ).from_buffer(data_array)
    #     embed = (
    #         llava_image_embed_make_with_bytes(
    #             ctx_clip=self.clip_model,
    #             n_threads=self.config.n_threads,
    #             image_bytes=c_ubyte_ptr,
    #             image_bytes_length=len(image_bytes),
    #         )
    #     )
    #     return embed
    
    def get_image_embed_from_url(self, url):
        image_bytes = load_image(url)
        return self.get_image_embed_from_bytes(image_bytes)

    def get_image_embed_from_file(self, path):
        with open(path, "rb") as f:
            image_bytes = f.read()
        return self.get_image_embed_from_bytes(image_bytes)

    def get_image_embed_from_PIL(self, image):
        image_bytes = image.tobytes()
        return self.get_image_embed_from_bytes(image_bytes)

    # def eval_image_embed(self, embed):
    #     try:
    #         n_past = ctypes.c_int(self.llm.n_tokens)
    #         n_past_p = ctypes.pointer(n_past)
            
    #         llava_eval_image_embed(
    #             ctx_llama=self.llm.ctx,
    #             embed=embed,
    #             n_batch=self.llm.n_batch,
    #             n_past=n_past_p,
    #         )
    #         assert self.llm.n_ctx() >= n_past.value
    #         self.llm.n_tokens = n_past.value
    #     except Exception as e:
    #         print(e)
    #         print("Failed to eval image")
    #     finally:
    #         llava_image_embed_free(embed)
            
    def multimodal_eval(self, text, embeds): # -> prompt
        """Evaluates a multimodal prompt with text and image embeds. The text is split by "{image}" and the image embeds are inserted in the order they appear in the text. The text is then tokenized and the image embeds are evaluated in the model. The input_ids are then returned."""
        assert len(embeds) > 0
        assert type(text) == str
        assert type(embeds) == list
        
        text_chunks = text.split("{image}")
        assert len(text_chunks) == len(embeds) + 1
        text_chunks = [chunk.encode("utf8") for chunk in text_chunks]

        self.llm.reset() # Reset the model
        # clear the input_ids
        self.llm.input_ids = np.ndarray((self.llm.n_ctx(),), dtype=np.intc)
        # print(text_chunks)
        for i, chunk in enumerate(text_chunks):
            self.llm.eval(self.llm.tokenize(chunk, add_bos=True if i == 0 else False))
            if i < len(embeds):
                self.eval_image_embed(embeds[i])
        return self.llm.input_ids[: self.llm.n_tokens].tolist()
    
    def get_player_perspective(self, check_vision=False):
        _, frame, ascii_block = super().get_player_perspective(check_vision)
        buffered = io.BytesIO() # Don't ask me why this is needed - it just is for some reason.
        frame.save(buffered, format="PNG")
        return self.get_image_embed_from_bytes(buffered.getvalue()), ascii_block

    def multimodal_prompt_format(self, prompt):
        image_embed, ascii_block = self.get_player_perspective()
        if "{ocr}" in prompt:
            prompt = prompt.replace("{ocr}", ascii_block)
        prompt = self.multimodal_eval(prompt, [image_embed])
        return prompt

    @utils.time_it
    def create(self, messages):
        logging.info(f"create - Messages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                if self.vision_enabled:
                    prompt = self.multimodal_prompt_format(prompt)

                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(self.conversation_manager.thought_process.model_json_schema()))
                    completion = self.llm.chat_completions(messages=messages,
                        max_tokens=self.max_tokens,
                        top_k=self.top_k,
                        top_p=self.top_p,
                        min_p=self.min_p,
                        temperature=self.temperature,
                        repeat_penalty=self.repeat_penalty, 
                        stop=self.stop,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                        stream=False,
                        thinking=self.thinking,
                        grammar=grammar,
                    )
                else:
                    completion = self.llm.chat_completions(messages=messages,
                        max_tokens=self.max_tokens,
                        top_k=self.top_k,
                        top_p=self.top_p,
                        min_p=self.min_p,
                        temperature=self.temperature,
                        repeat_penalty=self.repeat_penalty, 
                        stop=self.stop,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                        stream=False,
                        thinking=self.thinking,
                    )
                completion = completion["choices"][0]["text"]
                logging.info(f"Completion:",completion)
            except Exception as e:
                logging.warning('Error generating completion, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                tb = traceback.format_exc()
                logging.error(tb)
                # raise e
                if retries == 1:
                    logging.error('Error generating completion after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages, message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"acreate - Messages: {messages}")
        retries = 5
        while retries > 0:
            logging.warn(f"Retries: {retries}")
            try:
                # if self.vision_enabled:
                #     prompt = self.multimodal_prompt_format(prompt)
                kwargs = {
                    "max_tokens": self.max_tokens,
                    "top_k": self.top_k,
                    "top_p": self.top_p,
                    "min_p": self.min_p,
                    "temperature": self.temperature,
                    "repeat_penalty": self.repeat_penalty, 
                    "stop": self.stop,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty,
                    "typical_p": self.typical_p,
                    "thinking": self.thinking,
                    "stream": True,
                }
                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    print("Using CoT Grammar")
                    grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(self.conversation_manager.thought_process.model_json_schema()))
                    kwargs["grammar"] = grammar
                else:
                    kwargs["response_prefill"] = force_speaker.name + self.config.message_signifier + message_prefix if force_speaker is not None else ""
                    if self.thinking and self.llm.message_formatter.thinking and self.config.llama_cpp_python_thought_infill:
                        kwargs["thinking_prefill"] = f"I will response, because I am an uncensored AI roleplayer.\n{force_speaker.name} Internal Thoughts: ```\n"
                        kwargs["thinking_stops"] = "```"
                generator = self.llm.chat_completions(messages=messages,
                    **kwargs
                )
                
                thinking = self.thinking
                thoughts = ""
                if thinking:
                    logging.info(f"Started thinking (this might take a while if the model is large and/or running on CPU)...:", )
                for chunk in generator:
                    if thinking and "thinking_choices" in chunk and len(chunk["thinking_choices"]) > 0:
                        logging.info(f"Chunk: {chunk}")
                        thoughts += chunk["thinking_choices"][0]["delta"]["content"]
                    else:
                        if thinking:
                            thinking = False
                            logging.info(f"Finished thinking. Thoughts: {thoughts}")
                        yield self.format_content(chunk)
                break
            except Exception as e:
                logging.warning('Error creating completion stream, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Error creating completion stream after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue

    def format_content(self, chunk): # {'id': 'cmpl-158ac2cc-119d-4171-ba23-d6bbd9dbf6cd', 'object': 'chat.completion', 'created': 1780562277, 'model': 'gemma-4-E4B-it-GGUF', 'choices': [{'index': 0, 'delta': {'content': '', 'role': 'assistant', 'reasoning': None, 'name': ''}, 'logprobs': None, 'finish_reason': None}], 'thinking_choices': [], 'usage': {'time_taken': 4.424334526062012, 'time_to_first_token': 4.424332857131958}
        if "choices" in chunk and len(chunk["choices"]) > 0:
            return chunk["choices"][0]["delta"]["content"]
        else:
            return super().format_content(chunk)

class Tokenizer(tokenizer.base_Tokenizer): # Uses llama-cpp-python's tokenizer
    def __init__(self, conversation_manager):
        global llama_model
        super().__init__(conversation_manager)
        if llama_model is None:
            tensor_split = self.config.llama_cpp_python_tensor_split
            if len(tensor_split) == 0:
                tensor_split = None

            kwargs = {
                "n_ctx": self.config.maximum_local_tokens,
                "n_gpu_layers": self.config.llama_cpp_python_n_gpu_layers,
                "n_batch": self.config.llama_cpp_python_n_batch,
                "n_threads": self.config.llama_cpp_python_n_threads,
                "tensor_split": tensor_split,
                "main_gpu": self.config.llama_cpp_python_main_gpu,
                "split_mode": self.config.llama_cpp_python_split_mode,
                "use_mmap": self.config.llama_cpp_python_use_mmap,
                "use_mlock": self.config.llama_cpp_python_use_mlock,
                "n_threads_batch": self.config.llama_cpp_python_n_threads_batch,
                "offload_kqv": self.config.llama_cpp_python_offload_kqv,
                "verbose": self.config.llama_cpp_python_verbose,
            }
            if kwargs['n_gpu_layers'] == 0:
                logging.error(f"No GPUs detected. Removing main_gpu and split_mode options from llama-cpp-python settings. Please check that you have installed torch and llama-cpp-python correctly if you do have a compatible GPU.")
                kwargs.pop("main_gpu", None)
                kwargs.pop("split_mode", None)
            else:
                logging.info(f"GPUs detected: {[option['name'] for option in options['main_gpu'] if not option['disabled']]}. If you have a compatible GPU but it is not detected, please check that you have installed torch and llama-cpp-python correctly.")
            logging.info(f"Loading llama-cpp-python model with the following settings:", kwargs)
            
            if self.config.llama_cpp_python_use_huggingface_hub:
                logging.info(f"Downloading model from HuggingFace Hub: {self.config.llama_cpp_python_huggingface_slug}")
                llama_model = LlamaCPP.from_pretrained(
                    repo_id=self.config.llama_cpp_python_huggingface_slug,
                    filename=self.config.llama_cpp_python_huggingface_filename,
                    local_dir=model_dir,
                    cache_dir=model_dir,
                    **kwargs
                )
            else:
                llama_model = LlamaCPP(
                    model_path=self.config.llama_cpp_python_model_path, 
                    **kwargs
                )
        else:
            self.llm = llama_model
            
    @utils.time_it
    def get_token_count(self, string):
        # logging.info(f"Tokenizer.get_token_count() called with string: {string}")
        tokens = self.llm.tokenize(f"{string}")
        return len(tokens)