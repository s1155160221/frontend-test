from .answer import get_aisearch_results, get_final_completion, get_final_completion_agent
from .stream_answer import run_streaming_chat_core


class ChatService:
    def __init__(self):
        self.history_message_chain = []

    """def answer(self, payload):
        query = payload.get("question", "")

        query_with_docs = get_aisearch_results(query)

        final_completion_text = get_final_completion(self.history_message_chain, query_with_docs)

        # Update history
        self.history_message_chain.append({'role': 'user', 'content': query})
        self.history_message_chain.append({'role': 'assistant', 'content': final_completion_text})
        
        return final_completion_text"""
    
    def answer(self, payload):
        """ Agent Version"""
        query = payload.get("question", "")

        final_completion_text = get_final_completion_agent(self.history_message_chain, query)
        
        # Update history
        self.history_message_chain.append({'role': 'user', 'content': query})
        self.history_message_chain.append({'role': 'assistant', 'content': final_completion_text})
        
        return final_completion_text
    
    def history_get(self):
        return self.history_message_chain

    def history_clear(self):
        self.history_message_chain = []
        return self.history_message_chain
    
    async def stream_answer(self, payload, publish):
        """
        High-level streaming pipeline:
          - Validates payload
          - Delegates to run_streaming_core
          - Aggregates tokens and emits final events
        """
        query = payload.get('question', "")

        # CHAT CORE STARTS -------------------------------------------------------------------------
        delta_list: list[str] = []

        async def chat_core_event_handler(event_type: str, event_data: dict):
            """
            Interpret core events and translate them into publish() calls.
            """
            if event_type == 'answer_delta':
                delta_list.append(event_data.get('delta', ""))
                await publish('answer_delta', event_data, status="Processing")

            elif event_type == 'agent_updated':
                await publish('agent_updated', event_data, status="Processing")

            elif event_type == "tool_called":
                await publish("tool_called", event_data, status="Processing")

            elif event_type == "tool_output":
                await publish("tool_output", event_data, status="Processing")

        chat_core_final_response = await run_streaming_chat_core(query, chat_core_event_handler)

        # After streaming tokens, finalize
        if not chat_core_final_response.get("success"):
            msg = chat_core_final_response.get("message", "AI service returned an error")
            await publish("error", {"message": msg, "status": 500}, status="Failed")
            return
        
        # Success
        data_dict = chat_core_final_response.get('data', {})
        final_answer = data_dict.get('final_answer', "")
        if not final_answer and delta_list:
            final_answer = "".join(delta_list)

        await publish("answer", {"answer": final_answer}, status="Processing")
        # CHAT CORE ENDS -------------------------------------------------------------------------

        
        # Other Chat related steps (traces)
        traces = []

        await publish("traces", {"traces": traces}, status="Processing")