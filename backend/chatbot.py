"""
chatbot.py
LLM integration for the healthcare assistant.

Supports both OpenAI and Google Gemini as the model provider
(selected with the LLM_PROVIDER environment variable).

The answer is built with Retrieval-Augmented Generation:
retrieved context is injected into a system prompt before generation.
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from database import add_chat_message
from rag_pipeline import retrieve_context

# The system prompt keeps the assistant safe and grounded:
#  - answers come from the retrieved medical context when available
#  - no definitive diagnosis, dosages or treatment plans
#  - a clear "not a doctor" disclaimer is always included
#  - a short follow-up question is asked at the end
SYSTEM_PROMPT = """\
You are "MediCare AI", a friendly healthcare assistant built with Retrieval-Augmented Generation.

Your job is to help users understand medical topics using the knowledge base below,
which comes from trusted uploaded medical documents.

Rules you MUST follow:
1. Answer only general healthcare questions. Never give a definitive diagnosis.
2. Base your answer on the retrieved context when it is relevant.
3. If the context does not contain the answer, say so clearly and give a general, safe answer.
4. Never prescribe exact medication dosages or treatment plans.
5. ALWAYS include a clear note that you are not a doctor and that the user should
   consult a qualified healthcare professional for medical advice.
6. If the user describes an emergency (chest pain, severe bleeding, difficulty breathing,
   stroke signs), advise them to call emergency services immediately.
7. End with one short, relevant follow-up question to better help the user.

Retrieved context:
{context}

User question:
{question}
"""


def get_llm():
    """Return a chat model based on the configured provider."""
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "")
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")
        return ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=0.3
        )

    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to the .env file.")
    return ChatOpenAI(model=model, api_key=api_key, temperature=0.3)


def generate_answer(
    question: str, user_id: int | None = None
) -> tuple[str, list[str]]:
    """
    Generate a grounded answer for a user question.

    Returns ``(answer, sources)`` where ``sources`` is the ordered list of
    document filenames the answer was drawn from (empty when no knowledge
    base matched). The question and answer are saved to the user's chat
    history when a user_id is provided.
    """
    if user_id:
        add_chat_message(user_id, "user", question)

    # Step 1 - RAG: retrieve the most relevant document chunks.
    context, sources = retrieve_context(question)

    # Step 2 - Generation: feed the context to the LLM and stream the result.
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "{question}")]
    )
    chain = prompt | get_llm()
    result = chain.invoke({"context": context, "question": question})

    answer = result.content if hasattr(result, "content") else str(result)

    if user_id:
        add_chat_message(user_id, "assistant", answer, sources=sources)
    return answer, sources
