import streamlit as st
from assistant import *
import time
from openai import OpenAI

# Autenticación
def authenticate(password):
    return password == st.secrets["APP_PASSWORD"]

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Aplicación protegida")
    pwd = st.text_input("Ingresa la contraseña:", type="password")
    if st.button("Ingresar"):
        if authenticate(pwd):
            st.session_state.authenticated = True
            st.success("Contraseña correcta.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
else:
    def process_run(thread_id, assistant_id):
        run_id = runAssistant(thread_id, assistant_id)
        status = 'running'
        while status != 'completed':
            time.sleep(2)
            status = checkRunStatus(thread_id, run_id)

        messages = retrieveThread(thread_id)
        config = load_config()
        config[assistant_id]['conversation'] = messages
        config[assistant_id]['thread_id'] = thread_id  # guardar thread_id siempre
        save_config(config)
        return messages

    def display_chat(messages):
        for msg in messages:
            role = "user" if msg['role'] == 'user' else "assistant"
            with st.chat_message(role):
                st.markdown(msg['content'])

    st.set_page_config(page_title="🧠 OpenAI Playground", layout="wide")
    st.title("🧠 OpenAI Assistant Playground")

    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    st.sidebar.title("🔧 Asistentes Guardados")
    selected = st.sidebar.selectbox(
        "Selecciona un asistente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    # Agregar asistente por ID (expandible)
    with st.sidebar.expander("🔗 Agregar asistente por ID"):
        external_assistant_id = st.text_input("Assistant ID existente:")
        external_assistant_name = st.text_input("Ponle un nombre:")
        if st.button("➕ Agregar asistente"):
            if external_assistant_id and external_assistant_name:
                try:
                    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    assistant = client.beta.assistants.retrieve(external_assistant_id)
                    vector_store_ids = assistant.tool_resources.file_search.vector_store_ids
                    vector_store_id = vector_store_id = vector_store_id = vector_store_id = vector_store_id = vector_store_ids = vector_store_ids = assistant.tool_resources.file_search.vector_store_ids[0] if assistant.tool_resources.file_search.vector_store_ids else None

                    config[external_assistant_id] = {
                        "title": external_assistant_name,
                        "instructions": assistant.instructions,
                        "vector_store_id": vector_store_id,
                        "model": assistant.model,
                        "temperature": assistant.temperature,
                        "conversation": [],
                        "uploaded_files": [],
                        "thread_id": None
                    }
                    save_config(config)
                    st.success(f"Asistente '{external_assistant_name}' agregado exitosamente. Selecciónalo ahora desde la lista.")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al agregar: {e}")
            else:
                st.warning("Completa ambos campos.")

    st.sidebar.info("🔖 Los asistentes aparecen aquí una vez creados o agregados.")

    if selected := st.sidebar.selectbox(
        "Selecciona asistente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    ) == "➕ Crear nuevo asistente":
        st.header("✨ Crear Nuevo Asistente")
        title = st.text_input("Título")
        instructions = st.text_area("Prompt", "Eres un asistente útil.")
        initiation = st.text_input("Pregunta inicial")
        model = st.selectbox("Modelo", ["gpt-4-turbo", "gpt-3.5-turbo"])
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.7)
        files = st.file_uploader("Sube archivos", accept_multiple_files=True)

        if st.button("🚀 Crear Asistente"):
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
                        "conversation": [],
                        "uploaded_files": [file.name for file in files],
                        "thread_id": thread_id
                    }
                    save_config(config)
                    st.success("✅ Asistente creado exitosamente. Comienza a chatear abajo.")
                    time.sleep(1.5)
                    st.rerun()
            else:
                st.warning("Completa todos los campos y sube archivos.")
    else:
        assistant_id = assistant_names[selected]
        assistant = config[assistant_id]

        st.sidebar.subheader("📁 Archivos guardados")
        if assistant.get('uploaded_files'):
            for f in assistant['uploaded_files']:
                st.sidebar.markdown(f"- 📄 `{f}`")
        else:
            st.sidebar.write("Sin archivos.")

        if st.sidebar.button(f"❌ Eliminar '{selected}'"):
            del config[assistant_id]
            save_config(config)
            st.sidebar.success("Eliminado correctamente.")
            st.rerun()

        st.header(f"💬 Chat con '{selected}'")
        st.info("💡 Escribe abajo para interactuar.")

        messages = assistant.get('conversation', [])
        if messages:
            with st.expander("📑 Historial de conversación"):
                display_chat(messages)

        # Crear nuevos threads
        if st.button("🔄 Crear nueva conversación (Thread)"):
            new_thread_id = startAssistantThread("Hola", assistant['vector_store_id'])
            assistant['thread_id'] = new_thread_id
            assistant['conversation'] = []
            save_config(config)
            st.success("Nuevo thread creado, comienza la conversación desde abajo.")
            time.sleep(1.5)
            st.rerun()

        prompt = st.chat_input("Escribe aquí...")
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)

            if not assistant["thread_id"]:
                assistant["thread_id"] = startAssistantThread(prompt, assistant["vector_store_id"])

            addMessageToThread(assistant["thread_id"], prompt)
            messages = process_run(assistant["thread_id"], assistant_id)

            with st.chat_message("assistant"):
                st.markdown(messages[-1]['content'])

            save_config(config)

        # Mostrar historial
        if assistant.get('conversation'):
            with st.expander("📑 Ver historial completo"):
                display_chat(assistant['conversation'])

