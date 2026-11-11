import os, subprocess, time, requests

def start_ollama_server():
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    log = open("ollama.log", "w")
    process = subprocess.Popen(["ollama", "serve"], env=env, stdout=log, stderr=subprocess.STDOUT)

    for _ in range(30):
        try:
            if requests.get("http://127.0.0.1:11434/api/tags", timeout=2).ok:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Ollama did not start. Check /tmp/ollama.log")
    print("Ollama is running on localhost:11434")

if __name__=="__main__":
    start_ollama_server()