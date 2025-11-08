from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI , GoogleGenerativeAIEmbeddings

load_dotenv()

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash")

print(llm.invoke("Hi, my name is Aamir Ahmed and I am a software engineer"))
print(embeddings.embed_query("Hi, my name is Aamir Ahmed and I am a software engineer"))