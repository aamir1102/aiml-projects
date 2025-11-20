import os
from dotenv import load_dotenv
load_dotenv()

from typing import Annotated, Sequence, Literal
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.messages import AIMessage
from langchain_classic import hub  # (you used langchain_classic in your file)

# ----------------
# 1) STATE
# ----------------
class AgentState(TypedDict):
    # Append new messages rather than replace
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # Loop guard counter for rewrite → agent cycles
    attempts: int


# ----------------
# 2) ENRICHED PROMPTS
# ----------------

# 2a) System prompt for the "agent" node (tool orchestration)
AGENT_SYSTEM_PROMPT = """\
You are an agent orchestrating a Retrieval-Augmented Generation (RAG) workflow.

Core rules:
- Decide whether to use a retriever tool based on the user question and conversation state.
- Prefer using tools when the question requires facts, definitions, documentation, or content that should be grounded in sources.
- If the best answer is common knowledge and you are confident, you MAY answer directly, but keep answers brief and non-speculative.
- NEVER fabricate citations. If you use tool results, cite the sources clearly (e.g., “Source: <doc-title-or-URL>”).
- If retrieved documents are irrelevant, ask for clarification or propose a better query (the graph will route to rewrite).
- Be concise, accurate, and helpful. If you are uncertain, say so and propose next steps.

Output formatting:
- Use clear, short paragraphs and bullet points where helpful.
- Include sources only when you’ve grounded content on retrieved context.
"""

# 2b) Enriched RAG answer prompt (used in `generate`)
RAG_PROMPT = PromptTemplate(
    template=(
        "You are a careful assistant answering the user's question using ONLY the provided context.\n\n"
        "Question:\n{question}\n\n"
        "Context (retrieved passages):\n{context}\n\n"
        "Instructions:\n"
        "- Ground your answer strictly in the context above; do not invent facts.\n"
        "- If the context is insufficient, explicitly say what is missing and propose what to retrieve next.\n"
        "- Summarize and synthesize across passages; do not quote excessively unless necessary.\n"
        "- Include concise citations for any factual claims derived from the context. Use this style:\n"
        "    • Source: <short-title-or-URL>\n"
        "- Keep the tone professional and clear. Prefer bullet points if listing items.\n"
        "- If there are multiple interpretations or edge cases, surface them explicitly.\n\n"
        "Answer:"
    ),
    input_variables=["question", "context"],
)

# 2c) Enriched relevance grader prompt (used in `grade_documents`)
RELEVANCE_GRADER_PROMPT = PromptTemplate(
    template=(
        "You are evaluating whether a retrieved document is relevant to the user's question.\n\n"
        "User question:\n{question}\n\n"
        "Retrieved document content:\n{context}\n\n"
        "Guidelines:\n"
        "- Consider semantic relevance: concepts, definitions, mechanisms, workflows, APIs, or terminology that directly answer or clarify the question.\n"
        "- Superficial keyword overlaps WITHOUT substantive connection are NOT sufficient.\n"
        "- Exact match is not required; paraphrases or closely related explanations count as relevant.\n"
        "- If the document discusses a different library, tool, version, or unrelated topic, grade it as NOT relevant.\n"
        "- Be conservative: prefer 'no' unless you see a clear path to answer the question using the document.\n\n"
        "Provide a binary score: 'yes' if relevant, 'no' if not."
    ),
    input_variables=["context", "question"],
)

# 2d) Enriched rewrite prompt (used in `rewrite`)
REWRITE_PROMPT_TEMPLATE = """\
You are improving a user query for a RAG system.

Task:
- Infer the underlying intent and information need.
- Identify domain-specific terms, entities, APIs, features, or frameworks related to the question.
- Add clarifying constraints only if they are implied (e.g., version, scope, type of output).
- Remove ambiguity and make the query more retrievable.
- Keep it concise and specific (ideally one sentence).

Original question:
-------
{question}
-------

Return ONLY the improved query, no explanations.
"""


# ----------------
# 3) NODES (agent, generate, grade_documents, rewrite) with enriched prompts
# ----------------

def agent(state: AgentState):
    """Agent decides whether to call tools (retriever) or end."""
    print("---CALL AGENT---")
    messages = list(state["messages"])
    # Prepend a system message to improve tool-use behavior
    system_msg = SystemMessage(content=AGENT_SYSTEM_PROMPT)
    messages = [system_msg] + messages

    # Bind tools as before
    # Assumes `tools` variable exists: [retriever_tool, retriever_tool_langchain]
    model = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash")
    model = model.bind_tools(tools)

    response = model.invoke(messages)
    return {"messages": [response]}


