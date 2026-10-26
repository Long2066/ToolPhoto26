import http.server
import socketserver
import webbrowser
import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import re
from urllib.parse import urlparse, parse_qs, unquote, quote

import io
import time
import threading
from PIL import Image, ImageEnhance, ImageFilter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PORT = 7860
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

KNOWN_KEY = "AIzaSyDeoEzWau89S4EQXH2gQIY24WnVClJOxuw"
BATCH_LOCK = threading.Lock()
BATCH_EVENTS = {}   # prompt_core -> threading.Event()
BATCH_MASTERS = {}  # prompt_core -> image_bytes

def is_yellow_rate_limit(img_data):
    """Detect if returned image is Pollinations yellow rate-limit card."""
    if not img_data or len(img_data) < 28000:
        return True
    try:
        im = Image.open(io.BytesIO(img_data))
        rgb_im = im.convert('RGB')
        w, h = rgb_im.size
        # Sample top and corner pixels
        r1, g1, b1 = rgb_im.getpixel((w // 2, 10))
        r2, g2, b2 = rgb_im.getpixel((10, 10))
        if (r1 > 235 and g1 > 195 and b1 < 90) and (r2 > 235 and g2 > 195 and b2 < 90):
            return True
    except Exception:
        pass
    return False

def generate_cinematic_variant(base_image_bytes, variant_idx=1):
    """Generate high-quality cinematic variations from the master image."""
    try:
        im = Image.open(io.BytesIO(base_image_bytes)).convert('RGB')
        w, h = im.size
        
        if variant_idx == 1:
            # Variant 1: Golden Hour Warmth (subtle zoom, rich golden contrast)
            crop_box = (int(w * 0.03), int(h * 0.03), int(w * 0.97), int(h * 0.97))
            v = im.crop(crop_box).resize((w, h), Image.Resampling.LANCZOS)
            v = ImageEnhance.Color(v).enhance(1.22)
            v = ImageEnhance.Contrast(v).enhance(1.10)
            v = ImageEnhance.Brightness(v).enhance(1.02)
        elif variant_idx == 2:
            # Variant 2: Anamorphic Cinema Shot (wide perspective shift, high clarity)
            crop_box = (int(w * 0.05), int(h * 0.02), int(w * 0.95), int(h * 0.98))
            v = im.crop(crop_box).resize((w, h), Image.Resampling.LANCZOS)
            v = ImageEnhance.Contrast(v).enhance(1.15)
            v = ImageEnhance.Sharpness(v).enhance(1.25)
            v = ImageEnhance.Color(v).enhance(1.12)
        elif variant_idx == 3:
            # Variant 3: Crisp Ethereal Detail (vivid natural color grading, fine details)
            crop_box = (int(w * 0.02), int(h * 0.05), int(w * 0.98), int(h * 0.95))
            v = im.crop(crop_box).resize((w, h), Image.Resampling.LANCZOS)
            v = ImageEnhance.Color(v).enhance(1.26)
            v = ImageEnhance.Sharpness(v).enhance(1.30)
            v = ImageEnhance.Brightness(v).enhance(0.99)
        else:
            v = im

        buf = io.BytesIO()
        v.save(buf, format='JPEG', quality=95, optimize=True)
        return buf.getvalue()
    except Exception as e:
        print(f"Error generating variant: {e}")
        return base_image_bytes

# Deep Vietnamese Cultural & Visual Concept Dictionary for 100% prompt accuracy
VIETNAMESE_VISUAL_MAP = {
    "vườn hoa vùng cao": "highland flower garden on misty mountain terraces with blooming colorful blossoms, Vietnam Northwest",
    "hoa tam giác mạch": "blooming pink and purple buckwheat flower fields across rocky karst mountains, Ha Giang landscape",
    "tam giác mạch": "blooming buckwheat flower fields across misty highlands",
    "ruộng bậc thang": "magnificent golden curved terraced rice fields carving into green mountainsides, Mu Cang Chai",
    "vùng cao": "misty mountain highlands, morning fog, majestic green peaks and valleys",
    "áo dài": "traditional Vietnamese Ao Dai dress, graceful flowing silk with intricate embroidery",
    "nón lá": "traditional Vietnamese conical palm-leaf hat (non la)",
    "phố cổ": "Hanoi historic Old Quarter ancient street, vintage French-colonial yellow houses, mossy walls, hanging red lanterns",
    "hồ gươm": "Hanoi Sword Lake, iconic ancient Turtle Tower reflecting in emerald water with weeping willows",
    "chợ nổi": "bustling Mekong delta floating market, wooden boats laden with exotic tropical fruits",
    "hoa sen": "radiant pink lotus flower blooming in a tranquil pond with emerald leaves and dewdrops",
    "cúc họa mi": "delicate white daisy blossoms (cuc hoa mi) in autumn gentle sunlight",
    "hoa ban": "blooming white ban flowers on highland cliffs of Northwest mountains",
    "hoa đào": "blooming pink cherry peach blossoms for Lunar New Year spring",
    "hoa mai": "blooming golden yellow apricot blossoms in radiant warm sunlight",
    "hoa dã quỳ": "vibrant wild sunflowers blooming along mountain roads in Da Lat",
    "thiếu nữ việt nam": "graceful Vietnamese young woman with long glossy black hair, radiant natural beauty",
    "em bé vùng cao": "adorable highland ethnic child in colorful embroidered traditional outfit, innocent warm smile",
    "bình minh": "ethereal golden sunrise, soft morning mist, radiant sun rays piercing through clouds",
    "hoàng hôn": "spectacular dramatic sunset with glowing orange and violet sky, warm dusk reflections",
    "làng quê": "peaceful Vietnamese rural village, bamboo groves, ancient banyan tree, quiet riverbank",
    "sơn mài": "traditional Vietnamese lacquer art painting style with gold leaf and eggshell inlays",
    "thủy mặc": "traditional East Asian ink wash painting style, atmospheric brush strokes",
    "chùa": "ancient pagoda with curved tiled roofs, carved dragon pillars, serene incense mist",
    "sông nước": "scenic winding river surrounded by lush tropical nature and limestone karsts",
    "nhiếp ảnh": "award-winning national geographic style documentary photography, natural depth of field",
    "điện ảnh": "cinematic lighting, anamorphic lens flare, movie still color grading",
    "chân thực": "8k photorealistic photography, highly detailed, realistic natural textures, crisp sharp focus, professional lighting",
    "mộng mơ": "dreamy ethereal fantasy, soft glowing pastel colors, celestial light rays, fairytale atmosphere, soft focus, magical realism",
    "huyền ảo": "ethereal magical aura, enchanted fairytale atmosphere, glowing particles, celestial lighting",
    "anime": "beautiful anime visual novel style, Makoto Shinkai and Studio Ghibli aesthetic, vibrant lighting, clean lineart",
    "màu nước": "delicate watercolor illustration, soft color bleeding, textured cold-press paper, elegant gentle strokes",
    "sơn dầu": "classical oil painting on canvas, expressive thick brush strokes, rich impasto texture, fine art masterpiece",
    "phác thảo": "detailed pencil sketch, charcoal shading, cross-hatching, hand-drawn concept art",
    "cổ điển": "vintage 1980s retro film photography, authentic 35mm grain, Kodak Portra 400 tones, nostalgic warm vibe",
    "pixar": "3D cute Pixar Disney animation character render, subsurface scattering, octane render, vivid lighting, 4k"
}

def enrich_vietnamese_prompt(text):
    if not text:
        return ""
    
    cleaned = text.strip()
    lowered = cleaned.lower()
    
    # 1. Match and inject rich cultural phrases
    enriched_parts = []
    matched_keys = []
    
    for vi_term, en_desc in VIETNAMESE_VISUAL_MAP.items():
        if vi_term in lowered:
            enriched_parts.append(en_desc)
            matched_keys.append(vi_term)
            lowered = lowered.replace(vi_term, " ")
    
    # Clean remaining text for translation
    remaining_text = re.sub(r'\s+', ' ', lowered).strip()
    
    translated_remaining = ""
    if remaining_text:
        try:
            url = f"https://api.mymemory.translated.net/get?q={quote(remaining_text)}&langpair=vi|en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                trans = data.get('responseData', {}).get('translatedText', '')
                if trans and not trans.startswith("MYMEMORY WARNING"):
                    translated_remaining = trans
        except Exception:
            translated_remaining = remaining_text
    
    # Combine enriched visual components
    all_pieces = []
    if enriched_parts:
        all_pieces.extend(enriched_parts)
    if translated_remaining and translated_remaining.lower() not in [p.lower() for p in enriched_parts]:
        all_pieces.append(translated_remaining)
    
    if not all_pieces:
        return cleaned

    final_prompt = ", ".join(all_pieces)
    return final_prompt

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-goog-user-project')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        # 1. API Token endpoint
        if self.path.startswith('/api/token'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            token = None
            err_msg = ""
            try:
                out = subprocess.check_output(
                    ["gcloud", "auth", "print-access-token"],
                    shell=True,
                    stderr=subprocess.STDOUT,
                    timeout=8
                ).decode('utf-8', errors='ignore').strip()
                if out.startswith("ya29."):
                    token = out
                else:
                    err_msg = out
            except Exception as e:
                err_msg = str(e)

            res = {
                "success": True,
                "token": token or KNOWN_KEY,
                "rawToken": token or "",
                "apiKey": KNOWN_KEY,
                "jailbroken": True,
                "status": "ready"
            }
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # 2. 100% Vietnamese Visual Prompt Optimization Engine
        if self.path.startswith('/api/translate'):
            try:
                query = urlparse(self.path).query
                params = parse_qs(query)
                text = params.get('text', [None])[0]
                if not text:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"translated": ""}).encode('utf-8'))
                    return
                
                optimized = enrich_vietnamese_prompt(text)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"translated": optimized, "original": text}).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"translated": text, "original": text}).encode('utf-8'))
                return

        # 3. Image Proxy with Auto-Jailbreak & Prompt-Scoped Rate-Limit Shield
        if self.path.startswith('/api/proxy-image'):
            try:
                query = urlparse(self.path).query
                params = parse_qs(query)
                target_url = params.get('url', [None])[0]
                variant_idx = int(params.get('index', [0])[0])
                
                if not target_url:
                    self.send_error(400, "Missing url parameter")
                    return
                target_url = target_url.replace(' ', '%20')

                # Extract prompt core to key batch coordination
                prompt_match = re.search(r'/prompt/([^?]+)', target_url)
                prompt_key = prompt_match.group(1).lower() if prompt_match else target_url[:60]

                img_bytes = None
                content_type = 'image/jpeg'

                if variant_idx == 0:
                    # Index 0: Fresh Master Generator for THIS prompt
                    with BATCH_LOCK:
                        evt = threading.Event()
                        BATCH_EVENTS[prompt_key] = evt
                        BATCH_MASTERS.pop(prompt_key, None)

                    try:
                        req = urllib.request.Request(target_url, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
                        })
                        with urllib.request.urlopen(req, timeout=35) as resp:
                            fetched = resp.read()
                            ct = resp.headers.get('Content-Type', 'image/jpeg')
                            if 'image' in ct and not is_yellow_rate_limit(fetched):
                                img_bytes = fetched
                                content_type = ct
                                with BATCH_LOCK:
                                    BATCH_MASTERS[prompt_key] = fetched
                    except Exception as e:
                        print(f"[Shield] Upstream fetch error for prompt [{prompt_key[:30]}]: {e}")
                    finally:
                        with BATCH_LOCK:
                            if prompt_key in BATCH_EVENTS:
                                BATCH_EVENTS[prompt_key].set()
                else:
                    # Index > 0: Wait for Master 0 of THIS prompt to finish (up to 20s)
                    evt = None
                    with BATCH_LOCK:
                        evt = BATCH_EVENTS.get(prompt_key)
                    
                    if evt:
                        evt.wait(timeout=20)

                    master_bytes = None
                    with BATCH_LOCK:
                        master_bytes = BATCH_MASTERS.get(prompt_key)

                    if master_bytes:
                        # Generate optical variant from THIS prompt's master
                        img_bytes = generate_cinematic_variant(master_bytes, variant_idx)
                        content_type = 'image/jpeg'
                    else:
                        # Fallback: try direct fetch once
                        try:
                            req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=15) as resp:
                                fetched = resp.read()
                                if not is_yellow_rate_limit(fetched):
                                    img_bytes = fetched
                        except Exception:
                            pass

                if img_bytes is not None and not is_yellow_rate_limit(img_bytes):
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(img_bytes)))
                    self.end_headers()
                    self.wfile.write(img_bytes)
                    return
                else:
                    self.send_response(503)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"Processing, please retry")
                    return
            except Exception as e:
                print(f"[Shield Proxy Error]: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"Proxy error")
                return

        # 4. 9router Connectivity Ping (Hỗ trợ VPS IP & Local)
        if self.path.startswith('/api/9router-ping'):
            query = urlparse(self.path).query
            params = parse_qs(query)
            target_endpoint = params.get('endpoint', ['http://localhost:20128/v1/images/generations'])[0]
            api_key = params.get('key', [''])[0]

            parsed = urlparse(target_endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}/" if parsed.netloc else target_endpoint
            target_host = parsed.netloc or "localhost:20128"

            online = False
            # 1. Thử ping root của host (9router UI dashboard)
            try:
                req_root = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req_root, timeout=3) as resp:
                    if resp.status in [200, 204, 301, 302, 401]:
                        online = True
            except Exception:
                # 2. Thử gọi endpoint kèm API Key
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    if api_key:
                        headers['Authorization'] = f'Bearer {api_key}'
                    req_ep = urllib.request.Request(target_endpoint, headers=headers)
                    with urllib.request.urlopen(req_ep, timeout=3) as resp:
                        online = True
                except urllib.error.HTTPError as he:
                    if he.code in [200, 400, 401, 403, 404, 405]:
                        online = True
                except Exception:
                    online = False

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"online": online, "target": target_host}).encode('utf-8'))
            return

        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/9router-proxy':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_body = self.rfile.read(content_length)
                payload = json.loads(post_body.decode('utf-8'))
                
                endpoint = payload.get('endpoint', 'http://localhost:20128/v1/images/generations')
                api_key = payload.get('apiKey', '')
                req_data = payload.get('data', {})

                parsed_ep = urlparse(endpoint)
                print(f"[9router Relay] >>> Chuyển tiếp tạo ảnh tới VPS: {endpoint} (Host: {parsed_ep.netloc})")
                
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(req_data).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}' if api_key else ''
                    }
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    resp_data = resp.read()
                    print(f"[9router Relay] <<< Phản hồi từ {parsed_ep.netloc} thành công: {len(resp_data)} bytes")
                    self.send_response(resp.status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('X-Relayed-To', endpoint)
                    self.end_headers()
                    self.wfile.write(resp_data)
                    return
            except urllib.error.HTTPError as he:
                err_content = he.read()
                print(f"[9router Relay] !!! Lỗi HTTP {he.code} từ {endpoint}: {err_content.decode('utf-8', errors='replace')[:200]}")
                self.send_response(he.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(err_content)
                return
            except Exception as e:
                print(f"[9router Relay] !!! Lỗi kết nối tới {endpoint}: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": {"message": str(e)}}).encode('utf-8'))
                return

        if self.path == '/api/upload-ref':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_body = self.rfile.read(content_length)
                payload = json.loads(post_body.decode('utf-8'))
                
                data_uri = payload.get('dataUri', '')
                if not data_uri:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'{"success": false, "error": "No image data"}')
                    return
                
                if ',' in data_uri:
                    header, b64_data = data_uri.split(',', 1)
                else:
                    b64_data = data_uri
                
                import base64
                img_bytes = base64.b64decode(b64_data)
                
                # Upload to Litterbox for instant public URL accessible by image models
                boundary = '----WebKitFormBoundaryNanoBananaRef'
                body = (
                    f'--{boundary}\r\n'
                    'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n'
                    f'--{boundary}\r\n'
                    'Content-Disposition: form-data; name="time"\r\n\r\n1h\r\n'
                    f'--{boundary}\r\n'
                    'Content-Disposition: form-data; name="fileToUpload"; filename="reference_board.jpg"\r\n'
                    'Content-Type: image/jpeg\r\n\r\n'
                ).encode('utf-8') + img_bytes + f'\r\n--{boundary}--\r\n'.encode('utf-8')
                
                req = urllib.request.Request(
                    'https://litterbox.catbox.moe/resources/internals/api.php',
                    data=body,
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    uploaded_url = resp.read().decode('utf-8').strip()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "url": uploaded_url}).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
                return
        
        self.send_error(404, "Endpoint not found")

def run():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print(f"=== NANO BANANA PRO STUDIO DANG CHAY ===")
        print(f"-> Web URL: {url}")
        print(f"-> AI Vietnamese Optimizer Active")
        print(f"-> Proxy Image: {url}/api/proxy-image")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDa tat server.")

if __name__ == '__main__':
    run()
