import streamlit as st
from assistant import *
import time

# Función de autenticación simple
def authenticate(password):
    return password == st.secrets["APP_PASSWORD"]

# UI de autenticación
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Aplicación protegida")
    pwd = st.text_input("Ingresa la contraseña para acceder:", type="password")
    if st.button("Ingresar"):
        if authenticate(pwd):
            st.session_state.authenticated = True
            st.success("Contraseña correcta. Acceso permitido.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Contraseña incorrecta. Intenta nuevamente.")
else:
    # Toda tu app original aquí debajo (sin cambios funcionales)
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
            if msg['role'] == 'user':
                with st.chat_message("user"):
                    st.markdown(msg['content'])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg['content'])

    def main_app():
        st.set_page_config(page_title="🧠 OpenAI Playground", layout="wide")
        st.title("🧠 OpenAI Assistant Playground")
        config = load_config()
        assistant_names = {v['title']: k for k, v in config.items()}

        st.sidebar.title("🔧 Asistentes Guardados")
        selected = st.sidebar.selectbox(
            "Selecciona un asistente existente:",
            ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
        )

        st.sidebar.info("🔖 **Nota:** Los asistentes creados aparecerán aquí para acceso rápido posterior.")

        if selected == "➕ Crear nuevo asistente":
            st.header("✨ Crear Nuevo Asistente")
            title = st.text_input("Título del asistente")
            instructions = st.text_area("Prompt personalizado (instrucciones al asistente)", "Eres un asistente útil.")
            initiation = st.text_input("Pregunta inicial para empezar la conversación")
            model = st.selectbox("Modelo", ["gpt-4-turbo", "gpt-3.5-turbo"])
            temperature = st.slider("Temperatura", 0.0, 1.0, 0.7)
            files = st.file_uploader("Sube archivos para la base de conocimiento del asistente", accept_multiple_files=True)

            if st.button("🚀 Crear Asistente"):
                if files and title and initiation:
                    with st.spinner("Creando tu asistente..."):
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

                    st.success("✅ Asistente creado con éxito. ¡Empieza a chatear!")
                    display_chat(messages)

                    if st.button("Ir al chat ahora"):
                        st.rerun()
                else:
                    st.warning("Completa todos los campos y sube archivos para crear el asistente.")

        else:
            assistant_id = assistant_names[selected]
            assistant = config[assistant_id]

            st.sidebar.subheader("📁 Archivos del Asistente")
            if assistant.get('uploaded_files'):
                for f in assistant['uploaded_files']:
                    st.sidebar.markdown(f"- 📄 `{f}`")
            else:
                st.sidebar.write("Aún no hay archivos subidos.")

            if st.sidebar.button(f"❌ Eliminar '{selected}'"):
                del config[assistant_id]
                save_config(config)
                st.sidebar.success("Asistente eliminado exitosamente.")
                st.rerun()

            st.header(f"💬 Chateando con '{selected}'")
            messages = assistant.get('conversation', [])
            display_chat(messages)

            with st.expander("⚙️ Modificar instrucciones del asistente"):
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

                addMessageToThread(assistant["thread_id"], prompt)
                messages = process_run(assistant["thread_id"], assistant_id)

                with st.chat_message("assistant"):
                    st.markdown(messages[-1]['content'])

    main_app()


