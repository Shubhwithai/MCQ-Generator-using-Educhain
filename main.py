import hashlib
import fitz  # PyMuPDF for handling PDF files
import re
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List
from educhain import qna_engine
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
os.getenv("OPENAI_API_KEY")

# Define the MCQ model
class MCQ(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class MCQList(BaseModel):
    mcqs: List[MCQ]

# PDF Loader Class
class PdfFileLoader:
    def load_data(self, file):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        all_content = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            content = page.get_text("text")
            content = self.clean_string(content)
            all_content.append(content)

        doc_id = hashlib.sha256(" ".join(all_content).encode()).hexdigest()
        return {
            "doc_id": doc_id,
            "content": " ".join(all_content),
        }

    def clean_string(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

# Text File Loader Class
class TextFileLoader:
    def load_data(self, file):
        content = file.read().decode('utf-8')
        content = self.clean_string(content)
        doc_id = hashlib.sha256(content.encode()).hexdigest()
        return {
            "doc_id": doc_id,
            "content": content,
        }

    def clean_string(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

# URL Loader Class
class UrlLoader:
    def load_data(self, url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.get_text()
        content = self.clean_string(content)
        doc_id = hashlib.sha256(content.encode()).hexdigest()
        return {
            "doc_id": doc_id,
            "content": content,
        }

    def clean_string(self, text):
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

# Function to generate MCQs using educhain's qna_engine
def generate_mcq(topic, num=1, learning_objective="", difficulty_level="", prompt_template=None, **kwargs):
    if prompt_template is None:
        prompt_template = """
        Generate {num} multiple-choice question (MCQ) based on the given topic and level.
        Provide the question, four answer options, and the correct answer.

        Topic: {topic} 
        Difficulty Level: {difficulty_level}
        """

    result = qna_engine.generate_mcq(
        topic=topic,
        num=num,
        difficulty_level=difficulty_level,
        prompt_template=prompt_template,
    )

    return result

# Unified function to generate MCQs from different data sources
def generate_mcqs_from_data(source, source_type, num=1, learning_objective="", difficulty_level="", prompt_template=None, **kwargs):
    if source_type == 'pdf':
        loader = PdfFileLoader()
        data = loader.load_data(source)
    elif source_type == 'text':
        loader = TextFileLoader()
        data = loader.load_data(source)
    elif source_type == 'url':
        loader = UrlLoader()
        data = loader.load_data(source)
    else:
        raise ValueError("Unsupported source type. Please use 'pdf', 'text', or 'url'.")

    content = data['content']

    return generate_mcq(content, num=num, learning_objective=learning_objective, difficulty_level=difficulty_level, prompt_template=prompt_template, **kwargs)

# Function to format MCQs
def format_mcqs(mcqs):
    formatted_output = ""
    for i, mcq in enumerate(mcqs, 1):
        formatted_output += f"{i}. {mcq.question}\n"
        for j, option in enumerate(mcq.options, 1):
            formatted_output += f"   {chr(96+j)}) {option}\n"
        formatted_output += f"   Answer: {mcq.correct_answer}\n\n"
    return formatted_output

# Streamlit app
def main():
    st.title("MCQ Generator using Educhain")

    # Set up the OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    source_type = st.selectbox("Select source type", ["pdf", "text", "url"])
    num_mcqs = st.number_input("Number of MCQs", min_value=1, max_value=10, value=1)
    difficulty_level = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])

    if source_type == 'pdf':
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        if uploaded_file is not None:
            if st.button("Generate MCQs"):
                mcqs = generate_mcqs_from_data(uploaded_file, 'pdf', num=num_mcqs, difficulty_level=difficulty_level)
                formatted_mcqs = format_mcqs(mcqs.questions)  # Assuming mcqs.questions is the list of MCQ objects
                st.text(formatted_mcqs)

    elif source_type == 'text':
        uploaded_file = st.file_uploader("Choose a text file", type="txt")
        if uploaded_file is not None:
            if st.button("Generate MCQs"):
                mcqs = generate_mcqs_from_data(uploaded_file, 'text', num=num_mcqs, difficulty_level=difficulty_level)
                formatted_mcqs = format_mcqs(mcqs.questions)
                st.text(formatted_mcqs)

    elif source_type == 'url':
        url = st.text_input("Enter a URL")
        if url:
            if st.button("Generate MCQs"):
                mcqs = generate_mcqs_from_data(url, 'url', num=num_mcqs, learning_objective=learning_objective, difficulty_level=difficulty_level)
                formatted_mcqs = format_mcqs(mcqs.questions)
                st.text(formatted_mcqs)

if __name__ == "__main__":
    main()