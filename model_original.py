import streamlit as st
from utils import print_messages, StreamHandler
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import ChatMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import Document
import os
import glob
import json
from dotenv import load_dotenv

# Streamlit 페이지 설정
st.set_page_config(page_title="AI 창업 어시스턴트", page_icon="😎")
st.title("😎AI 창업 어시스턴트😎")

# OpenAI API 키 가져오기
OPENAI_API_KEY = ''
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

# Streamlit 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "store" not in st.session_state:
    st.session_state["store"] = dict()

# 사이드바 설정
with st.sidebar:
    session_id = st.text_input("Session Id", value="sample_id")
    clear_btn = st.button("대화기록 초기화")
    if clear_btn:
        st.session_state["messages"] = []
        st.session_state["store"] = dict()

# 대화 기록 출력
print_messages()

# JSON 데이터 로드 함수
# okay
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
        st.error(f"JSON 파일 로드 중 오류 발생: {e}")
    return all_chunks

# FAISS 벡터스토어 및 리트리버 설정 함수
# okay
def setup_vector_store(data_folder, index_save_path, embedding_model="text-embedding-ada-002"):
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
    embeddings = OpenAIEmbeddings(model=embedding_model)
    vectorstore = FAISS.from_documents(documents, embeddings)

    # FAISS 벡터스토어 저장
    vectorstore.save_local(index_save_path)
    return vectorstore

# FAISS 벡터스토어 및 리트리버 로드
index_path = "data/vectorstore/faiss_index"
chunks_folder = "data/chunks/"

if "vectorstore" not in st.session_state:
    # 최초 실행 시 인덱스 파일 확인 및 로드
    faiss_file = f"{index_path}.faiss"
    pkl_file = f"{index_path}.pkl"

    if not (os.path.exists(faiss_file) and os.path.exists(pkl_file)):
        st.info(f"FAISS 인덱스 파일이 없습니다. 새로 생성합니다: {index_path}")
        st.session_state["vectorstore"] = setup_vector_store(chunks_folder, index_path)
    else:
        st.session_state["vectorstore"] = FAISS.load_local(index_path, OpenAIEmbeddings())

retriever = st.session_state["vectorstore"].as_retriever(search_type="similarity", search_kwargs={"k": 5})

# 프롬프트 데이터 로드 함수
def load_prompt(file_path):
    """Load the prompt text from a specified file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        st.error(f"프롬프트 파일 로드 중 오류 발생: {e}")
        return None

# 프롬프트 데이터 로드
prompt_path = "data/prompts/prompt.txt"
prompt_text = load_prompt(prompt_path)
if not prompt_text:
    st.stop()

# 세션 기록을 가져오는 함수
def get_session_history(session_ids: str) -> BaseChatMessageHistory:
    """Retrieve session history or initialize it if not available."""
    if session_ids not in st.session_state["store"]:
        st.session_state["store"][session_ids] = ChatMessageHistory()
    return st.session_state["store"][session_ids]

# 대화 기록 길이 제한 함수
def truncate_messages(messages, max_tokens=6000):
    """Truncate messages to fit within the maximum token limit."""
    current_length = 0
    truncated_messages = []
    for message in reversed(messages):  # 최신 메시지부터 확인
        message_length = len(message.content.split())  # message["content"] 대신 message.content
        if current_length + message_length > max_tokens:
            break
        truncated_messages.insert(0, message)
        current_length += message_length
    return truncated_messages

# 사용자 입력 처리
if user_input := st.chat_input("궁금한 것을 입력하세요."):
    # 리트리버에서 문서 검색
    relevant_docs = retriever.get_relevant_documents(user_input)
    context = "\n".join([doc.page_content for doc in relevant_docs])
    max_context_length = 3000  # 검색된 문서의 최대 길이 제한
    context = context[:max_context_length]

    st.chat_message("user").write(user_input)
    st.session_state["messages"].append(ChatMessage(role="user", content=user_input))

    # AI 응답 생성
    with st.chat_message("assistant"):
        stream_handler = StreamHandler(st.empty())

        # 모델 생성
        llm = ChatOpenAI(model="gpt-4", streaming=True, callbacks=[stream_handler], max_tokens=500)

        # 프롬프트 생성
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"{prompt_text[:1000]}\n\n아래는 리트리버에서 가져온 데이터입니다:\n{context}"
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )

        # RunnableWithMessageHistory 설정
        chain = prompt | llm
        chain_with_memory = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="question",
            history_messages_key="history",
        )

        # 대화 기록 제한
        st.session_state["messages"] = truncate_messages(st.session_state["messages"])

        # 사용자 입력 처리 및 AI 응답 생성
        response = chain_with_memory.invoke(
            {"question": user_input},
            config={"configurable": {"session_id": session_id}},
        )
        st.session_state["messages"].append(
            ChatMessage(role="assistant", content=response.content)
        )
