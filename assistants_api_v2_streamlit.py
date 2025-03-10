import streamlit as st
from assistant import *
import time
from openai import OpenAI

# --- Autenticación ---
def authenticate(password):
    return password == st.secrets["APP_PASSWORD"]

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Acceso restringido")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if authenticate(pwd):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
else:
    # --- Funciones Auxiliares ---
    def process_run(thread_id, assistant_id):
        run_id = runAssistant(thread_id, assistant_id)
        while checkRunStatus(thread_id, run_id) != 'completed':
            time.sleep(2)
        return retrieveThread(thread_id)

    def display_chat(messages):
        for msg in messages:
            role = "👤" if msg['role'] == 'user' else "🤖"
            with st.chat_message(msg['role']):
                st.markdown(f"{role} {msg['content']}")

    # --- Página principal ---
    st.set_page_config(page_title="OpenAI Playground", layout="wide")
    st.markdown("### 🧠 OpenAI Playground")

    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    # Sidebar compacta
    st.sidebar.markdown("### 🔧 Asistentes")
    selected = st.sidebar.selectbox("Selecciona asistente:", ["➕ Crear nuevo"] + list(assistant_names.keys()))

    with st.sidebar.expander("➕ Añadir asistente por ID"):
        external_assistant_id = st.text_input("Assistant ID:")
        external_assistant_name = st.text_input("Nombre:")
        if st.button("Añadir"):
            if external_assistant_id and external_assistant_name:
                try:
                    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    assistant = client.beta.assistants.retrieve(external_assistant_id)
                    vector_store_id = assistant.tool_resources.file_search.vector_store_ids[0] if assistant.tool_resources.file_search.vector_store_ids else None
                    config[external_assistant_id] = {
                        "title": external_assistant_name,
                        "instructions": assistant.instructions,
                        "vector_store_id": vector_store_id,
                        "model": assistant.model,
                        "temperature": assistant.temperature,
                        "threads": {},
                        "uploaded_files": []
                    }
                    save_config(config)
                    st.success("Asistente añadido correctamente. Selecciónalo desde el sidebar.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    if selected == "➕ Crear nuevo":
        st.markdown("#### ✨ Nuevo asistente")
        title = st.text_input("Título breve:")
        instructions = st.text_area("Prompt:", "Eres un asistente útil.")
        initiation = st.text_input("Primera pregunta:")
        model = st.selectbox("Modelo:", ["gpt-4o-mini","gpt-4-turbo", "gpt-3.5-turbo"])
        temperature = st.slider("Temperatura:", 0.0, 0.5, 0.7)
        files = st.file_uploader("Subir archivos:", accept_multiple_files=True)

        if st.button("Crear asistente"):
            if files and title and initiation:
                with st.spinner("Creando..."):
                    locations = [f"temp_{file.name}" for file in files]
                    for file, loc in zip(files, locations):
                        with open(loc, "wb") as f:
                            f.write(file.getvalue())
                    file_ids = [saveFileOpenAI(loc) for loc in locations]
                    assistant_id, vector_id = createAssistant(file_ids, title, model, temperature, instructions)
                    thread_id = startAssistantThread(initiation, vector_id)
                    config[assistant_id] = {
                        "title": title,
                        "instructions": instructions,
                        "vector_store_id": vector_id,
                        "model": model,
                        "temperature": temperature,
                        "uploaded_files": [file.name for file in files],
                        "threads": {thread_id: [{"role": "user", "content": initiation}]},
                        "current_thread": thread_id
                    }
                    save_config(config)
                st.success(f"Creado '{title}'. Selecciónalo en la lista lateral.")
                time.sleep(3)
                st.rerun()
    else:
        assistant_id = assistant_names[selected]
        assistant = config[assistant_id]

        # Edición de prompt junto al título
        with st.expander(f"🤖 **{selected}** [Editar Prompt]"):
            instructions = st.text_area("Instrucciones:", assistant['instructions'])
            if st.button("Actualizar prompt"):
                updateAssistantInstructions(assistant_id, instructions)
                assistant['instructions'] = instructions
                save_config(config)
                st.success("Prompt actualizado.")

        # Área principal de chat
        st.markdown("#### 💬 Chat actual")
        threads = assistant.get('threads', {})
        thread_options = ["➕ Nueva conversación"] + list(threads.keys())
        selected_thread = st.selectbox("Conversaciones anteriores:", thread_options)

        if selected_thread == "➕ Nueva conversación":
            initiation = st.text_input("Pregunta inicial para nuevo thread:")
            if st.button("Iniciar conversación"):
                if initiation:
                    new_thread_id = startAssistantThread(initiation, assistant["vector_store_id"])
                    assistant['current_thread'] = new_thread_id
                    threads[new_thread_id] = [{"role": "user", "content": initiation}]
                    assistant['threads'] = threads
                    save_config(config)
                    st.success("Conversación creada.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Introduce una pregunta.")
        else:
            assistant['current_thread'] = selected_thread
            save_config(config)
            messages = retrieveThread(selected_thread)
            with st.expander("📑 Ver historial"):
                display_chat(messages)

            prompt = st.chat_input("Escribe tu mensaje...")
            if prompt:
                with st.chat_message("user"):
                    st.markdown(f"👤 {prompt}")
                addMessageToThread(selected_thread, prompt)
                messages = process_run(selected_thread, assistant_id)
                with st.chat_message("assistant"):
                    st.markdown(f"🤖 {messages[-1]['content']}")
                assistant['threads'][selected_thread] = messages
                save_config(config)

        # Sidebar inferior con archivos y eliminación
        st.sidebar.markdown("---")
        st.sidebar.markdown("📁 **Archivos**")
        uploaded_files = assistant.get('uploaded_files', [])
        st.sidebar.write(uploaded_files if uploaded_files else "No hay archivos.")

        if st.sidebar.button(f"🗑️ Eliminar '{selected}'"):
            del config[assistant_id]
            save_config(config)
            st.sidebar.success("Asistente eliminado.")
            st.rerun()
