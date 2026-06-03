# Rinon Voice Lab

Local prototype chat app that connects LM Studio, Irodori-TTS VoiceDesign, and a simple animated character UI.

## Assumptions

- LM Studio OpenAI-compatible API: `http://127.0.0.1:1234/v1`
- Irodori-TTS install: `H:\AI\Irodori-TTS`
- Default model: `gemma-4-31b-it`
- App URL: `http://127.0.0.1:7862/`

## Run

```powershell
H:\AI\Irodori-TTS\.venv\Scripts\python.exe app.py
```

## Notes

- Generated temporary audio is written to `static/generated/` and ignored by Git.
- Saved audio is written to `saved_audio/` and ignored by Git.
- Chat/session saves are local runtime data and ignored by Git.
