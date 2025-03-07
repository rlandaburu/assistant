import streamlit as st
from assistant import *
import time

def process_run(st, thread_id, assistant_id):
    run_id = runAssistant(thread_id, assistant_id)
    status = 'running'

    while status != 'completed':
        with st.spinner('Waiting for assistant response . . .'):
            time.sleep(10)  # Faster refresh for testing
            status = checkRunStatus(thread_id, run_id)

    thread_messages = retrieveThread(thread_id)

    # Update conversation log in JSON
    config = load_config()
    config[assistant_id]['conversation'] = thread_messages
    save_config(config)

    for message in thread_messages:
        role = 'User' if message['role'] == 'user' else 'Assistant'
        st.markdown(f"**{role}:** {message['content']}")

def main():
    st.title("Chatwoot Assistant Playground")
    config = load_config()

    if 'assistant_initialized' not in st.session_state:
        title = st.text_input("Assistant Title", key="title")
        initiation = st.text_input("First Question to Assistant", key="initiation")
        model = st.selectbox("Select Model", ["gpt-4-turbo", "gpt-3.5-turbo"], key="model")
        temperature = st.slider("Set Temperature", 0.0, 1.0, 0.7, key="temperature")

        uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, key="uploader")

        if uploaded_files and title and initiation:
            file_locations = []
            for uploaded_file in uploaded_files:
                location = f"temp_{uploaded_file.name}"
                with open(location, "wb") as f:
                    f.write(uploaded_file.getvalue())
                file_locations.append(location)
                st.success(f'{uploaded_file.name} uploaded successfully.')

            with st.spinner('Creating assistant...'):
                file_ids = [saveFileOpenAI(loc) for loc in file_locations]
                assistant_id, vector_id = createAssistant(file_ids, title, model, temperature)

            thread_id = startAssistantThread(initiation, vector_id)

            st.session_state.update({
                "thread_id": thread_id,
                "assistant_id": assistant_id,
                "assistant_initialized": True,
                "last_message": initiation
            })

            st.success("Assistant initialized!")
            st.write(f"**Assistant ID:** {assistant_id}")
            st.write(f"**Vector Store ID:** {vector_id}")
            st.write(f"**Thread ID:** {thread_id}")

            process_run(st, thread_id, assistant_id)

    # Follow-up conversations
    if st.session_state.get('assistant_initialized'):
        follow_up = st.text_input("Follow-up Question", key="follow_up")
        if st.button("Submit Follow-up") and follow_up and follow_up != st.session_state["last_message"]:
            st.session_state["last_message"] = follow_up
            addMessageToThread(st.session_state["thread_id"], follow_up)
            process_run(st, st.session_state["thread_id"], st.session_state["assistant_id"])

    # Display assistant configuration & history
    if st.sidebar.button("Show Assistant Configurations"):
        st.sidebar.json(config)

if __name__ == "__main__":
    main()

