# Standard library imports
import os
import sys
import webbrowser
from urllib.parse import quote
from datetime import datetime, timezone
import re
import termios
import tty
from io import BytesIO

# Third-party imports
import requests
import json
from bs4 import BeautifulSoup
from PIL import Image

# Typing imports
from typing import List, Dict

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'
PURPLE = '\033[95m'

#BlueSky API: https://docs.bsky.app/blog/create-post
def post_to_bluesky(link):
    print(f"{BLUE}Posting to BlueSky...{RESET}")

    BLUESKY_HANDLE = "mattsayar.com"
    BLUESKY_APP_PASSWORD = open('bsky.txt').read().strip()

    #create session
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
    )
    resp.raise_for_status()
    session = resp.json()

    post_text = input(f"{YELLOW}Enter the text for your post: {RESET}") + "\n\n" + link

    # Fetch the current time
    # Using a trailing "Z" is preferred over the "+00:00" format
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Required fields that each post must include
    post = {
        "$type": "app.bsky.feed.post",
        "createdAt": now,
    }

    # Need to make the link clickable. Parse the URL then make it a facet
    def parse_urls(text: str) -> List[Dict]:
        spans = []
        # partial/naive URL regex based on: https://stackoverflow.com/a/3809435
        # tweaked to disallow some training punctuation
        url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
        text_bytes = text.encode("UTF-8")
        for m in re.finditer(url_regex, text_bytes):
            spans.append({
                "start": m.start(1),
                "end": m.end(1),
                "url": m.group(1).decode("UTF-8"),
            })
        return spans

    # Parse facets from text
    def parse_facets(text: str) -> List[Dict]:
        facets = []
        for u in parse_urls(text):
            facets.append({
                "index": {
                    "byteStart": u["start"],
                    "byteEnd": u["end"],
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        # NOTE: URI ("I") not URL ("L")
                        "uri": u["url"],
                    }
                ],
            })
        return facets
    
    def fetch_embed_url_card(access_token: str, url: str) -> Dict:
        # the required fields for every embed card
        card = {
            "uri": url,
            "title": "",
            "description": "",
        }

        # fetch the HTML
        resp = requests.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # parse out the "og:title" and "og:description" HTML meta tags
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            card["title"] = title_tag["content"]
        description_tag = soup.find("meta", property="og:description")
        if description_tag:
            card["description"] = description_tag["content"]

        # if there is an "og:image" HTML meta tag, fetch and upload that image
        image_tag = soup.find("meta", property="og:image")
        if image_tag:
            img_url = image_tag["content"]
            # naively turn a "relative" URL (just a path) into a full URL, if needed
            if "://" not in img_url:
                img_url = url + img_url
            resp = requests.get(img_url)
            resp.raise_for_status()

            # Determine the MIME type based on the image URL (case-insensitive)
            img_url_lower = img_url.lower()
            if img_url_lower.endswith(".png"):
                image_mimetype = "image/png"
            elif img_url_lower.endswith(".jpg") or img_url_lower.endswith(".jpeg"):
                image_mimetype = "image/jpeg"
            elif img_url_lower.endswith(".gif"):
                image_mimetype = "image/gif"
            elif img_url_lower.endswith(".webp"):
                image_mimetype = "image/webp"
            elif img_url_lower.endswith(".svg"):
                image_mimetype = "image/svg+xml"
            else:
                # Default to JPEG if we can't determine the type
                image_mimetype = "image/jpeg"

            # Resize the image if it's too large for BlueSky
            if len(resp.content) > 1000000:
                image = Image.open(BytesIO(resp.content))
                image.thumbnail((1024, 1024))  # Resize to fit within 1024x1024
                buffer = BytesIO()
                image.save(buffer, format=image.format)
                image_content = buffer.getvalue()
            else:
                image_content = resp.content

            blob_resp = requests.post(
                "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
                headers={
                    "Content-Type": image_mimetype,
                    "Authorization": "Bearer " + access_token,
                },
                data=image_content,
            )
            blob_resp.raise_for_status()
            card["thumb"] = blob_resp.json()["blob"]

        return {
            "$type": "app.bsky.embed.external",
            "external": card,
        }

    post["text"] = post_text
    post["facets"] = parse_facets(post["text"])
    post["embed"] = fetch_embed_url_card(session["accessJwt"], link)

    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": "Bearer " + session["accessJwt"]},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": post,
        },
    )
    resp.raise_for_status()

    print(f"{GREEN}BlueSky post confirmed.{RESET}")

