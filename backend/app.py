from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import fitz
from dotenv import load_dotenv
import os
import yt_dlp
from faster_whisper import WhisperModel

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

print("🚀 Starting AI Backend...")

# ----------------- ENV -----------------
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError("❌ API KEY not found")
else:
    print("✅ API Key Loaded")

# ----------------- FLASK -----------------
app = Flask(__name__)
CORS(app)

# ----------------- WHISPER -----------------
print("⏳ Loading Whisper model...")
model = WhisperModel("tiny", compute_type="int8")
print("✅ Whisper Ready")

# ----------------- OPENROUTER -----------------
def get_summary(prompt):
    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "AI Summarizer"
            },
            json={
               
                "model": "openai/gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 1200,
                "messages": [
                    {"role": "system", "content": "You are an expert AI writer. Always follow instructions strictly. Write natural, human-like output."},
                    {"role": "user", "content": prompt[:6000]}
                ]
            },
            timeout=60
        )

        data = res.json()

        if "choices" not in data:
            return data.get("error", {}).get("message", "API error")

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return str(e)

# ----------------- VIDEO ID -----------------
def get_video_id(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""

    if host == "youtu.be":
        return parsed.path.lstrip("/")

    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/")[1].split("/")[0]

    return None

# ----------------- AUDIO -----------------
def download_audio(url):
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': 'audio.%(ext)s',
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def audio_to_text(path):
    segments, _ = model.transcribe(path, beam_size=1, vad_filter=True)
    return " ".join([s.text for s in segments])

# ----------------- TRANSCRIPT -----------------
def get_transcript(video_id):
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([i['text'] for i in data])
    except:
        return None

def get_audio_transcript(video_id, url):
    path = download_audio(url)
    text = audio_to_text(path)

    if os.path.exists(path):
        os.remove(path)

    return text

# ----------------- TEXT -----------------
@app.route('/summarize/text', methods=['POST'])
def summarize_text():
    data = request.get_json()

    # ✅ FIX 1: JSON check
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    text = data.get("text")
    language = data.get("language", "English")

    # ✅ FIX 2: Empty text check
    if not text or not text.strip():
        return jsonify({"error": "No text"}), 400

    text = text[:2000]

    prompt = f"""
You are an expert summarizer and teacher.

IMPORTANT:
- Generate output ONLY in {language}.
- Do NOT use Bengali, Hindi, or any other language.
- Even if the input text contains Bengali, write the summary entirely in {language}.

GOAL:
Create a clear, high-quality, and meaningful summary that helps in quick understanding and revision.

INSTRUCTIONS:
- First understand the full meaning of the text
- Then extract only the most important ideas
- Do NOT just shorten sentences — rewrite intelligently

OUTPUT FORMAT:
- 5 to 8 bullet points
- Each point should express ONE clear idea
- Each sentence max 18 words (slightly flexible for clarity)

QUALITY RULES:
- Start each point with a **bold keyword**
- Avoid repetition
- Keep flow logical (general → specific)
- Focus on key concepts, facts, and insights
- Remove unnecessary details, examples, and filler content

WRITING STYLE:
- Simple, natural, human-like
- Easy to read and revise
- Slightly explanatory, not just keywords

TEXT:
{text}
"""
    return jsonify({"summary": get_summary(prompt)})

# ----------------- PDF SUMMARY -----------------
@app.route('/summarize/pdf', methods=['POST'])
def summarize_pdf():
    try:
        file = request.files['file']
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = "".join([p.get_text() for p in doc])[:3000]

        prompt = f"""
You are an expert AI summarizer.

TASK:
Create a structured summary.

RULES:
- 5–8 bullet points
- Each sentence max 14 words
- Each must include **bold keyword**
- No repetition
- Natural writing style

IF BENGALI:
- Natural Bengali (not translation)

TEXT:
{text}
"""
        return jsonify({"summary": get_summary(prompt)})

    except:
        return jsonify({"error": "PDF failed"}), 500

# ----------------- RESEARCH TABLE -----------------
def split_text(text, chunk_size=2000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def generate_research_table(text, language, mode="chunk"):

    if mode == "chunk":
        prompt = f"""
Create a clean research table.

Columns:
Author | Sample | Title | Source | Findings | Model | Year

RULES:
- Each cell max 6 words
- No long sentences
- Use N/A if missing
- Only table output

Language: {language}

TEXT:
{text}
"""
    else:
        prompt = f"""
Improve and clean the table.

RULES:
- Remove duplicates
- Keep 8–10 best rows
- Very short cells only

Output ONLY table.

Language: {language}

DATA:
{text}
"""
    return get_summary(prompt)

@app.route('/generate/research-table', methods=['POST'])
def research_table():
    try:
        file = request.files['file']
        doc = fitz.open(stream=file.read(), filetype="pdf")
        full_text = "".join([p.get_text() for p in doc])

        chunks = split_text(full_text)
        all_tables = []

        for chunk in chunks[:2]:
            result = generate_research_table(chunk, "English", "chunk")
            all_tables.append(result)

        combined = "\n\n".join(all_tables)
        final_result = generate_research_table(combined, "English", "final")

        return jsonify({"table": final_result})

    except:
        return jsonify({"error": "Table generation failed"}), 500

# ----------------- YOUTUBE -----------------
@app.route('/summarize/youtube', methods=['POST'])
def summarize_youtube():
    try:
        data = request.get_json()
        url = data.get("url")

        vid = get_video_id(url)
        if not vid:
            return jsonify({"error": "Invalid URL"}), 400

        text = get_transcript(vid) or get_audio_transcript(vid, url)

        chunks = [text[i:i+1500] for i in range(0, len(text), 1500)]
        partials = []

        for chunk in chunks:
            prompt = f"""
Summarize clearly.

RULES:
- Bullet points
- Max 14 words per sentence
- Use **bold keywords**
- No repetition
- Natural writing

TEXT:
{chunk}
"""
            partials.append(get_summary(prompt))

        final = get_summary(f"""
Create final structured summary.

RULES:
- 8–12 bullet points
- Remove repetition
- Smooth flow
- Use **bold keywords**

{''.join(partials)}
""")

        return jsonify({
            "summary": final,
            "thumbnail": f"https://img.youtube.com/vi/{vid}/0.jpg"
        })

    except:
        return jsonify({"error": "YT failed"}), 500

# ----------------- NOTES -----------------
# ----------------- NOTES -----------------
@app.route('/generate/notes', methods=['POST'])
def generate_notes():
    try:
        data = request.get_json()
        summary = data.get("summary", "")
        language = data.get("language", "English")

        prompt = f"""
You are a TOP-level exam note-maker.

IMPORTANT:
- Generate output ONLY in {language}.
- Do NOT use Bengali, Hindi, or any other language.
- Even if the input text is in Bengali, translate the ideas and write the notes entirely in {language}.

Your task is to convert the given content into high-quality, exam-oriented study notes.

GOAL:
- Make notes that help in revision + writing answers in exams
- Clear, structured, and easy to memorize

OUTPUT FORMAT (STRICT):

1. **Title**
(Short, clear topic name)

2. **Overview**
(2–3 lines summary of the topic)

3. **Key Concepts**
- Use bullet points
- Highlight **important terms**

4. **Detailed Explanation**
- Explain concepts clearly
- Break into small paragraphs
- Each paragraph starts with **bold term**
- Keep explanation concise
- Avoid long examples
- Use simple language
- Add examples if helpful

5. **Important Points for Exam**
- Short, crisp bullet points
- Include definitions, facts, keywords
- Highlight **must-remember points**
- Include 1–2 **must-remember** points

6. **Possible Exam Questions**
- 3–5 questions (short + long type)

7. **Conclusion**
- 2–3 lines final summary

WRITING RULES:
- Use simple, human-like language
- Avoid repetition
- Keep sentences short and clear
- Use **bold keywords** for important terms
- Make notes look like written by a smart student

TEXT:
{summary}
"""
        return jsonify({"notes": get_summary(prompt)})

    except:
        return jsonify({"error": "Notes failed"}), 500

# ----------------- TRANSLATE -----------------
@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.get_json()
        text = data.get("text", "")
        target = data.get("target", "Bengali")

        prompt = f"""
Rewrite into {target} naturally.

RULES:
- No word-by-word translation
- Preserve meaning
- Keep formatting
- Human-like language
- Natural Bengali if selected

TEXT:
{text}
"""
        return jsonify({"translated": get_summary(prompt)})

    except:
        return jsonify({"error": "Translate failed"}), 500

# ----------------- HOME -----------------
@app.route('/')
def home():
    return "✅ Backend Running"

# ----------------- RUN -----------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)