import streamlit as st
from assistant import *
import time

def process_run(st, thread_id, assistant_id):
    # Run the Assistant
    run_id = runAssistant(thread_id, assistant_id)
    status = 'running'

    # Check Status Session
    while status != 'completed':
        with st.spinner('Waiting for assistant response . . .'):
            time.sleep(20)  # 20-second delay
            status = checkRunStatus(thread_id, run_id)

    # Retrieve the Thread Messages
    thread_messages = retrieveThread(thread_id)
    for message in thread_messages:
        if message['role'] == 'user':
            st.write('User Message:', message['content'])
        else:
            st.write('Assistant Response:', message['content'])

def main():
    st.title("Chatwoot Assistant V2")
    """
    My name is Karabo, your personal AI Assistant. I create file_search assistants, just upload your knowledge base and start chatting to your documents.
    """

    if 'assistant_initialized' not in st.session_state:
        # Input field for the title
        title = st.text_input("Enter the title", key="title")
        initiation = st.text_input("Enter the assistant's first question", key="initiation")

        # File uploader widget
        uploaded_files = st.file_uploader("Upload Files for the Assistant", accept_multiple_files=True, key="uploader")
        file_locations = []

        if uploaded_files and title and initiation:
            for uploaded_file in uploaded_files:
                # Read file as bytes
                bytes_data = uploaded_file.getvalue()
                location = f"temp_file_{uploaded_file.name}"
                # Save each file with a unique name
                with open(location, "wb") as f:
                    f.write(bytes_data)
                file_locations.append(location)
                st.success(f'File {uploaded_file.name} has been uploaded successfully.')

            # Upload file and create assistant
            with st.spinner('Processing your file and setting up the assistant...'):
                file_ids = [saveFileOpenAI(location) for location in file_locations]
                assistant_id, vector_id = createAssistant(file_ids, title)

            # Start the Thread
            thread_id = startAssistantThread(initiation, vector_id)

            # Save state
            st.session_state.thread_id = thread_id
            st.session_state.assistant_id = assistant_id
            st.session_state.last_message = initiation
            st.session_state.assistant_initialized = True

            st.write("Assistant ID:", assistant_id)
            st.write("Vector ID:", vector_id)
            st.write("Thread ID:", thread_id)

            process_run(st, thread_id, assistant_id)

    # Handling follow-up questions only if assistant is initialized
    if 'assistant_initialized' in st.session_state and st.session_state.assistant_initialized:
        follow_up = st.text_input("Enter your follow-up question", key="follow_up")
        submit_button = st.button("Submit Follow-up")

        if submit_button and follow_up and follow_up != st.session_state.last_message:
            st.session_state.last_message = follow_up
            addMessageToThread(st.session_state.thread_id, follow_up)
            process_run(st, st.session_state.thread_id, st.session_state.assistant_id)

if __name__ == "__main__":
    main()
