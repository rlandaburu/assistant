import streamlit as st
from assistant import *
import time

def process_run(thread_id, assistant_id):
    run_id = runAssistant(thread_id, assistant_id)
    status = 'running'
    while status != 'completed':
        with st.spinner("🔄 Procesando respuesta..."):
            time.sleep(5)
            status = checkRunStatus(thread_id, run_id)

    messages = retrieveThread(thread_id)
    config = load_config()
    config[assistant_id]['conversation'] = messages
    save_config(config)

    for msg in messages:
        role = "🔵 Usuario" if msg['role'] == 'user' else "🟢 Asistente"
        st.markdown(f"**{role}:** {msg['content']}")

def main():
    st.title("🧠 OpenAI Assistant Playground")
    config = load_config()
    assistant_names = {v['title']: k for k, v in config.items()}

    st.sidebar.title("🔧 Asistentes Guardados")
    selected = st.sidebar.selectbox(
        "Selecciona un asistente:",
        ["➕ Crear nuevo asistente"] + list(assistant_names.keys())
    )

    st.sidebar.info("🔖 **Nota:** Los asistentes creados se guardan aquí para uso rápido posterior.")

    if selected == "➕ Crear nuevo asistente":
        st.header("✨ Crear Nuevo Asistente")
        title = st.text_input("Título del asistente")
        instructions = st.text_area("Prompt personalizado", "Eres un asistente útil.")
        initiation = st.text_input("Pregunta inicial")
        model = st.selectbox("Modelo", ["gpt-4-turbo", "gpt-3.5-turbo"])
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.7)
        files = st.file_uploader("Sube archivos", accept_multiple_files=True)

        if st.button("Crear Asistente"):
            if files and title and initiation:
                locations = []
                for file in files:
                    loc = f"temp_{file.name}"
                    with open(loc, "wb") as f:
                        f.write(file.getvalue())
                    locations.append(loc)

                file_ids = [saveFileOpenAI(loc) for loc in locations]
                assistant_id, vector_id = createAssistant(file_ids, title, model, temperature, instructions)
                thread_id = startAssistantThread(initiation, vector_id)

                config[assistant_id]["thread_id"] = thread_id
                save_config(config)
                process_run(thread_id, assistant_id)

    else:
        assistant_id = assistant_names[selected]
        assistant = config[assistant_id]
        st.header(f"🗣️ {selected}")
        instructions = st.text_area("Modificar prompt del asistente:", assistant.get('instructions'))

        if st.button("Actualizar instrucciones"):
            updateAssistantInstructions(assistant_id, instructions)
            assistant['instructions'] = instructions
            save_config(config)
            st.success("Instrucciones actualizadas.")

        with st.expander("📁 Archivos del asistente"):
            st.write(assistant.get('uploaded_files', []))

        with st.expander("📑 Conversación previa"):
            for msg in assistant.get('conversation', []):
                role = "🔵 Usuario" if msg['role'] == 'user' else "🟢 Asistente"
                st.markdown(f"**{role}:** {msg['content']}")

        pregunta = st.text_input("💬 Continuar conversación aquí:")
        extra_files = st.file_uploader("Agregar archivos (opcional)", accept_multiple_files=True)

        if st.button("Enviar al asistente"):
            if extra_files:
                locations = [f"temp_{f.name}" for f in extra_files]
                for file, loc in zip(extra_files, locations):
                    with open(loc, "wb") as f:
                        f.write(file.getvalue())
                ids = [saveFileOpenAI(l) for l in locations]
                updateVectorStoreWithFiles(assistant['vector_store_id'], ids)

            thread_id = assistant.get('thread_id') or startAssistantThread(pregunta, assistant['vector_store_id'])
            assistant['thread_id'] = thread_id
            save_config(config)
            addMessageToThread(thread_id, pregunta)
            process_run(thread_id, assistant_id)

if __name__ == "__main__":
    main()

