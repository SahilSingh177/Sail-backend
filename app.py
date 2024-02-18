import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
# from langchain.vectorstores import FAISS
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
# from langchain.chat_models import ChatOpenAI
# from langchain.llms import HuggingFaceHub
from langchain_community.llms import HuggingFaceHub
from htmlTemplates import bot_template, user_template,css

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=512,
        chunk_overlap=100,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# Embeddings
# For embedding we have two options:
# 1. Use OpenAI AdaV2 model -> Currently ranked 6th on the leaderboard
# 2. Use Instructor embedding model -> Currently ranked 2nd on the leaderboard


def get_vectorStore(text_chunks):
    # embeddings = OpenAIEmbeddings()
    embeddings = HuggingFaceInstructEmbeddings(
        model_name="hkunlp/instructor-xl")
    vector_store = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    print(vector_store)
    return vector_store

# Conversation chain


def get_conversation_chain(vector_store):
    # llm = ChatOpenAI()
    llm = HuggingFaceHub(repo_id="google/flan-t5-xxl", model_kwargs={"temperature":0.5, "max_length":128})
    memory = ConversationBufferMemory(
        memory_key='chat_history', return_messages=True)
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(),
        memory=memory
    )
    return conversation_chain

def handle_userInput(user_question):
    chunks = get_text_chunks(user_question)
    responses = []
    for chunk in chunks:
        response = st.session_state.conversation({'question': chunk})
        responses.append(response)
        st.session_state.chat_history.extend(response['chat_history'])
    
    for response in responses:
        for i, message in enumerate(response['chat_history']):
            if i % 2 == 0:
                st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
            else:
                st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)


def main():
    load_dotenv()
    st.set_page_config(page_title="Sail", page_icon=":books:", layout="wide")
    st.write(css, unsafe_allow_html=True)
    if "conversation" not in st.session_state:
        st.session_state.conversation = ""
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.header("Sail")
    user_question = st.text_input("Ask a question about the doc")
    if user_question:
        handle_userInput(user_question)
    
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload a document", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing..."):

                # Get Pdf text
                raw_text = get_pdf_text(pdf_docs)

                # Get the text chunks
                text_chunks = get_text_chunks(raw_text)
                st.write(text_chunks)

                # Create vector store
                vector_store = get_vectorStore(text_chunks)

                # Create conversation chain
                # Making a variable session state does two things:
                # 1. It stores the values across reruns of the script
                # 2. It can be used outside the scope of the component where it is defined (sidebar in this case)
                st.session_state.conversation = get_conversation_chain(
                    vector_store)


if __name__ == '__main__':
    main()
