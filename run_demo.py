import os, sys, threading, time, webbrowser
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:8000')
threading.Thread(target=open_browser,daemon=True).start()
uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
