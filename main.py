import json
import time
from time import sleep

import requests
from tenacity import retry, wait_fixed
from lxml import etree
from lxml.html import fromstring

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 " \
             "Safari/537.36"


class ForumScraper:
    def __init__(self, url, cookie, prod=True):
        self.prod = prod
        self.payload = {}
        self.url = url
        self.ses = requests.Session()
        self.ses.headers.update({"user-agent": USER_AGENT})
        if prod:
            self.ses.cookies.update({"xf_user": cookie})
        else:
            self.ses.cookies.update({"2213_user": cookie})
        self.get_authorization()

    def get_authorization(self):
        try:
            res = self.ses.get(self.url)
            if res.status_code > 303:
                print("error at forum request, code:", res.status_code)
                raise Exception("error: forum request error")
            # print(res.text[397:550])
            html = fromstring(res.content)
            self.payload['_xfToken'] = html.find('.//input[@name="_xfToken"]').value
        except AttributeError:
            raise Exception("error: not logged in!")

    def reply(self, thread_id, response):
        if self.prod:
            url = f"{self.url}/threads/{thread_id}/add-reply"
        else:
            url = f"{self.url}?threads/{thread_id}/add-reply"
        self.payload["message_html"] = response
        self.ses.post(url, data=self.payload)


def format_response(position, artist, title, cover):
    return f"""<p style="text-align: center;">as 500 mais da <strong><span style="color: rgb(184, 49, 47);">Kiss
    FM</span></strong></p><p style="text-align: center;"><strong id="isPasted">ouça AO VIVO:</strong></p><p
    style="text-align: center;"><a href="https://kissfm.com.br/ao-vivo/" target="_blank"
    rel="noopener"><u><strong>https://kissfm.com.br/ao-vivo/</strong></u></a></p><p style="text-align:
    center;"><br></p><p id="isPasted" style="text-align: center;"><strong><span style="font-size: 18px;">POSIÇÃO N#
    {position}</span></strong></p><p style="text-align: center;">banda<strong>: {artist}</strong></p><p
    style="text-align: center;">musica : <strong> {title}</strong></p><p style="text-align: center;"><br></p><p
    style="text-align: center;"><u><strong><img src="{cover}" class="fr-fic fr-dii" style="width:
    250px;"></strong></u><br></p>"""


def get_cover(artist, title):
    res = requests.get(
        f"https://itunes.apple.com/search?term={artist}%20{title}&media=music&entity=song&limit=1&explicit=Yes"
    )
    if res.status_code != 200:
        print("warning itunes cover error")
        return "https://kissfm.com.br/wp-content/themes/KISSFM/img/logofot.png"
    reson = res.json()
    if reson["results"]:
        return reson["results"][0]["artworkUrl100"].replace("/100x100bb.jpg", "/500x500bb.jpg")
    return "https://kissfm.com.br/wp-content/themes/KISSFM/img/logofot.png"


def check_timestamp(timestamp):
    current_time = int(time.time())
    timestamp = int(timestamp)
    time_difference = current_time - timestamp
    if 0 < time_difference <= 30:
        remaining_seconds = 30 - time_difference
        return remaining_seconds
    else:
        return 0



def load_conf():
    try:
        with open("conf.json", 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        return {"stamp": 0, "position": 500}


def save_conf(data):
    with open("conf.json", 'w') as file:
        json.dump(data, file, indent=2)


def get_track():
    infos = {}
    req = requests.get(
        "https://np.tritondigital.com/public/nowplaying?mountName=RADIO_KISSFM&numberToFetch=1&eventType=track")
    # print(req.status_code)
    if req.status_code != 200:
        raise Exception("get_track error")
    # print(req.text)
    root = etree.fromstring(req.content)
    selectors = [
        '//nowplaying-info/@timestamp',
        '//property[@name="cue_title"]/text()',
        '//property[@name="track_artist_name"]/text()'
    ]
    for index, info in enumerate(["timestamp", "title", "artist"]):
        item = root.xpath(selectors[index])
        infos[info] = item[0] if item else ""
    return infos


def main(forum_scraper, thread):
    track_info = get_track()
    conf = load_conf()
    print(track_info, conf)
    prev_stamp = conf["stamp"]
    actual_stamp = track_info["timestamp"]
    if prev_stamp == 0 or prev_stamp != actual_stamp:
        position = conf["position"] - 1
        time_flood = check_timestamp(prev_stamp)
        if time_flood:
            sleep(time_flood)
        artist = track_info["artist"]
        title = track_info["title"]
        cover = get_cover(artist, title)
        print("poste!", artist, title)
        forum_scraper.reply(thread, format_response(position, artist, title, cover))
        if position == 1:
            exit()
        save_conf({"stamp": actual_stamp, "position": position})


@retry(wait=wait_fixed(10))
def run(url, cookie, thread, prod=True):
    fs = ForumScraper(url, cookie, prod)
    while True:
        main(fs, thread)
        sleep(10)


url1 = "https://6a596cadec0edb75.demo-xenforo.com/2213/index.php"
url2 = "https://www.ignboards.com"
cookie1 = "2,iLRxvPg_1uAU0YyXf-D1cD7RwjmUYhsusbshdhdhxhx" # test '2213_user cookie
cookie2 = "96576647,gsgsgGujHs6263hdhdhdhdhdbdhsjxjisbe" # ign 'xf_user' cookie from browser

# run(url1, cookie1, "1", False) # test: create a xenforo demo on: https://xenforo.com/demo/

run(url2, cookie2, "456723641", True)
 