def post_to_hackernews(link):
    print(f"{BLUE}Opening Hacker News submit page...{RESET}")
    webbrowser.open("https://news.ycombinator.com/submit")
    input(f"{YELLOW}Press Enter to confirm you posted...{RESET}")
    print(f"{GREEN}Hacker News post 'confirmed'.{RESET}")

# free Zapier automation: 
# https://zapier.com/shared/6d07ead8e8fec1d6edb64448d953572b46c006f0
def post_to_linkedin(link):
    print(f"{BLUE}Opening LinkedIn feed...{RESET}")
    webbrowser.open(f"https://www.linkedin.com/feed/")
    input(f"{YELLOW}Press Enter to confirm you posted...{RESET}")
    print(f"{GREEN}LinkedIn post 'confirmed'.{RESET}")


def post_to_reddit(link):
    print(f"{BLUE}Opening Reddit submit page...{RESET}")
    webbrowser.open("https://www.reddit.com/submit")
    input(f"{YELLOW}Press Enter to confirm you posted...{RESET}")
    print(f"{GREEN}Reddit post 'confirmed'.{RESET}")


def post_to_tildes(link):
    print(f"{BLUE}Opening Tildes...{RESET}")
    webbrowser.open("https://tildes.net/")
    input(f"{YELLOW}Press Enter to confirm you posted...{RESET}")
    print(f"{GREEN}Tildes post 'confirmed'.{RESET}")

# for "enter to continue or space to skip" prompt
def get_key_press():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

# for "enter to continue or space to skip" prompt
def prompt_user(prompt):
    print(prompt, end='', flush=True)
    key = get_key_press()
    print()  # for newline after key press
    return key

def main():
    os.system('cls' if os.name == 'nt' else 'clear')  # Clear the screen for better UX
    print(f"{YELLOW}=== Social Media Poster Checklist ==={RESET}\n")

    if len(sys.argv) < 2:
        print(f"{RED}Error: No link provided!{RESET}")
        print(f"{YELLOW}Please run the script with a link as a command line argument, like this:{RESET}")
        print(f"{YELLOW}  python3 social_poster.py \"https://www.example.com/your-link\"{RESET}")
        print(f"{YELLOW}Remember to put the link in quotes if it has special characters.{RESET}")
        sys.exit(1)  # Exit with a non-zero status code

    link = sys.argv[1]

    if prompt_user(f"{PURPLE}Do you want to post to Bluesky? Press Enter to continue or space to skip") in ["\r", "\n"]:
        post_to_bluesky(link)
    if prompt_user(f"{PURPLE}Do you want to post to Hackernews? Press Enter to continue or space to skip") in ["\r", "\n"]:
        post_to_hackernews(link)
    if prompt_user(f"{PURPLE}Do you want to post to LinkedIn? Not recommended if Zapier is set up! Press Enter to continue or space to skip") in ["\r", "\n"]:
        post_to_linkedin(link)
    if prompt_user(f"{PURPLE}Do you want to post to Reddit? Press Enter to continue or space to skip") in ["\r", "\n"]:
        post_to_reddit(link)
    if prompt_user(f"{PURPLE}Do you want to post to Tildes? Press Enter to continue or space to skip") in ["\r", "\n"]:
        post_to_tildes(link)
    
    print(f"\n{GREEN}All done! May the reacts be ever in your favor.{RESET}")

if __name__ == "__main__":
    main()