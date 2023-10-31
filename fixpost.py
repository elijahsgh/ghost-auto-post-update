import sys
import requests
import json
import jwt
from bs4 import BeautifulSoup
import markdown
from secrets import ghost_content_key, ghost_admin_key
import datetime

ghost_site = sys.argv[1]
slug = sys.argv[2]

toc_markdown = """
## Table of Contents

"""

admin_api_url = "/ghost/api/admin"
admin_posts_url = f"{admin_api_url}/posts/"
content_api_url = "/ghost/api/content"
posts_url = f"{content_api_url}/posts/slug/{slug}"
headers = {
    "Accept-Version": "v5.0",
}
params = {"key": ghost_content_key}

result = requests.get(
    f"{ghost_site}{posts_url}",
    headers=headers,
    params=params,
).json()

post_to_update = result['posts'][0]

soup = BeautifulSoup(post_to_update['html'], "html.parser")

excerpt_snippet = soup.find('p').text[:300]
excerpt_text = excerpt_snippet[:excerpt_snippet.rfind('.')+1]

soup.find('h1').decompose()

results = soup.select("h2, h3, h4")

for r in results:
    toc_indent = ""

    match r.name:
        case "h2":
            toc_indent = "\n- "
        case "h3":
            toc_indent = "\t- "
        case "h5":
            toc_indent = "\t\t- "
        case _:
            pass

    ref_text = r.text.replace(' ', '-').lower()

    toc_item = f"{toc_indent}[{r.text}](#{ref_text})\n\n"
    r.attrs['id'] = ref_text

    toc_markdown += toc_item

tocsoup = BeautifulSoup(markdown.markdown(toc_markdown), "html.parser")

first_h2 = soup.find('h2')
first_h2.insert_before(tocsoup)

id, secret = ghost_admin_key.split(':')

iat = int(datetime.datetime.now().timestamp())
header = {'alg': 'HS256', 'typ': 'JWT', 'kid': id}

payload = {
    'iat': iat,
    'exp': iat + 5 * 60,
    'aud': '/admin/'
}

token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

put_result = requests.put(f"{ghost_site}{admin_posts_url}{post_to_update['id']}/",
    headers = {
        "Authorization": f"Ghost {token}",
        "Accepted-Version": "v5.0"
    },
    json = {
        "posts": [
            {
                "updated_at": post_to_update['updated_at'],
                "html": str(soup),
                "custom_excerpt": excerpt_text,
            }
        ]
    },
    params = {
        "source": "html"
    }
)

print(f"Put result {put_result.status_code} {put_result.text}")
