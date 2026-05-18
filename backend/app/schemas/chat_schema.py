from typing import Union, Optional
from pydantic import BaseModel, Field


# PO (Walmart)
class ReferenceItemModel(BaseModel):
    citation_num: int = Field(description="assign citation numbers starting from 1 to documents used, do not skip numbers")
    url: str = Field(description="url of the referenced document")
    blog: str = Field(description="blog of the referenced document")
    title: str = Field(description="title of the referenced document")
    published_date: float = Field(description="published_date of the referenced document")

class ChatResponseModel(BaseModel):
    answer: str
    reference_list: list[ReferenceItemModel] = Field(
        default=None,
        description="Return Null/empty object if no reference is used"
    )