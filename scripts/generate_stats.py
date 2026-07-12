from __future__ import annotations

import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from collections import Counter
from pathlib import Path
from typing import Any


API_ROOT = "https://api.github.com"
OUTPUT_PATH = Path("assets/stats.svg")


def request_json(path: str, token: str) -> Any:
    """
    GitHub REST API üzerinden JSON veri alır.

    Ağ, kimlik doğrulama veya API hatalarında açıklayıcı
    bir RuntimeError oluşturur.
    """

    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "profile-readme-stat-generator",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            return json.load(response)

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"GitHub API request failed with HTTP "
            f"{exc.code}: {body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"GitHub API request failed: {exc.reason}"
        ) from exc


def fetch_all_repositories(
    username: str,
    token: str,
) -> list[dict[str, Any]]:
    """
    Kullanıcıya ait herkese açık repository kayıtlarının
    tamamını sayfalı biçimde getirir.
    """

    repositories: list[dict[str, Any]] = []
    page = 1

    while True:
        encoded_username = urllib.parse.quote(username)

        path = (
            f"/users/{encoded_username}/repos"
            f"?type=owner"
            f"&sort=updated"
            f"&per_page=100"
            f"&page={page}"
        )

        batch = request_json(path, token)

        if not isinstance(batch, list):
            raise RuntimeError(
                "Unexpected repositories response "
                "from GitHub API."
            )

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    return repositories


def compact_number(value: int) -> str:
    """
    Büyük sayıları 1.2K veya 2.4M biçiminde gösterir.
    """

    if value < 1_000:
        return str(value)

    if value < 1_000_000:
        result = f"{value / 1_000:.1f}K"
        return result.replace(".0K", "K")

    result = f"{value / 1_000_000:.1f}M"
    return result.replace(".0M", "M")


def generate_svg(
    *,
    username: str,
    public_repos: int,
    total_stars: int,
    followers: int,
    top_language: str,
) -> str:
    """
    GitHub profilinde gösterilecek yerel SVG kartını üretir.
    """

    safe_username = html.escape(username)
    safe_top_language = html.escape(top_language)

    return f"""<svg
  xmlns="http://www.w3.org/2000/svg"
  width="1200"
  height="245"
  viewBox="0 0 1200 245"
  role="img"
  aria-labelledby="title desc"
>
  <title id="title">
    {safe_username} GitHub profile summary
  </title>

  <desc id="desc">
    GitHub API kullanılarak otomatik güncellenen profil özet kartları.
  </desc>

  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#080c14"/>
      <stop offset="1" stop-color="#0d1725"/>
    </linearGradient>

    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#24d3ee"/>
      <stop offset=".5" stop-color="#7c5cff"/>
      <stop offset="1" stop-color="#ff4f9a"/>
    </linearGradient>

    <style>
      text {{
        font-family: Inter, "Segoe UI", Arial, sans-serif;
      }}

      .label {{
        fill: #7f93ae;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1.2px;
      }}

      .value {{
        fill: #f7fbff;
        font-size: 32px;
        font-weight: 800;
      }}

      .note {{
        fill: #71849d;
        font-size: 13px;
      }}
    </style>
  </defs>

  <rect
    width="1200"
    height="245"
    rx="24"
    fill="url(#bg)"
  />

  <rect
    x="1"
    y="1"
    width="1198"
    height="243"
    rx="23"
    fill="none"
    stroke="#293950"
  />

  <text
    x="42"
    y="44"
    fill="#f5f8ff"
    font-size="20"
    font-weight="800"
  >
    GitHub Activity Snapshot
  </text>

  <text
    x="1158"
    y="44"
    text-anchor="end"
    class="note"
  >
    @{safe_username} · automatically updated
  </text>

  <rect
    x="42"
    y="68"
    width="258"
    height="118"
    rx="18"
    fill="#0d1827"
    stroke="#263a52"
  />

  <rect
    x="318"
    y="68"
    width="258"
    height="118"
    rx="18"
    fill="#0d1827"
    stroke="#263a52"
  />

  <rect
    x="594"
    y="68"
    width="258"
    height="118"
    rx="18"
    fill="#0d1827"
    stroke="#263a52"
  />

  <rect
    x="870"
    y="68"
    width="288"
    height="118"
    rx="18"
    fill="#0d1827"
    stroke="#263a52"
  />

  <text x="66" y="101" class="label">
    PUBLIC REPOSITORIES
  </text>

  <text x="66" y="146" class="value">
    {compact_number(public_repos)}
  </text>

  <text x="342" y="101" class="label">
    TOTAL STARS
  </text>

  <text x="342" y="146" class="value">
    {compact_number(total_stars)}
  </text>

  <text x="618" y="101" class="label">
    FOLLOWERS
  </text>

  <text x="618" y="146" class="value">
    {compact_number(followers)}
  </text>

  <text x="894" y="101" class="label">
    TOP LANGUAGE
  </text>

  <text x="894" y="146" class="value">
    {safe_top_language}
  </text>

  <rect
    x="42"
    y="211"
    width="1116"
    height="3"
    rx="1.5"
    fill="url(#accent)"
    opacity=".78"
  />
</svg>
"""


def main() -> int:
    """
    GitHub API verilerini alır ve stats.svg dosyasını günceller.
    """

    token = os.environ.get(
        "GITHUB_TOKEN",
        "",
    ).strip()

    username = os.environ.get(
        "GITHUB_USERNAME",
        "",
    ).strip()

    if not token:
        print(
            "GITHUB_TOKEN is missing.",
            file=sys.stderr,
        )
        return 1

    if not username:
        print(
            "GITHUB_USERNAME is missing.",
            file=sys.stderr,
        )
        return 1

    encoded_username = urllib.parse.quote(username)

    user = request_json(
        f"/users/{encoded_username}",
        token,
    )

    repositories = fetch_all_repositories(
        username,
        token,
    )

    visible_repositories = [
        repository
        for repository in repositories
        if not repository.get("fork", False)
        and not repository.get("archived", False)
    ]

    total_stars = sum(
        int(repository.get("stargazers_count", 0))
        for repository in visible_repositories
    )

    languages = Counter(
        str(repository["language"])
        for repository in visible_repositories
        if repository.get("language")
    )

    if languages:
        top_language = languages.most_common(1)[0][0]
    else:
        top_language = "Not set"

    svg = generate_svg(
        username=username,
        public_repos=int(
            user.get(
                "public_repos",
                len(repositories),
            )
        ),
        total_stars=total_stars,
        followers=int(
            user.get(
                "followers",
                0,
            )
        ),
        top_language=top_language,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        svg,
        encoding="utf-8",
    )

    print(f"Updated {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
