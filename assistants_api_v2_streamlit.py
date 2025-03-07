import streamlit as st
from assistant import *
import time

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

    # Sidebar - Manejo asistentes
    st.sidebar.title("🔧 Asistentes Guardados")
    selected = st.sidebar.selectbox(
        "Selecciona un asistente existente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    # Agregar asistente por ID
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 Agregar asistente por ID")
    external_assistant_id = st.sidebar.text_input("Assistant ID existente:")
    external_assistant_name = st.sidebar.text_input("Ponle un nombre al asistente:")
    if st.sidebar.button("➕ Agregar asistente"):
        if external_assistant_id and external_assistant_name:
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            assistant = client.beta.assistants.retrieve(external_assistant_id)
            config[external_assistant_id] = {
                "title": external_assistant_name,
                "instructions": assistant.instructions,
                "vector_store_id": assistant.tool_resources.file_search.vector_store_ids[0],
                "model": assistant.model,
                "temperature": assistant.temperature,
                "conversation": [],
                "uploaded_files": [],
                "thread_id": None
            }
            save_config(config)
            st.sidebar.success("Asistente agregado exitosamente.")
            st.rerun()
        else:
            st.sidebar.error("Ingresa tanto el ID como un nombre válido.")

    st.sidebar.info("🔖 Los asistentes creados o agregados aparecen aquí.")

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
                    locations = []
                    for file in files:
                        loc = f"temp_{file.name}"
                        with open(loc, "wb") as f:
                            f.write(file.getvalue())
                        locations.append(loc)

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
                    messages = process_run(thread_id, assistant_id)

                st.success("Asistente creado con éxito.")
                display_chat(messages)

                if st.button("Ir al chat ahora"):
                    st.rerun()
            else:
                st.warning("Completa todos los campos y sube archivos.")

    else:
        assistant_id = assistant_names[selected]
        assistant = config[assistant_id]

        st.sidebar.subheader("📁 Archivos guardados")
        files = assistant.get('uploaded_files')
        if files:
            for f in files:
                st.sidebar.markdown(f"- 📄 `{f}`")
        else:
            st.sidebar.write("Sin archivos.")

        if st.sidebar.button(f"❌ Eliminar '{selected}'"):
            del config[assistant_id]
            save_config(config)
            st.sidebar.success("Asistente eliminado.")
            st.rerun()

        st.header(f"💬 Chat con '{selected}'")
        st.info("💡 Usa la caja de chat abajo para interactuar con el asistente.")

        messages = assistant.get('conversation', [])
        display_chat(messages)

        with st.expander("⚙️ Modificar instrucciones"):
            instructions = st.text_area("Prompt actual:", assistant.get('instructions'))
            if st.button("Actualizar instrucciones"):
                updateAssistantInstructions(assistant_id, instructions)
                assistant['instructions'] = instructions
                save_config(config)
                st.success("Instrucciones actualizadas.")

        prompt = st.chat_input("Escribe tu mensaje aquí...")
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




