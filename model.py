from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
import os
import glob
import json

# JSON 데이터 로드 함수
def load_all_chunks(folder_path):
    """Load pre-chunked JSON data from a specified folder."""
    all_chunks = []
    try:
        for file_path in glob.glob(os.path.join(folder_path, "*.json")):
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                if "content" in data:
                    chunk = {"content": data["content"], "source": file_path}
                    all_chunks.append(chunk)
    except Exception as e:
        print(f"JSON 파일 로드 중 오류 발생: {e}")
    return all_chunks

# FAISS 벡터스토어 및 리트리버 설정 함수
def setup_vector_store(data_folder, index_save_path, embedding_model="text-embedding-ada-002", api_key=None):
    """Set up FAISS vector store from pre-chunked data."""
    os.makedirs(os.path.dirname(index_save_path), exist_ok=True)  # Ensure directory exists

    # 문서 로드 및 변환
    documents = []
    for chunk in load_all_chunks(data_folder):
        content = chunk.get("content", "")
        metadata = {"source": chunk.get("source", "unknown")}
        documents.append(Document(page_content=content, metadata=metadata))

    if not documents:
        raise ValueError("로드된 문서가 없습니다. 데이터 폴더를 확인하세요.")

    # 임베딩 생성 및 FAISS 벡터스토어 구축
    embeddings = OpenAIEmbeddings(model=embedding_model, openai_api_key=api_key)
    vectorstore = FAISS.from_documents(documents, embeddings)

    # FAISS 벡터스토어 저장
    vectorstore.save_local(index_save_path)
    return vectorstore

# FAISS 벡터스토어 및 리트리버 로드
index_path = "./data/vectorstore/faiss_index"
chunks_folder = "./data/chunks/"

# 프롬프트 데이터 로드 함수
def load_prompt(file_path):
    """Load the prompt text from a specified file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"프롬프트 파일 로드 중 오류 발생: {e}")
        return None

# 프롬프트 데이터 로드
prompt_path = "data/prompts/prompt.txt"
prompt_text = load_prompt(prompt_path)
if not prompt_text:
    print("prompt를 불러오지 못했습니다.")
