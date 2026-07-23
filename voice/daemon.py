import os
import re
import uuid
import time
import requests
import pyttsx3
import speech_recognition as sr
import sounddevice as sd
import scipy.io.wavfile as wav
import tempfile

# Configuration
SERVER_URL = "http://127.0.0.1:8000/api/chat"
WAKE_WORD = "jarvis"
SESSION_ID = uuid.uuid4().hex
FS = 16000  # Sample rate

def strip_markdown(text):
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'`{1,3}(.*?)`{1,3}', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'#+\s+(.*)', r'\1', text)
    text = re.sub(r'>\s+(.*)', r'\1', text)
    text = re.sub(r'[-*+]\s+', '', text)
    text = text.replace('\n', ' ')
    return text.strip()

def init_tts():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'Zira' in voice.name or 'David' in voice.name or 'English' in voice.name:
            engine.setProperty('voice', voice.id)
            break
    engine.setProperty('rate', 170)
    return engine

def speak(engine, text):
    clean_text = strip_markdown(text)
    print(f"[JARVIS SPEAKS]: {clean_text}")
    engine.say(clean_text)
    engine.runAndWait()

def process_command(command, engine):
    print(f"\n[DAEMON] Sending command to server: '{command}'")
    try:
        response = requests.post(
            SERVER_URL,
            json={"query": command, "session_id": SESSION_ID},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        result_text = data.get("result", "I did not understand the response.")
        speak(engine, result_text)
    except requests.exceptions.ConnectionError:
        speak(engine, "I cannot connect to the server. Please ensure my brain is running.")
    except Exception as e:
        print(f"[ERROR] {e}")
        speak(engine, "I encountered an error processing your request.")

def record_audio(duration):
    """Record audio using sounddevice to bypass PyAudio build errors on Windows."""
    print("[DAEMON] Listening...")
    recording = sd.rec(int(duration * FS), samplerate=FS, channels=1, dtype='int16')
    sd.wait()
    return recording

def listen_loop():
    recognizer = sr.Recognizer()
    engine = init_tts()
    temp_wav = os.path.join(tempfile.gettempdir(), "jarvis_temp.wav")
    
    print("[DAEMON] Ready! Listening for wake word: 'Jarvis'")
    speak(engine, "Jarvis daemon is online and listening in the background.")

    while True:
        try:
            # Record 5 seconds of audio
            recording = record_audio(5)
            wav.write(temp_wav, FS, recording)

            # Transcribe audio using Google's free API
            with sr.AudioFile(temp_wav) as source:
                audio_data = recognizer.record(source)
            
            try:
                text = recognizer.recognize_google(audio_data).lower()
                print(f"[DAEMON] Heard: '{text}'")

                if WAKE_WORD in text:
                    parts = text.split(WAKE_WORD, 1)
                    command = parts[1].strip()
                    
                    if command:
                        process_command(command, engine)
                    else:
                        speak(engine, "Yes, sir?")
                        # Wait for next command immediately
                        follow_up_recording = record_audio(5)
                        wav.write(temp_wav, FS, follow_up_recording)
                        with sr.AudioFile(temp_wav) as fsource:
                            f_audio_data = recognizer.record(fsource)
                        try:
                            follow_up = recognizer.recognize_google(f_audio_data).lower()
                            print(f"[DAEMON] Follow up: '{follow_up}'")
                            if follow_up:
                                process_command(follow_up, engine)
                        except sr.UnknownValueError:
                            speak(engine, "I didn't catch that.")
            except sr.UnknownValueError:
                # Speech was unintelligible or silence
                pass

        except sr.RequestError as e:
            print(f"[ERROR] Could not request results from Speech Recognition service; {e}")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n[DAEMON] Shutting down.")
            speak(engine, "Shutting down the voice daemon.")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    listen_loop()
