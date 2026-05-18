from openai.types.responses import ResponseTextDeltaEvent
from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled, function_tool
from agents.mcp import MCPServerStreamableHttp
from agents.result import RunResultStreaming

from .clients import oai_client


# Config
set_default_openai_client(client=oai_client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)

# MCPs
mcp_config_list = [
    #{'name': "test_server", 'url': "http://127.0.0.1:8000/mcp"}
]

def get_mcp_objects():
    mcp_objects = [
        MCPServerStreamableHttp(
            name=server['name'],
            cache_tools_list=True,
            params={
                "url": server['url']
            }
        )
        for server in mcp_config_list
    ]
    return mcp_objects

# Standard Response Generator
async def response_generator(response: RunResultStreaming):
    async for event in response.stream_events():
        #yield "stream", (str(event) + "\n\n")
        
        # Raw events from LLM
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            yield "stream", (str(event.data.delta) + "\n\n")
        # Current agent changes
        elif event.type == "agent_updated_stream_event":
            print(f"> Current Agent: {event.new_agent.name}")
        # Higher-level events
        elif event.type == "run_item_stream_event":
            if event.name == "tool_called":
                print(f"> Tool Called, name: {event.item.raw_item.name}, args: {event.item.raw_item.arguments}")
            elif event.name == "tool_output":
                print(f"> Tool Output output: {event.item.raw_item['output']}")

    # Post-streaming
    final_answer = response.final_output
    conversation_history = response.to_input_list()
    token_usage = {
        'input_tokens': response.context_wrapper.usage.input_tokens,
        'output_tokens': response.context_wrapper.usage.output_tokens,
        'total_tokens': response.context_wrapper.usage.total_tokens
    }

    yield "end", (final_answer, conversation_history, token_usage)