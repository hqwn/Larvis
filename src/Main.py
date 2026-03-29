#imports
import numpy as np
import whisper
import pyaudio
import numpy as np
from openai import OpenAI
from openwakeword.model import Model
import sounddevice as sd
import soundfile as sf
from pocket_tts import TTSModel
import time
import torch

#model init
vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
(get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
client = OpenAI(base_url="http://localhost:8000/api/v1", api_key="lemonade")
speech_model = whisper.load_model("base.en")
model = Model(wakeword_models=[r"models/jarvis_v2.onnx"],inference_framework="onnx") 
pocket_model = TTSModel.load_model()
pocket_voice = pocket_model.get_state_for_audio_prompt("alba")

#audio init
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000          
CHUNK = 512
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
running = False

#Ai call
def ai_response(Question):
    return client.chat.completions.create(
        model="user.Qwen3-1.7B",
    messages=[{"role": "system", "content": f'You are a voice assistant like alexa, so BE CONSICE and return small output with NO EMOJIS, NO FORMATTING like asterisks, and proper punctuation with periods, commas, and exclamation marks, MAKE SURE TO INCLUDE ALL OF THAT. ALso talk in ENGLISH'}, {'role': 'user', 'content':Question}],
        stream= True,
        temperature= .45
    )

#Wake_word
def wake_word():

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_frame = np.frombuffer(data, dtype=np.int16)
        prediction = model.predict(audio_frame)

        for wakeword, score in prediction.items():
            if score > 0.5:
                return True

#speech recognition
def speech_recognition():

    vad_iterator = VADIterator(vad_model)
    frames = []

    max_duration = 15 
    start_time = time.time()
    
    while (time.time() - start_time) < max_duration:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16)
        frames.append(audio)
        audio_32 = audio.astype(np.float32) / 32768.0
        
        speech_dict = vad_iterator(torch.from_numpy(audio_32), return_seconds=True)
        if speech_dict:
            if 'end' in speech_dict:
                print("Silence detected, stopping recording.")
                break


    audio_data = np.concatenate(frames).astype(np.float32) / 32768.0

    result = speech_model.transcribe(audio_data, fp16=False)
    return result['text']


#Text To Speech
def tts(text):

    #returns if user said nothing
    if not text.strip() or text == ' ':
        return
    
    audio_tensor = pocket_model.generate_audio(
        pocket_voice,text
    )

    sd.stop()
    sd.play(audio_tensor.numpy(), 24000)
    sd.wait()

#Play Audio's
def play_audio(filename):
    data, fs = sf.read(filename, dtype='float32')
    sd.play(data, fs)
    sd.wait() 

#Full run script
def run_jarvis(status):

    while True:
        if wake_word():

            #plays a audio sound to signal that it has heard jarvis
            play_audio(r'audio/musheran-beep-313342.mp3')
            status.append({'type': 'status', 'content': 'Heard Jarvis!'})

            #recognize the user's speech
            speech = speech_recognition()
            status.append({'type': 'status', 'content': f'Asked, {speech}'})

            before_response = time.time()
            response = ai_response(speech)
            sentence = ''
            first_token = False

            for i in response:
                token = i.choices[0].delta.content
                if token:
                    if first_token == False:
                        first_token = True
                        status.append({'type': 'token latency', 'content':f'{time.time() - before_response}'})
                    sentence += token
                if any(p in sentence for p in ['.', '?', '!', ';', ':']):
                    print(sentence)
                    tts(sentence)
                    sentence = ''

            tts(sentence)
            status.append({'type': 'full latency', 'content':f'{time.time() - before_response}'})
            model.reset()
