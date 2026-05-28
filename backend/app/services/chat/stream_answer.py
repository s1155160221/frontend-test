import logging
import time

from openai.types.shared import Reasoning
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, ModelSettings, Runner, function_tool

from app.utils.llm_helper import llm_get_embedding, llm_classify
from app.utils.srch_helper import srch_search_hybrid
from app.utils.prompts import chatbot_prompt
from app.schemas.chat_schema import ChatResponseModel


# Agent testing
chat_agent = Agent(
    name='Chat Agent',
    model='gpt-5.1',
    model_settings=ModelSettings(
        reasoning=Reasoning(effort='medium'),
        verbosity='medium'
    ),
    instructions=chatbot_prompt,
    output_type=ChatResponseModel
)


async def run_streaming_chat_core(query: str, event_callback) -> dict:
    """
    Core streaming logic:
      - Talks to OpenAI (or your pipeline) with stream=True.
      - For each chunk, calls event_callback({"type": ..., "payload": {...}}).
      - Returns ai_data dict at the end.
    """
    stream_response = Runner.run_streamed(chat_agent, input=query)

    # Streaming
    async for event in stream_response.stream_events():
        # Answer delta
        if event.type == 'raw_response_event' and isinstance(event.data, ResponseTextDeltaEvent):
            await event_callback(event_type='answer_delta', event_data={'delta': event.data.delta})

        # Agent updated
        elif event.type == 'agent_updated_stream_event':
            await event_callback(event_type='agent_updated', event_data={'agent_name': event.new_agent.name})

        # Tool call
        elif event.type == 'run_item_stream_event':
            if event.name == 'tool_called':
                await event_callback(event_type='tool_called', event_data={'tool_name': event.item.raw_item.name, 'tool_args': event.item.raw_item.arguments})
            elif event.name == 'tool_output':
                await event_callback(event_type='tool_output', event_data={'tool_output': event.item.raw_item['output']})
    
    # Post-streaming
    final_answer = stream_response.final_output
    conversation_history = stream_response.to_input_list()
    token_usage = {
        'input_tokens': stream_response.context_wrapper.usage.input_tokens,
        'output_tokens': stream_response.context_wrapper.usage.output_tokens,
        'total_tokens': stream_response.context_wrapper.usage.total_tokens
    }

    data_dict = {
        'final_answer': final_answer,
        'conversation_history': conversation_history,
        'token_usage': token_usage
    }
    return {"success": True, "data": data_dict}