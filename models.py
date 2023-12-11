import os

OPENAI_MODELS = ["gpt-3.5-turbo", "gpt-4", "gpt-4-1106-preview"]
REPLICATE_MODELS = ["llama2_70b", "llama2_13b", "llama2_7b", "gpt-2-xl", "gpt-2-large", "airoboros", "spicyboros",
                    "falcon"]
ANTHROPIC_MODELS = ["claude2"]
AVAILABLE_MODELS = OPENAI_MODELS + REPLICATE_MODELS + ANTHROPIC_MODELS

REPLICATE_LINKS = {
    "llama2_70b": "meta/llama-2-70b-chat:35042c9a33ac8fd5e29e27fb3197f33aa483f72c2ce3b0b9d201155c7fd2a287"}


def check_model_exists(model_name):
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Model {model_name} is not available. Available models are {AVAILABLE_MODELS}.")


def load_api_links(model_list):
    openai_api_token = replicate_api_token = anthropic_api_token = None
    api_links = {}
    for model_name in model_list:
        model_name = model_name.lower()
        if model_name not in AVAILABLE_MODELS:
            raise Exception(f"{model_name} not in available models. Please choose from: {AVAILABLE_MODELS}")
        # First checking environment variables
        if model_name in OPENAI_MODELS:
            openai_api_token = os.environ.get("OPENAI_API_TOKEN")
            if not openai_api_token:
                raise Exception(
                    f"OpenAI model {model_name} specified but no OpenAI API Token found in env var OPENAI_API_TOKEN")
            api_links[model_name] = "openai"
        if model_name in REPLICATE_MODELS:
            replicate_api_token = os.environ.get("REPLICATE_API_TOKEN")
            if not replicate_api_token:
                raise Exception(
                    f"Replicate model {model_name} specified but no Replicate API Token found in env var REPLICATE_API_TOKEN")
            api_links[model_name] = REPLICATE_LINKS[model_name]
        if model_name in ANTHROPIC_MODELS:
            anthropic_api_token = os.environ.get("ANTHROPIC_API_TOKEN")
            if not anthropic_api_token:
                raise Exception(
                    f"Anthropic model {model_name} specified but no Anthropic API Token found in env var ANTHROPIC_API_TOKEN")
            api_links[model_name] = "anthropic"
    return api_links
