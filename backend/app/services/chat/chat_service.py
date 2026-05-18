from .answer import get_aisearch_results, get_final_completion, get_final_completion_agent


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