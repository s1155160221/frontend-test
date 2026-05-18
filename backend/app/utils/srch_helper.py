from azure.search.documents.models import VectorizedQuery, QueryType

from .clients import srch_client

def srch_search_hybrid(query: str, query_embedding: str, top: int, select: list, filter: str):
    doc_dict_list = []

    vector_query = VectorizedQuery(
        vector=query_embedding,
        fields="vector",
        exhaustive=False,
    )

    search_results = srch_client.search(
        search_text=query,
        vector_queries=[vector_query],
        top=top,
        select=select,
        filter=filter,
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="semantic-config-cy-dev-001" # For QueryType.SEMANTIC
    )
    for doc in search_results:
        doc_dict_list.append(dict(doc))
    return doc_dict_list

def srch_index_upload_docs(docs: list):
    srch_client.upload_documents(docs)

def srch_index_delete_docs(docs: list):
    srch_client.delete_documents([{"id": doc['id']} for doc in docs])