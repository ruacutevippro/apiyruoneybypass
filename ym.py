from flask import Flask, request, jsonify
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

app = Flask(__name__)

# Tạo cloudscraper session vượt CAPTCHA
session = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows'})
headers = {"User-Agent": "Mozilla/5.0"}

# Dữ liệu nhiệm vụ mẫu
links = {
    "m88": {"url": "https://bet88ec.com/cach-danh-bai-sam-loc", "ref": "https://bet88ec.com/", "code": "taodeptrai"},
    "fb88": {"url": "https://fb88mg.com/ty-le-cuoc-hong-kong-la-gi", "ref": "https://fb88mg.com/", "code": "taodeptrai"},
    "188bet": {"url": "https://88betag.com/cach-choi-game-bai-pok-deng", "ref": "https://88betag.com/", "code": "taodeptrailamnhe"},
    "w88": {"url": "https://188.166.185.213/tim-hieu-khai-niem-3-bet-trong-poker-la-gi", "ref": "https://188.166.185.213/", "code": "taodeptrai"},
    "v9bet": {"url": "https://v9betho.com/ca-cuoc-the-thao-ao/", "ref": "https://v9betho.com/", "code": "taodeptrai"},
    "vn88": {"url": "https://vn88ie.com/cach-choi-mega-6-45/", "ref": "https://vn88ie.com/", "code": "taodeptrai"},
    "bk8": {"url": "https://bk8ze.com/cach-choi-punto-banco/", "ref": "https://bk8ze.com/", "code": "taodeptrai"},
}

# Hàm theo dõi redirect để lấy link cuối cùng
def follow_redirect_until_out(url, session, headers, max_wait=30):
    waited = 0
    while waited < max_wait:
        resp = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        final_url = resp.url
        domain = urlparse(final_url).netloc
        if domain != "yeumoney.com":
            return final_url
        meta = soup.find("meta", attrs={"http-equiv": lambda x: x and x.lower() == "refresh"})
        if meta and "url=" in meta.get("content", ""):
            url = urljoin(url, meta["content"].split("url=", 1)[1].strip())
            time.sleep(2)
            waited += 2
            continue
        js_match = re.search(r"window\.location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]", resp.text)
        if js_match:
            url = urljoin(url, js_match.group(1))
            time.sleep(2)
            waited += 2
            continue
        break
    return final_url

@app.route('/bypass', methods=['GET'])
def bypass_link():
    link = request.args.get('link')
    task = request.args.get('nv')  # dùng 'nv' thay vì 'nhiemvu'

    if not link or not task or task not in links:
        return jsonify({"error": "Thiếu link hoặc nhiệm vụ không hợp lệ!"}), 400

    try:
        info = links[task]

        # Bước 1: Gửi yêu cầu để lấy mã xác minh
        response = session.post("https://traffic-user.net/GET_MA.php", params={
            "codexn": info["code"],
            "url": info["url"],
            "loai_traffic": info["ref"],
            "clk": 1000
        }, timeout=10)

        match = re.search(r'<span id="layma_me_vuatraffic"[^>]*>\s*(\d+)\s*</span>', response.text)
        if not match:
            return jsonify({"error": "Không lấy được mã xác minh!"}), 500

        code = match.group(1)

        # Bước 2: Truy cập trang rút gọn và lấy form
        page = session.get(link, headers=headers)
        soup = BeautifulSoup(page.text, "html.parser")
        form = soup.find("form")

        if not form:
            return jsonify({"error": "Không tìm thấy form!"}), 500

        action = form.get("action") or link
        if not action.startswith("http"):
            action = urljoin(link, action)

        data = {
            input_tag.get("name"): input_tag.get("value", "")
            for input_tag in form.find_all("input") if input_tag.get("name")
        }
        data["code"] = code

        # Bước 3: Gửi POST xác minh
        verify = session.post(action, data=data, headers=headers, allow_redirects=True)

        # Bước 4: Theo redirect ra khỏi yeumoney
        final_url = follow_redirect_until_out(verify.url, session, headers)

        # Trả về kết quả JSON
        return jsonify({
            "code": code,
            "final_url": final_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
