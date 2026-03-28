import streamlit as st
import threading
import Main as main  

if 'status' not in st.session_state and 'thread' not in st.session_state and 'token_latency' not in st.session_state and 'full_latency' not in st.session_state:
    st.session_state.token_latency = 0
    st.session_state.full_latency = 0
    st.session_state.status = []
    st.session_state.thread = None


@st.fragment(run_every=0.2)
def show_status():

    for i, item in enumerate(st.session_state.status):
        status = st.session_state.status
        match item['type']:
            case 'status':
                content = item['content']
                st.toast(content)
                status.pop(i)
            case 'token latency':
                st.session_state.token_latency = float(item['content'])
                status.pop(i)
            case 'full latency':
                st.session_state.full_latency = float(item['content'])
                status.pop(i)

    st.subheader("System Status")
    col1, col2 = st.columns(2)
    col1.metric('first token latency', f'~{st.session_state.token_latency:.2f} seconds')
    col2.metric('full response with tts latency', f'~{st.session_state.full_latency:.2f} seconds')

show_status()
if st.toggle('Start Jarvis'):

    if st.session_state.thread is None or not st.session_state.thread.is_alive():
        
        st.session_state.thread = threading.Thread(
            target=main.run_jarvis, 
            args=(st.session_state.status,),
            daemon=True 
        )

        st.session_state.thread.start()
        st.toast("Jarvis is running! Say Jarvis, then say your question, you will hear a beep when it hears jarvis")

with st.sidebar:
    st.markdown("""
        #How to Use
                
        1. **Toggle 'Start Jarvis'**.
        2. **Say "Jarvis"** clearly into your microphone.
        3. **Listen for the Beep** 🔔 (This confirms the model heard you).
        4. **Ask your question** right after the beep!
        5. **Be Patient:** * It **Transcribes** your voice (Whisper).
            * Then, the **Brain** generates a response (Qwen).
            * Finally, it **Synthesizes** the voice (Pocket-TTS).
        
        *Check the **System Status** metrics below to see exactly how fast it's working!*
        """)
    