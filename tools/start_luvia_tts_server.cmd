@echo off
cd /d E:\AI\Irodori-TTS
if not exist outputs mkdir outputs
E:\AI\Irodori-TTS\.venv\Scripts\python.exe E:\AI\Irodori-TTS\remote_luvia_tts_server.py >> E:\AI\Irodori-TTS\outputs\remote_luvia_server.out.log 2>> E:\AI\Irodori-TTS\outputs\remote_luvia_server.err.log
