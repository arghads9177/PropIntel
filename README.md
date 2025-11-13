# 🏡 PropIntel — Real Estate Answers. Instantly. Accurately.

PropIntel is an AI-powered **Real Estate Intelligence Assistant** that delivers instant, accurate property information using **RAG (Retrieval-Augmented Generation)**, **LangGraph**, **LangChain**, and **ChromaDB**.  
It is designed to assist **real estate agencies, sales teams, and property buyers** by providing fast, conversational access to project details, listings, amenities, booking status, and operational insights — all grounded in verified data.

---

## 🚀 Overview

PropIntel is built as a production-style AI assistant that understands real estate data from multiple sources such as:

- Public website pages (project details, amenities, FAQs, specifications)  
- Marketing brochures, PDFs, and floorplans  
- Operational data extracted from internal systems like **eBuilder**  
- CSV/DB exports of listings, availability & pricing  

Using RAG, the assistant retrieves context from indexed documents and answers queries with citations.  
Using LangGraph, it orchestrates agentic workflows, language processing, and tool-switching for reliability.

PropIntel can be extended into a sales assistant, property recommender, CRM automation tool, and more.

---

## 🧠 Key Features

### 🔍 **1. Property Q&A (RAG-Powered)**
Ask questions about any project or listing:
- "Tell me about the amenities in Project X"  
- "What is the price of a 3BHK in Salt Lake?"  
- "Show me the specifications for Tower A"  

Powered by ChromaDB embeddings with metadata-rich retrieval.

---

### 🏗 **2. Multi-Source Knowledge Integration**
PropIntel intelligently indexes and retrieves information from:
- Website property pages  
- Brochures & PDFs  
- eBuilder (CSV/DB exports)  
- Legal & FAQ documents  
- Floorplans and images (optional multimodal support)

---

### 🧩 **3. Agentic Workflow (LangGraph)**
Built on a modular LangGraph architecture:
- Language detection  
- RAG retriever  
- Property data tool  
- Booking status lookup  
- Lead summarization automation  
- LLM fallback (OpenAI → Google → Groq)

---

### 🌍 **4. Multilingual Support (Optional)**
Supports multilingual queries:
- English  
- Hindi  
- Bengali  

Each answer includes language tag + confidence.

---

### 💼 **5. Real Estate Automations**
Includes lightweight automations for:
- Lead qualification  
- Property recommendations  
- Summary generation  
- Email-ready response templates  
- CRM webhook integration (optional)

---

### 🧾 **6. Citations & Transparency**
Every response includes:
- Document source  
- Chunk metadata  
- Confidence score  

Never hallucinate—PropIntel is grounded in indexed facts.

---

## 🧩 Tech Stack

- **LangGraph** – Agent workflow orchestration  
- **LangChain** – RAG pipeline components  
- **ChromaDB** – Vector storage  
- **OpenAI Embeddings** – Document & metadata embeddings  
- **LLMs:** OpenAI (primary), Google & Groq (fallback)  
- **Streamlit** – Frontend demo application  
- **Python** – Ingestion, parsing, processing  

---

## 🎯 Use Cases

- Property discovery & information lookup  
- Buyer assistance & FAQs  
- Lead qualification & matching  
- Booking/payment status lookup  
- Sales team productivity enhancement  
- Automated summaries for CRM or email  

---

## 🚀 Getting Started
`git clone https://github.com/arghads9177/PropIntel`

`cd PropIntel`

`pip install -r requirements.txt`

`streamlit run app/ui.py`

---

## 📝 License
Open-source under the MIT License.

---

## 📬 Contact
For questions or collaboration, feel free to reach out via LinkedIn or email.

---

*PropIntel — Real Estate Answers. Instantly. Accurately.*
