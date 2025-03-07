from openai import OpenAI
import streamlit as st
import os



def createAssistant(file_ids, title):
    #Create the OpenAI Client Instance
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    #GET Instructions saved in the Settings.py File (We save the instructions there for easy access when modifying)
    instructions = """
    You are a helpful assistant. Use your knowledge base to answer user questions.
    """

    #The GPT Model for the Assistant (This can also be updated in the settings )
    model = "gpt-4-turbo"

    #Only Retireval Tool is relevant for our use case
    tools = [{"type": "file_search"}]

    ##CREATE VECTOR STORE
    vector_store = client.beta.vector_stores.create(name=title,file_ids=file_ids)
    tool_resources = {"file_search": {"vector_store_ids": [vector_store.id]}}

    #Create the Assistant
    assistant = client.beta.assistants.create(
    name=title,
    instructions=instructions,
    model=model,
    tools=tools,
    tool_resources=tool_resources
    )

    #Return the Assistant ID
    return assistant.id,vector_store.id




def saveFileOpenAI(location):
    #Create OpenAI Client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    #Send File to OpenAI
    file = client.files.create(file=open(location, "rb"),purpose='assistants')

    # Delete the temporary file
    os.remove(location)

    #Return FileID
    return file.id



def startAssistantThread(prompt,vector_id):
    #Initiate Messages
    messages = [{"role": "user", "content": prompt}]
    #Create the OpenAI Client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    #Create the Thread
    tool_resources = {"file_search": {"vector_store_ids": [vector_id]}}
    thread = client.beta.threads.create(messages=messages,tool_resources=tool_resources)

    return thread.id



def runAssistant(thread_id, assistant_id):
    #Create the OpenAI Client
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    run = client.beta.threads.runs.create(thread_id=thread_id,assistant_id=assistant_id)
    return run.id



def checkRunStatus(thread_id, run_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    run = client.beta.threads.runs.retrieve(thread_id=thread_id,run_id=run_id)
    return run.status



def retrieveThread(thread_id):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    thread_messages = client.beta.threads.messages.list(thread_id)
    list_messages = thread_messages.data
    thread_messages = []
    for message in list_messages:
        obj = {}
        obj['content'] = message.content[0].text.value
        obj['role'] = message.role
        thread_messages.append(obj)
    return thread_messages[::-1]



def addMessageToThread(thread_id, prompt):
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    thread_message = client.beta.threads.messages.create(thread_id,role="user",content=prompt)
