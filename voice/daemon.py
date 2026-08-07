import os
import re
import uuid
import time
import json
import zipfile
import urllib.request
import requests
import queue
import sys
import subprocess

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
    # No initialization needed for PowerShell TTS
    return None

def speak(engine, text):
    clean_text = strip_markdown(text)
    print(f"[JARVIS SPEAKS]: {clean_text}")
    # Escape single quotes and double quotes to prevent PowerShell syntax errors
    ps_text = clean_text.replace("'", "''").replace('"', '\"')
    
    ps_cmd = (
        'Add-Type -AssemblyName System.Speech; '
        '$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
        '$synth.Rate = 2; '
        f'$synth.Speak(\'{ps_text}\')'
    )
    # Run synchronously so it waits until speech is finished
    subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
        
def clear_queue(q):
    """Empty the audio queue so Jarvis doesn't hear his own echo"""
    with q.mutex:
        q.queue.clear()

def download_model_if_missing():
    model_dir = os.path.join(os.path.dirname(__file__), "..", "data", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "vosk-model-small-en-us-0.15")
    
    if not os.path.exists(model_path):
        print("[DAEMON] Downloading Vosk model (40MB)... This will only happen once.")
        zip_path = os.path.join(model_dir, "model.zip")
        url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        urllib.request.urlretrieve(url, zip_path)
        print("[DAEMON] Extracting model...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        os.remove(zip_path)
        print("[DAEMON] Model ready!")
    return model_path

def listen_loop():
    model_path = download_model_if_missing()
    
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd
    
    model = Model(model_path)
    recognizer = KaldiRecognizer(model, FS)
    
    engine = init_tts()
    
    q = queue.Queue()

    def callback(indata, frames, time, status):
        """This is called for each audio block by sounddevice"""
        if status:
            print(status, file=sys.stderr)
        q.put(bytes(indata))
        
    print("[DAEMON] Ready! Listening for wake word: 'Jarvis'")
    speak(engine, "Jarvis daemon is online and listening in the background.")

    with sd.RawInputStream(samplerate=FS, blocksize=8000, device=None, dtype='int16',
                           channels=1, callback=callback):
        waiting_for_followup = False
        while True:
            try:
                data = q.get()
                if recognizer.AcceptWaveform(data):
                    print("") # New line after partials
                    res = json.loads(recognizer.Result())
                    text = res.get("text", "")
                    
                    if not text:
                        continue
                        
                    print(f"[DAEMON] Heard: '{text}'")
                    
                    if waiting_for_followup:
                        if text:
                            process_command(text, engine)
                        waiting_for_followup = False
                        continue
                        
                    # Some Vosk models might transcribe it as travis, garbage, etc, but we look for jarvis
                    if "jarvis" in text or "travis" in text or "darvis" in text:
                        # Extract the command after the wake word
                        if "jarvis" in text:
                            parts = text.split("jarvis", 1)
                        elif "travis" in text:
                            parts = text.split("travis", 1)
                        else:
                            parts = text.split("darvis", 1)
                            
                        command = parts[1].strip()
                        
                        if command:
                            process_command(command, engine)
                            clear_queue(q)
                        else:
                            speak(engine, "Yes, sir?")
                            waiting_for_followup = True
                            clear_queue(q)
                else:
                    # Print partial results so the user can see it's listening
                    partial_res = json.loads(recognizer.PartialResult())
                    partial_text = partial_res.get("partial", "")
                    if partial_text:
                        print(f"\r[DAEMON] Hearing: {partial_text}", end="", flush=True)
                            
            except KeyboardInterrupt:
                print("\n[DAEMON] Shutting down.")
                speak(engine, "Shutting down the voice daemon.")
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    listen_loop()
