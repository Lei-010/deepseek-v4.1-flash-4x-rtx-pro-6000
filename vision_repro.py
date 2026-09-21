"""Reproduce the vision math-domain-error and capture full traceback."""
import json, urllib.request, base64, io, traceback

KEY = open("/state/api-key").read().strip()

def req(body, timeout=300):
    r = urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:2000]}

from PIL import Image, ImageDraw
image = Image.new("RGB", (3024, 588), "white")
d = ImageDraw.Draw(image)
d.ellipse((200, 100, 588, 488), fill="red")
d.rectangle((2400, 100, 2788, 488), fill="blue")
buf = io.BytesIO()
image.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode()

out = req({"model": "deepseek-v4.1-flash", "temperature": 0,
    "chat_template_kwargs": {"thinking": False},
    "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Describe the two colored shapes and their left-to-right order. Be concise."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}]})
print(json.dumps(out, ensure_ascii=False)[:3000])
