import json
import os
from openai import OpenAI
import streamlit as st

CONFIG_FILE = "assistant_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def createAssistant(file_ids, title, model, temperature):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    instructions = """
    You are a helpful assistant. Use your knowledge base to answer user questions.
    """

    tools = [{"type": "file_search"}]

    vector_store = client.beta.vector_stores.create(name=title, file_ids=file_ids)
    tool_resources = {"file_search": {"vector_store_ids": [vector_store.id]}}

    assistant = client.beta.assistants.create(
        name=title,
        instructions=instructions,
        model=model,
        tools=tools,
        tool_resources=tool_resources,
        temperature=temperature
    )

    config = load_config()
    config[assistant.id] = {
        "title": title,
        "vector_store_id": vector_store.id,
        "model": model,
        "temperature": temperature,
        "conversation": []
    }
    save_config(config)

    return assistant.id, vector_store.id

def saveFileOpenAI(location):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    file = client.files.create(file=open(location, "rb"), purpose='assistants')
    os.remove(location)
    return file.id

def startAssistantThread(prompt, vector_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    messages = [{"role": "user", "content": prompt}]
    tool_resources = {"file_search": {"vector_store_ids": [vector_id]}}
    thread = client.beta.threads.create(messages=messages, tool_resources=tool_resources)
    return thread.id

def runAssistant(thread_id, assistant_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
    return run.id

def checkRunStatus(thread_id, run_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return run.status

def retrieveThread(thread_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    messages = client.beta.threads.messages.list(thread_id)
    thread_messages = [{
        'content': m.content[0].text.value,
        'role': m.role
    } for m in messages.data[::-1]]
    return thread_messages

def addMessageToThread(thread_id, prompt):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    client.beta.threads.messages.create(thread_id, role="user", content=prompt)
