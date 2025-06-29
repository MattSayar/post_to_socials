# Post to Socials

This hot new script will literally save minutes of your life! It's just a simple way to help post new links to various sites. BlueSky is the only one that's fully automated, then it opens new tabs to each site's "submit a post" screen:
* Hacker News
* LinkedIn
* Reddit
* Tildes

# Usage
Store a BlueSky [App Password](https://bsky.app/settings/app-passwords) in a file in the same directory called `bsky.txt`.

## Running with uv (recommended)
```bash
uv run post_to_socials.py https://example.com
```

## Running with Python
Install dependencies first:
```bash
pip install requests beautifulsoup4 pillow
```

Then run:
```bash
python3 post_to_socials.py https://example.com
# or
./post_to_socials.py https://example.com
```