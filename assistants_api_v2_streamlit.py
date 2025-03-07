import streamlit as st
from assistant import *
import time

def process_run(thread_id, assistant_id):
    run_id = runAssistant(thread_id, assistant_id)
    status = 'running'

    while status != 'completed':
        with st.spinner('Waiting for assistant response...'):
            time.sleep(5)
            status = checkRunStatus(thread_id, run_id)

    thread_messages = retrieveThread(thread_id)

    # Update conversation log in JSON
    config = load_config()
    config[assistant_id]['conversation'] = thread_messages
    save_config(config)

    st.write("### Conversation:")
    for message in thread_messages:
        role = "👤 User" if message['role'] == 'user' else "🤖 Assistant"
        st.markdown(f"**{role}:** {message['content']}")

def main():
    st.title("🧠 OpenAI Assistant Playground")

    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    # Sidebar for assistant selection
    st.sidebar.title("🔧 Manage Assistants")
    selected_assistant_name = st.sidebar.selectbox(
        "Select existing assistant", 
        ["➕ Create New Assistant"] + list(assistant_names.keys())
    )

    if selected_assistant_name == "➕ Create New Assistant":
        # Create new assistant interface
        st.header("✨ Create a New Assistant")
        title = st.text_input("Assistant Title", key="new_title")
        initiation = st.text_input("Initial Question", key="new_initiation")
        model = st.selectbox("Model", ["gpt-4-turbo", "gpt-3.5-turbo"], key="new_model")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, key="new_temp")
        uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, key="new_files")

        if uploaded_files and title and initiation:
            file_locations = []
            for uploaded_file in uploaded_files:
                location = f"temp_{uploaded_file.name}"
                with open(location, "wb") as f:
                    f.write(uploaded_file.getvalue())
                file_locations.append(location)
                st.success(f'Uploaded {uploaded_file.name}')

            with st.spinner('Creating assistant...'):
                file_ids = [saveFileOpenAI(loc) for loc in file_locations]
                assistant_id, vector_id = createAssistant(file_ids, title, model, temperature)

            thread_id = startAssistantThread(initiation, vector_id)

            st.success("Assistant created successfully!")
            process_run(thread_id, assistant_id)

    else:
        # Existing assistant selected
        assistant_id = assistant_names[selected_assistant_name]
        assistant = config[assistant_id]
        
        st.header(f"🗣️ Assistant: {selected_assistant_name}")
        st.write(f"**Model:** {assistant['model']}")
        st.write(f"**Temperature:** {assistant['temperature']}")

        # Continue existing conversation or ask new question
        last_conversation = assistant.get('conversation', [])
        if last_conversation:
            st.write("### Last conversation:")
            for message in last_conversation:
                role = "👤 User" if message['role'] == 'user' else "🤖 Assistant"
                st.markdown(f"**{role}:** {message['content']}")

        follow_up = st.text_input("Continue the conversation...", key="follow_up_existing")
        uploaded_files = st.file_uploader("Upload Additional Files (optional)", accept_multiple_files=True, key="additional_files")

        if st.button("Submit"):
            vector_store_id = assistant['vector_store_id']
            if uploaded_files:
                file_locations = []
                for uploaded_file in uploaded_files:
                    location = f"temp_{uploaded_file.name}"
                    with open(location, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    file_locations.append(location)
                    st.success(f'Uploaded {uploaded_file.name}')
                
                # Update vector store with new files
                file_ids = [saveFileOpenAI(loc) for loc in file_locations]
                updateVectorStoreWithFiles(vector_store_id, file_ids)
                st.success("Vector store updated with new files!")

            # Start or continue thread
            thread_id = assistant.get("thread_id")
            if not thread_id:
                thread_id = startAssistantThread(follow_up, vector_store_id)
                config[assistant_id]["thread_id"] = thread_id
                save_config(config)
            else:
                addMessageToThread(thread_id, follow_up)

            process_run(thread_id, assistant_id)

if __name__ == "__main__":
    main()
