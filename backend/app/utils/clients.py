import logging
import time

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import OpenAI, AsyncOpenAI
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled

from .env_vars import *


# Setup clients
# Azure OpenAI
oai_client = OpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)

# Openai Agents Config
agents_client = AsyncOpenAI(
    base_url=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY
)
set_default_openai_client(client=agents_client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)

# Azure AI Search
srch_client = SearchClient(
    endpoint=AZURE_AISEARCH_ENDPOINT,
    index_name=f"idx-yiklung",
    credential=AzureKeyCredential(AZURE_AISEARCH_KEY)
    #credential=get_credential_aisearch(),
)