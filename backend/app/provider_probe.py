from __future__ import annotations

import argparse
import getpass
import io
import wave


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe an OpenAI-compatible transcription provider without storing credentials.")
    parser.add_argument("--provider", choices=["nvidia", "compatible"], default="nvidia")
    parser.add_argument("--base-url", default="https://integrate.api.nvidia.com/v1")
    parser.add_argument("--model", default="openai/whisper-large-v3")
    parser.add_argument("--server", default="grpc.nvcf.nvidia.com:443")
    parser.add_argument("--function-id", default="b702f636-f60c-4a3d-a6f4-f3568c13bd7d")
    parser.add_argument("--language-code", default="multi")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    api_key = args.api_key or getpass.getpass("API key: ")
    if args.provider == "nvidia":
        _probe_nvidia(api_key, args)
    else:
        _probe_compatible(api_key, args)


def _probe_compatible(api_key: str, args: argparse.Namespace) -> None:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Install backend requirements first: python -m pip install -r backend/requirements.txt") from exc

    client = OpenAI(api_key=api_key, base_url=args.base_url.rstrip("/") + "/")
    print(f"Base URL: {args.base_url}")
    print(f"Model: {args.model}")

    try:
        models = client.models.list()
        ids = [item.id for item in getattr(models, "data", [])][:20]
        print("Models endpoint: ok")
        if ids:
            print("First models:")
            for model_id in ids:
                print(f"- {model_id}")
    except Exception as exc:  # noqa: BLE001 - probe output.
        print(f"Models endpoint: failed: {exc}")

    try:
        audio = _silent_wav()
        response = client.audio.transcriptions.create(
            model=args.model,
            file=("probe.wav", audio, "audio/wav"),
            response_format="verbose_json",
        )
        print("Audio transcription endpoint: ok")
        text = getattr(response, "text", None) if not isinstance(response, dict) else response.get("text")
        segments = getattr(response, "segments", None) if not isinstance(response, dict) else response.get("segments")
        words = getattr(response, "words", None) if not isinstance(response, dict) else response.get("words")
        print(f"Text field: {'yes' if text is not None else 'no'}")
        print(f"Segments field: {'yes' if segments is not None else 'no'}")
        print(f"Words field: {'yes' if words is not None else 'no'}")
    except Exception as exc:  # noqa: BLE001 - probe output.
        print(f"Audio transcription endpoint: failed: {exc}")


def _probe_nvidia(api_key: str, args: argparse.Namespace) -> None:
    try:
        import riva.client
    except ImportError as exc:
        raise SystemExit("Install backend requirements first: python -m pip install -r backend/requirements.txt") from exc

    print(f"Server: {args.server}")
    print(f"Function ID: {args.function_id}")
    print(f"Language: {args.language_code}")
    try:
        auth = riva.client.Auth(
            use_ssl=True,
            uri=args.server,
            metadata_args=[
                ["function-id", args.function_id],
                ["authorization", f"Bearer {api_key}"],
            ],
        )
        asr_service = riva.client.ASRService(auth)
        config = riva.client.RecognitionConfig(
            language_code=args.language_code,
            max_alternatives=1,
            enable_automatic_punctuation=True,
            verbatim_transcripts=True,
            enable_word_time_offsets=True,
        )
        response = asr_service.offline_recognize(_silent_wav().read(), config)
        results = list(getattr(response, "results", []))
        words = []
        if results and getattr(results[0], "alternatives", []):
            words = list(getattr(results[0].alternatives[0], "words", []))
        print("NVIDIA Riva gRPC endpoint: ok")
        print(f"Results field: {'yes' if results else 'no'}")
        print(f"Words field: {'yes' if words else 'no'}")
    except Exception as exc:  # noqa: BLE001 - probe output.
        print(f"NVIDIA Riva gRPC endpoint: failed: {exc}")


def _silent_wav() -> io.BytesIO:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * 16_000)
    buffer.seek(0)
    return buffer


if __name__ == "__main__":
    main()
