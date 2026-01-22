import argparse
import time

from faster_whisper import WhisperModel

from podcast_agents.config import AUDIO_DIR, TRANSCRIPTS_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe an audio file.")
    parser.add_argument(
        "-n",
        "--number",
        type=str,
        required=True,
        help="episode number (e.g. 12)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    model_size = "small"
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    input_path = AUDIO_DIR / f"{args.number}.wav"
    if not input_path.is_file():
        raise RuntimeError(f"Input file not found: {input_path}")

    print(f"Starting transcription: {input_path}")
    transcription_start = time.perf_counter()
    segments, _ = model.transcribe(
        str(input_path),
        beam_size=5,
    )

    output_path = TRANSCRIPTS_DIR / f"{args.number}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            f.write(f"{segment.text}\n")

    transcription_duration = time.perf_counter() - transcription_start
    print(f"Transcription time: {transcription_duration:.2f} seconds")


if __name__ == "__main__":
    main()
