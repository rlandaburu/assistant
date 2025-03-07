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
    # Funciones auxiliares primero
    def process_run(thread_id, assistant_id):
        run_id = runAssistant(thread_id, assistant_id)
        status = 'running'
        while status != 'completed':
            time.sleep(2)
            status = checkRunStatus(thread_id, run_id)
        return retrieveThread(thread_id)

    def display_chat(messages):
        for msg in messages:
            role = msg['role']
            with st.chat_message(role):
                st.markdown(msg['content'])

    # App principal
    st.set_page_config(page_title="🧠 OpenAI Playground", layout="wide")
    st.title("🧠 OpenAI Assistant Playground")

    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    st.sidebar.title("🔧 Asistentes Guardados")
    selected = st.sidebar.selectbox(
        "Selecciona asistente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    # Agregar por ID
    with st.sidebar.expander("🔗 Agregar asistente por ID"):
        external_assistant_id = st.text_input("Assistant ID existente:")
        external_assistant_name = st.text_input("Ponle un nombre:")
        if st.button("➕ Agregar asistente"):
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
                    st.success(f"Asistente '{external_assistant_name}' agregado con éxito. Selecciónalo desde la lista a la izquierda.")
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al agregar: {e}")
            else:
                st.warning("Completa ambos campos.")

    selected = st.sidebar.selectbox(
        "Selecciona un asistente existente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    if selected == "➕ Crear nuevo asistente":
        st.header("✨ Crear Nuevo Asistente")
        title = st.text_input("Título del asistente")
        instructions = st.text_area("Prompt personalizado", "Eres un asistente útil.")
        initiation = st.text_input("Pregunta inicial")
        model = st.selectbox("Modelo", ["gpt-4-turbo", "gpt-3.5-turbo"])
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.7)
        files = st.file_uploader("Archivos para conocimiento", accept_multiple_files=True)

        if st.button("🚀 Crear Asistente"):
            if files and title and initiation:
                with st.spinner("Creando asistente..."):
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
                        "threads": {
                            thread_id: [{"role": "user", "content": initiation}]
                        },
                        "current_thread": thread_id
                    }
                    save_config(config)

                st.success(f"✅ Asistente '{title}' creado. Búscalo ahora en la lista de asistentes a la izquierda.")
                time.sleep(3)
                st.rerun()
            else:
                st.warning("Completa todos los campos y sube archivos.")
    else:
        assistant_id = assistant_names[selected]
        assistant = config[assistant_id]

        st.sidebar.subheader("📁 Archivos guardados")
        files = assistant.get('uploaded_files', [])
        st.sidebar.write(files if files else "Sin archivos.")

        if st.sidebar.button(f"❌ Eliminar '{selected}'"):
            del config[assistant_id]
            save_config(config)
            st.sidebar.success("Asistente eliminado correctamente.")
            st.rerun()

        # Modificar instrucciones claramente arriba
        with st.expander("⚙️ Modificar instrucciones del asistente"):
            instructions = st.text_area("Prompt actual:", assistant.get('instructions'))
            if st.button("Actualizar instrucciones"):
                updateAssistantInstructions(assistant_id, instructions)
                assistant['instructions'] = instructions
                save_config(config)
                st.success("Instrucciones actualizadas correctamente.")

        st.header(f"💬 Chat con '{selected}'")
        st.info("💡 Usa la caja de chat abajo para interactuar con el asistente.")

        # Gestión clara de múltiples threads
        threads = assistant.get('threads', {})
        thread_names = list(threads.keys())

        st.subheader("🧵 Conversaciones guardadas (Threads)")
        selected_thread = st.selectbox("Selecciona un thread:", ["➕ Nuevo Thread"] + thread_names)

        if selected_thread == "➕ Nuevo Thread":
            initiation = st.text_input("Pregunta inicial del nuevo thread:")
            if st.button("Crear nuevo thread"):
                if initiation:
                    new_thread_id = startAssistantThread(initiation, assistant["vector_store_id"])
                    threads[new_thread_id] = []
                    assistant['threads'] = threads
                    assistant['current_thread'] = new_thread_id
                    save_config(config)
                    st.success("Nuevo thread creado exitosamente.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Escribe una pregunta inicial para el nuevo thread.")
        else:
            assistant['current_thread'] = selected_thread
            save_config(config)

            # Mostrar historial del thread actual
            messages = retrieveThread(selected_thread)
            with st.expander("📑 Historial del thread seleccionado"):
                display_chat(messages)

            # Interacción con el thread actual
            prompt = st.chat_input("Escribe tu mensaje aquí...")
            if prompt:
                with st.chat_message("user"):
                    st.markdown(prompt)

                addMessageToThread(selected_thread, prompt)
                messages = process_run(selected_thread, assistant_id)

                with st.chat_message("assistant"):
                    st.markdown(messages[-1]['content'])

                assistant['threads'][selected_thread] = messages
                save_config(config)
