import logging
import time

from openai.types.shared import Reasoning
from agents import Agent, ModelSettings, Runner, function_tool

from app.utils.llm_helper import llm_get_embedding, llm_classify
from app.utils.srch_helper import srch_search_hybrid
from app.utils.prompts import chatbot_prompt
from app.schemas.chat_schema import ChatResponseModel


@function_tool
def get_aisearch_results(query: str):
    """Fetch 5 knowledge documents.

    Args:
        query: The query used to conduct vector similarity search
    """
    # Generate embedding
    query_embedding = llm_get_embedding(query)

    # AI search
    doc_dict_list = srch_search_hybrid(
        query=query,
        query_embedding=query_embedding,
        top=5,
        select=['blog', 'url', 'title', 'published_date', 'content'],
        filter=None
    )

    query_with_docs = str({
        'retrieved_documents': doc_dict_list,
        'user_query': query
    })

    return query_with_docs

def format_response(chat_response_dict):
    answer = chat_response_dict["answer"]
    refs = chat_response_dict.get("reference_list", [])

    lines = [answer, "", "reference:"]
    for ref in refs:
        citation = ref["citation_num"]
        blog = ref["blog"]
        title = ref["title"]
        url = ref["url"]
        lines.append(f"- [{citation}]<{blog}><{title}><{url}>")

    result_str = "\n".join(lines)
    return result_str

def get_final_completion(history_message_chain, query_with_docs):
    chat_response_dict = llm_classify(history_message_chain, chatbot_prompt, ChatResponseModel, query_with_docs)
    final_completion_text = format_response(chat_response_dict)

    return final_completion_text

# Agent testing
chat_agent = Agent(
    name='Chat Agent',
    model='gpt-5.1',
    model_settings=ModelSettings(
        reasoning=Reasoning(effort='medium'),
        verbosity='medium'
    ),
    instructions=chatbot_prompt,
    output_type=ChatResponseModel,
    tools=[get_aisearch_results],
)

def get_final_completion_agent(history_message_chain, query: str):
    query_with_history = history_message_chain + [{"role": "user", "content": query}]
    response = Runner.run_sync(chat_agent, query_with_history, max_turns=5)

    trace = response.to_input_list()
    logging.warning(trace)

    chat_response_dict = response.final_output.model_dump()
    final_completion_text = format_response(chat_response_dict)

    return final_completion_text