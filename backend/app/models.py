from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(pattern=r"^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=20000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=50)
    use_kb: bool = True


class DocumentInfo(BaseModel):
    doc_id: str
    doc_name: str
