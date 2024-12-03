from stream import show_intro, ChatHistoryManager
from datetime import datetime
import streamlit as st
import requests
import uuid
import re

# FastAPI 서버 URL
API_URL = "http://127.0.0.1:8000/ask"

# 페이지 설정
st.set_page_config(page_title="제주도 창업 계획", page_icon="🏝️")
st.title("🏝️ 제주도 창업 계획 도우미")
st.subheader("안녕하세요!! 성공적인 제주 창업을 도와주는 사업 계획 도우미입니다. 무엇을 알려드릴까요?")

# 애플리케이션 안내 표시
show_intro()

# 세션 ID 생성 및 저장
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
session_id = st.session_state.session_id

# 히스토리 관리자 초기화
history_manager = ChatHistoryManager()

# OpenAI API 키 입력 섹션 
st.sidebar.header("🔑 OpenAI API Key")
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")

# 메시지 상태 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 대화 초기화 버튼 (항상 표시)
if st.sidebar.button("대화 초기화"):
    st.session_state.messages = []
    st.rerun()

# 사이드바 메뉴
menu = st.sidebar.radio("메뉴", ["채팅", "채팅 히스토리", "히스토리 검색"])

if menu == "채팅":
    # 기존 메시지 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # api key 입력 시
    if api_key:
        # 빠른 질문 버튼
        st.sidebar.header("🚀 빠른 질문")
        quick_questions = [
            "제주 지역 창업 아이템 추천",
            "정부 지원 및 자금 확보",
            "법적/행정적 필수 절차"
        ]

        st.empty()  # 답변이 2번 보이는 현상 방지
        for question in quick_questions:
            if st.sidebar.button(question):
                # 사용자 메시지 처리
                st.session_state.messages.append({"role": "user", "content": question})
                with st.chat_message("user"):
                    st.markdown(question)
                history_manager.add_message("user", question, session_id)

                # AI 응답 생성
                with st.chat_message("assistant"):
                    with st.spinner("Waiting for a response..."):
                        # FastAPI 서버로 POST 요청
                        response = requests.post(API_URL, json={"api_key": api_key, "question": question})
                        
                        if response.status_code == 200:
                            answer = response.json().get("answer", "No answer received.")
                            st.markdown(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                            history_manager.add_message("assistant", answer, session_id)
                        else:
                            st.error("Failed to get a response from the server.")

        # 채팅 입력란
        if question := st.chat_input("창업 아이디어 또는 질문을 입력하세요"):
            # 사용자 메시지 처리
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            history_manager.add_message("user", question, session_id)

            # 기존 대화 이력 가져오기 (최대 20개의 메시지로 제한)
            conversation_history = history_manager.get_messages(session_id, limit=20)
            # 시간 순서대로 정렬
            conversation_history = conversation_history[::-1]
            
            # AI 응답 생성
            with st.chat_message("assistant"):
                with st.spinner("Waiting for a response..."):
                    # 대화 이력을 서버로 전송
                    data = {
                        "api_key": api_key,
                        "conversation": [{"role": role, "content": content} for role, content, _ in conversation_history],
                        "question": question
                    }
                    # FastAPI 서버로 POST 요청
                    response = requests.post(API_URL, json=data)
                    
                    if response.status_code == 200:
                        answer = response.json().get("answer", "No answer received.")
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        history_manager.add_message("assistant", answer, session_id)
                    else:
                        st.error("Failed to get a response from the server.")

    else:
        st.warning("OpenAI API 키를 입력해주세요.")

elif menu == "채팅 히스토리":
    # 저장된 채팅 히스토리 표시 
    st.header("📜 채팅 히스토리")
    messages = history_manager.get_messages(session_id, limit=100)
    
    for msg in messages:
        role, content, timestamp = msg
        formatted_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
        
        if role == "user":
            st.markdown(f"**👤 사용자 [{formatted_timestamp}]:**\n{content}")
        else:
            st.markdown(f"**🤖 AI [{formatted_timestamp}]:**\n{content}")
        
        st.divider()
    
    # 히스토리 삭제 버튼
    if st.button("전체 히스토리 삭제"):
        history_manager.clear_history(session_id)
        st.success("채팅 히스토리가 삭제되었습니다.")

elif menu == "히스토리 검색":
    # 특정 키워드로 히스토리 검색 
    st.header("🔍 히스토리 검색")
    search_query = st.text_input("검색어를 입력하세요")
    
    if search_query:
        # 검색 결과 표시
        results = history_manager.search_messages(search_query, session_id)
        st.subheader(f"'{search_query}' 검색 결과")
        
        if results:
            for msg in results:
                role, content, timestamp = msg
                formatted_timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
                
                # 검색어 하이라이트
                highlighted_content = re.sub(
                    f'({re.escape(search_query)})', 
                    r'**\1**', 
                    content, 
                    flags=re.IGNORECASE
                )
                
                if role == "user":
                    st.markdown(f"**👤 사용자 [{formatted_timestamp}]:**\n{highlighted_content}")
                else:
                    st.markdown(f"**🤖 AI [{formatted_timestamp}]:**\n{highlighted_content}")
                
                st.divider()
        else:
            st.info("검색 결과가 없습니다.")