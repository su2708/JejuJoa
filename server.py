from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Dict
from fastapi import FastAPI
from model import setup_vector_store, load_prompt
import os

# FAISS 벡터스토어와 전처리된 문서 위치
index_path = "./data/vectorstore/faiss_index"
chunks_folder = "./data/chunks/"
faiss_file = f"{index_path}.faiss"
pkl_file = f"{index_path}.pkl"

# 프롬프트 데이터 로드
prompt_path = "data/prompts/prompt.txt"
prompt_text = load_prompt(prompt_path)
if not prompt_text:
    print("prompt를 불러오지 못했습니다.")

# FastAPI 앱 초기화
app = FastAPI()

# 요청 모델 정의
class QueryRequest(BaseModel):
    api_key: str
    question: str
    conversation: List[Dict[str, str]] = Field(default_factory=list)  # default는 빈 배열 

# 응답 생성 함수: 기존 대화 내역을 포함해서 응답 생성 
def generate_response(api_key, question, conversation):   
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=api_key,
    )
    
    # 벡터스토어 생성
    if not (os.path.exists(faiss_file) and os.path.exists(pkl_file)):
        vectorstore = setup_vector_store(chunks_folder, index_path, api_key=api_key)
    else:
        vectorstore = FAISS.load_local(index_path, OpenAIEmbeddings(api_key=api_key))

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    
    relevant_docs = retriever.get_relevant_documents(question)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    max_context_length = 3000  # 검색된 문서의 최대 길이 제한
    context = context[:max_context_length]
    
    # 프롬프트 생성
    messages = [
        {
            "role": "system",
            "content": f"{prompt_text[:1000]}\n\n아래는 리트리버에서 가져온 데이터입니다:\n{context}"
        }
    ]

    # 기존 대화 이력을 메시지에 추가
    
    # conversation의 모든 항목을 messages list의 끝에 추가
    messages.extend(conversation)
    print(messages)
    # 현재 질문 추가
    messages.append({"role": "user", "content": question})

    # LLM에게 메시지 전달
    response = llm(messages)

    answer = response.content

    return answer

# 엔드포인트 정의
@app.post("/ask")
async def ask_question(request: QueryRequest):
    api_key = request.api_key
    question = request.question
    conversation = request.conversation
    answer = generate_response(api_key, question, conversation)
    return {"question": question, "answer": answer}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)