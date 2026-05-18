import time
import json
import base64

from .clients import oai_client


def get_b64_url(input_path: str):
    with open(input_path, "rb") as img_file:
        b64_img = base64.b64encode(img_file.read()).decode("utf-8")
    return f"data:image/png;base64,{b64_img}"

# Base call
def llm_get_embedding(text: str):
    response = oai_client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding

def llm_get_completion(message_chain: list):
    response = oai_client.chat.completions.create(
        model="gpt-5",
        messages=message_chain,
        reasoning_effort="low",
    )
    completion_text = response.choices[0].message.content
    return completion_text

def llm_get_completion_parse(response_format, message_chain: list):
    response = oai_client.chat.completions.parse(
        model="gpt-5",
        messages=message_chain,
        reasoning_effort="low",
        response_format=response_format
    )
    completion_text = response.choices[0].message.parsed
    return completion_text

# Classification
def llm_classify(history_message_chain: list, sys_msg: str, response_format, extracted_text: str):
    message_chain = []
    message_chain.extend(history_message_chain)

    message_chain.append({'role':'system', 'content': sys_msg})
    message_chain.append({'role':'user', 'content': extracted_text})

    classified_dict = llm_get_completion_parse(response_format, message_chain)
    classified_dict = classified_dict.model_dump()
    return classified_dict

def llm_classify_img(sys_msg: str, response_format, extracted_text: str, img_list: list, img_type: str = "url"):
    image_url_object_list = []
    if img_list:
        if img_type == "url":
            image_url_object_list = [{"type": "image_url", "image_url": f"{url}"} for url in img_list]
        elif img_type == "path":
            image_url_object_list = [{"type": "image_url", "image_url": f"{get_b64_url(path)}"} for path in img_list]
        else:
            raise ValueError(f"Does not support img_type: {img_type}")
    query = [
        {"type": "text", "text": extracted_text},
        *image_url_object_list
    ]
    
    message_chain = [{'role':'system', 'content': sys_msg}]
    message_chain.append({'role':'user', 'content': query})

    classified_dict = llm_get_completion_parse(response_format, message_chain)
    classified_dict = classified_dict.model_dump()
    return classified_dict