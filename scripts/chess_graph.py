#!/usr/bin/env python3
"""Render a GitHub contribution calendar as a chessboard with a knight that hops across it.

Usage: chess_graph.py OUTPUT.svg
Env:   GH_USER, GH_TOKEN  (live data). Without a token, a sample board is drawn.
"""
import json
import os
import sys
import urllib.request

CELL, GAP, PAD_X, PAD_TOP, PAD_BOTTOM = 14, 3, 24, 58, 30
STEP = CELL + GAP
GOLD = ["#4a3f1f", "#8a7230", "#D6B25E", "#f3dc9b"]
DARK_SQ, LIGHT_SQ = "#15140f", "#1d1b14"
QUERY = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount weekday}}}}}}"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": user}}).encode(),
        headers={"Authorization": "bearer " + token, "User-Agent": "chess-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[0] * 7 for _ in cal["weeks"]]
    for i, w in enumerate(cal["weeks"]):
        for d in w["contributionDays"]:
            weeks[i][d["weekday"]] = d["contributionCount"]
    return weeks, cal["totalContributions"]


def sample():
    seed, weeks = 7, []
    for _ in range(53):
        col = []
        for _ in range(7):
            seed = (seed * 9301 + 49297) % 233280
            col.append(int(seed / 233280 * 9) if seed % 5 else 0)
        weeks.append(col)
    return weeks, sum(map(sum, weeks))


def level(n, top):
    if n <= 0:
        return -1
    q = n / max(top, 1)
    return 0 if q <= .25 else 1 if q <= .5 else 2 if q <= .75 else 3


def knight_path(weeks):
    """Walk the board with legal knight moves, preferring squares that have contributions."""
    cols, rows = len(weeks), 7
    moves = [(2, 1), (2, -1), (1, 2), (1, -2), (3, 0)][:4]
    c, r, path = 0, 3, [(0, 3)]
    seen = {(0, 3)}
    while c < cols - 2:
        options = []
        for dc, dr in moves:
            nc, nr = c + dc, r + dr
            if 0 <= nr < rows and nc < cols:
                score = (weeks[nc][nr] > 0) * 2 + ((nc, nr) not in seen)
                options.append((score, -abs(nr - 3), nc, nr))
        if not options:
            break
        options.sort(reverse=True)
        _, _, c, r = options[0]
        seen.add((c, r))
        path.append((c, r))
    return path


def render(weeks, total, user):
    cols = len(weeks)
    top = max(max(w) for w in weeks)
    width = PAD_X * 2 + cols * STEP
    height = PAD_TOP + 7 * STEP + PAD_BOTTOM
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
        f'aria-label="{total} contributions in the last year, drawn as a chessboard">',
        f'<rect width="{width}" height="{height}" rx="14" fill="#0C0C0F"/>',
        f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="14" fill="none" stroke="#D6B25E" stroke-opacity=".4"/>',
        f'<text x="{PAD_X}" y="30" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="12" letter-spacing="3" fill="#D6B25E">'
        f'THE BOARD  ·  {total} MOVES IN THE LAST YEAR</text>',
        f'<text x="{width-PAD_X}" y="30" text-anchor="end" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11" fill="#8b8576">@{user}</text>',
    ]
    for c, week in enumerate(weeks):
        for r, n in enumerate(week):
            lv = level(n, top)
            fill = GOLD[lv] if lv >= 0 else (DARK_SQ if (c + r) % 2 == 0 else LIGHT_SQ)
            out.append(f'<rect x="{PAD_X + c*STEP}" y="{PAD_TOP + r*STEP}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}"/>')
    pts = knight_path(weeks)
    cx = lambda c: PAD_X + c * STEP + CELL / 2
    cy = lambda r: PAD_TOP + r * STEP + CELL / 2
    d = "M" + " L".join(f"{cx(c):.1f} {cy(r):.1f}" for c, r in pts)
    out.append(f'<path d="{d}" fill="none" stroke="#D6B25E" stroke-opacity=".35" stroke-dasharray="3 4"/>')
    dur = max(len(pts) * 0.9, 10)
    out.append(
        '<g><circle r="11" fill="#D6B25E" fill-opacity=".18"/>'
        '<text y="8" text-anchor="middle" font-size="22" fill="#f3dc9b" '
        'font-family="\'Segoe UI Symbol\',\'Apple Symbols\',\'DejaVu Sans\',\'Noto Sans Symbols2\',serif">♞</text>'
        f'<animateMotion dur="{dur:.0f}s" repeatCount="indefinite" path="{d}"/></g>'
    )
    legend_x = width - PAD_X - 4 * 18 - 70
    ly = height - 14
    out.append(f'<text x="{legend_x}" y="{ly}" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" fill="#8b8576">fewer</text>')
    for i, col in enumerate(GOLD):
        out.append(f'<rect x="{legend_x + 34 + i*16}" y="{ly-9}" width="11" height="11" rx="2" fill="{col}"/>')
    out.append(f'<text x="{legend_x + 34 + 4*16 + 4}" y="{ly}" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10" fill="#8b8576">more</text>')
    out.append(f'<text x="{PAD_X}" y="{ly}" font-family="Georgia,serif" font-style="italic" font-size="12" fill="#8b8576">Every square is a day. Every gold one is a move played.</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "chess.svg"
    user, token = os.environ.get("GH_USER", "CheckMate-Intelik"), os.environ.get("GH_TOKEN")
    weeks, total = fetch(user, token) if token else sample()
    with open(target, "w", encoding="utf-8") as f:
        f.write(render(weeks, total, user))


if __name__ == "__main__":
    main()
