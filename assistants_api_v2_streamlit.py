import streamlit as st
from assistant import *
import time

def process_run(thread_id, assistant_id):
    run_id = runAssistant(thread_id, assistant_id)
    status = 'running'

    while status != 'completed':
        with st.spinner('Esperando respuesta del asistente...'):
            time.sleep(5)
            status = checkRunStatus(thread_id, run_id)

    thread_messages = retrieveThread(thread_id)

    config = load_config()
    config[assistant_id]['conversation'] = thread_messages
    save_config(config)

    st.write("### Conversación actual:")
    for message in thread_messages:
        role = "👤 Usuario" if message['role'] == 'user' else "🤖 Asistente"
        st.markdown(f"**{role}:** {message['content']}")

def main():
    st.title("🧠 OpenAI Assistant Playground")

    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    # Barra lateral para seleccionar o crear asistente
    st.sidebar.title("🔧 Asistentes")
    selected_assistant_name = st.sidebar.selectbox(
        "Selecciona un asistente existente", 
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    if selected_assistant_name == "➕ Crear nuevo asistente":
        st.header("✨ Crear Nuevo Asistente")
        title = st.text_input("Título del Asistente")
        instructions = st.text_area("Prompt del Asistente (instrucciones personalizadas)", 
                                    "Eres un asistente útil. Usa tu base de conocimiento para responder.")
        initiation = st.text_input("Pregunta inicial")
        model = st.selectbox("Modelo", ["gpt-4-turbo", "gpt-3.5-turbo"])
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.7)
        uploaded_files = st.file_uploader("Subir archivos", accept_multiple_files=True)

        if st.button("Crear Asistente"):
            if uploaded_files and title and initiation:
                file_locations = []
                for uploaded_file in uploaded_files:
                    location = f"temp_{uploaded_file.name}"
                    with open(location, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    file_locations.append(location)
                    st.success(f'Archivo subido: {uploaded_file.name}')

                with st.spinner('Creando asistente...'):
                    file_ids = [saveFileOpenAI(loc) for loc in file_locations]
                    assistant_id, vector_id = createAssistant(file_ids, title, model, temperature, instructions)

                thread_id = startAssistantThread(initiation, vector_id)
                config = load_config()
                config[assistant_id]["thread_id"] = thread_id
                save_config(config)

                st.success("¡Asistente creado con éxito!")
                process_run(thread_id, assistant_id)
            else:
                st.error("Completa todos los campos y sube al menos un archivo.")

    else:
        assistant_id = assistant_names[selected_assistant_name]
        assistant = config[assistant_id]
        
        st.header(f"🗣️ Asistente: {selected_assistant_name}")
        st.write(f"**Modelo:** {assistant['model']}")
        st.write(f"**Temperatura:** {assistant['temperature']}")

        # Mostrar y editar instrucciones actuales
        st.subheader("Instrucciones (Prompt)")
        new_instructions = st.text_area("Editar instrucciones del asistente", assistant.get('instructions', 'Eres un asistente útil.'))

        if st.button("Actualizar instrucciones"):
            updateAssistantInstructions(assistant_id, new_instructions)
            config[assistant_id]['instructions'] = new_instructions
            save_config(config)
            st.success("Instrucciones actualizadas correctamente.")

        # Mostrar conversación previa si existe
        last_conversation = assistant.get('conversation', [])
        if last_conversation:
            st.subheader("Última conversación:")
            for message in last_conversation:
                role = "👤 Usuario" if message['role'] == 'user' else "🤖 Asistente"
                st.markdown(f"**{role}:** {message['content']}")

        # Campo siempre disponible para continuar conversación
        follow_up = st.text_input("Continuar conversación...")
        uploaded_files = st.file_uploader("Subir archivos adicionales (opcional)", accept_multiple_files=True)

        if st.button("Enviar Mensaje"):
            vector_store_id = assistant['vector_store_id']
            if uploaded_files:
                file_locations = []
                for uploaded_file in uploaded_files:
                    location = f"temp_{uploaded_file.name}"
                    with open(location, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    file_locations.append(location)
                    st.success(f'Archivo subido: {uploaded_file.name}')
                
                file_ids = [saveFileOpenAI(loc) for loc in file_locations]
                updateVectorStoreWithFiles(vector_store_id, file_ids)
                st.success("Archivos agregados al Vector Store!")

            thread_id = assistant.get("thread_id")
            if not thread_id:
                thread_id = startAssistantThread(follow_up, vector_store_id)
                config[assistant_id]["thread_id"] = thread_id
                save_config(config)
            else:
                addMessageToThread(thread_id, follow_up)

            process_run(thread_id, assistant_id)

    # Mostrar ubicación de almacenamiento
    st.sidebar.info("📁 Las configuraciones y conversaciones se almacenan en `assistant_config.json`")

if __name__ == "__main__":
    main()