def grade_documents(state: AgentState) -> Literal["generate", "rewrite"]:
    """Determine whether retrieved documents are relevant."""
    print("---CHECK RELEVANCE---")

    # Data model for structured output
    from pydantic import BaseModel, Field
    class Grade(BaseModel):
        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    # LLM with structured output
    model = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash")
    llm_with_tool = model.with_structured_output(Grade)

    messages = state["messages"]
    last_message = messages[-1]

    # Extract last HumanMessage as question
    question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break
    if question is None:
        question = messages[0].content

    docs = last_message.content
    chain = RELEVANCE_GRADER_PROMPT | llm_with_tool
    scored_result = chain.invoke({"question": question, "context": docs})
    score = scored_result.binary_score.strip().lower()

    if score == "yes":
        print("---DECISION: DOCS RELEVANT---")
        return "generate"
    else:
        print("---DECISION: DOCS NOT RELEVANT---")
        return "rewrite"


def generate(state: AgentState):
    """Generate grounded answer using enriched RAG prompt."""
    print("---GENERATE---")

    messages = state["messages"]

    # Extract last HumanMessage as question
    question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break
    if question is None:
        question = messages[0].content

    # Last tool output contains retrieved docs
    last_message = messages[-1]
    docs = last_message.content

    model = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash")
    rag_chain = RAG_PROMPT | model | StrOutputParser()
    response = rag_chain.invoke({"context": docs, "question": question})

    return {"messages": [AIMessage(content=response)]}


def rewrite(state: AgentState):
    """
    Transform the query to produce a better question, but only if attempts < 3.
    If attempts >= 3, skip the LLM call and just propagate the current state.
    """
    current_attempts = state.get("attempts", 0)

    # Guard BEFORE any LLM call
    if current_attempts >= 3:
        print("---SKIPPING LLM CALL: max rewrite attempts reached---")
        return {"attempts": current_attempts}

    print("---TRANSFORM QUERY---")

    messages = state["messages"]
    # Extract last HumanMessage as question
    question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break
    if question is None:
        question = messages[0].content

    rewrite_prompt = PromptTemplate(
        template=REWRITE_PROMPT_TEMPLATE, input_variables=["question"]
    )

    model = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash")
    chain = rewrite_prompt | model | StrOutputParser()
    improved_query = chain.invoke({"question": question})

    current_attempts += 1
    return {
        "messages": [HumanMessage(content=improved_query)],
        "attempts": current_attempts,
    }


# ----------------
# 4) ROUTING GUARD
# ----------------
def route_after_rewrite(state: AgentState) -> Literal["agent", "end"]:
    tries = state.get("attempts", 0)
    print(f"---REWRITE ATTEMPTS: {tries}---")
    if tries >= 3:
        print("---TERMINATING: max rewrite attempts reached---")
        return "end"
    return "agent"


# ----------------
# 5) GRAPH WIRING
# ----------------

workflow = StateGraph(AgentState)

# Assumes your tool setup exists:
# retriever_tool, retriever_tool_langchain, tools = [retriever_tool, retriever_tool_langchain]
retrieve = ToolNode([retriever_tool, retriever_tool_langchain])

workflow.add_node("agent", agent)       # agent (decides tools/end)
workflow.add_node("retrieve", retrieve) # retrieval
workflow.add_node("rewrite", rewrite)   # query rewriting
workflow.add_node("generate", generate) # final answer

workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "retrieve", END: END},
)

workflow.add_conditional_edges(
    "retrieve",
    grade_documents,  # returns "generate" or "rewrite"
)

workflow.add_edge("generate", END)

workflow.add_conditional_edges(
    "rewrite",
    route_after_rewrite,
    {"agent": "agent", "end": END},
)

graph = workflow.compile()

# ----------------
# 6) SAFE INVOCATION (seed attempts=0)
# ----------------
graph.invoke({"messages": "What is Langgraph?", "attempts": 0})
graph.invoke({"messages": "What is Langchain?", "attempts": 0})
graph.invoke({"messages": "What is Machine learning?", "attempts": 0})
graph.invoke({"messages": "Tell me about Langgraph ecosystem", "attempts": 0})


#https://github.com/Alex2Yang97/yahoo-finance-mcp/tree/main
#https://github.com/krishnaik06/MCPSERVERLangchain/blob/main/client.py