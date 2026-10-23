#!/usr/bin/env python3
"""digitspan-lp の共通部分（head の alternate・言語切替・フッター・更新日）を
全言語ぶん書き戻す。sumflash-lp の tools/i18n.py をもとに、ページをディレクトリ型
（`privacy/index.html` → URL は `/privacy/`）にしたもの。

各 HTML は次の3つの目印を持つ。目印のあいだはこのスクリプトが上書きするので、
手で書かない。目印の外（title / description / og / 本文）だけを手で書く。

    <!--chrome:alt-->  ... <!--/chrome:alt-->    canonical / hreflang / css / アイコン
    <!--chrome:nav-->  ... <!--/chrome:nav-->    上のバー（ページ・言語へのリンクと、JS を使わないテーマ切替）
    <!--chrome:foot--> ... <!--/chrome:foot-->   フッター

法務ページの更新日は `<p class="updated" data-updated="YYYY-MM-DD">` の日付から
言語ごとの書き方で埋める。**日付を直すのは1か所だけ**でよい。

使い方: python3 tools/i18n.py        （全ファイルを書き戻す）
        python3 tools/i18n.py --check（差分が出るなら異常終了）
"""
from __future__ import annotations

import hashlib
import pathlib
import posixpath
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://fukuidinotech.github.io/digitspan-lp/"

# ページの鍵 → 言語ディレクトリからの置き場（空 = 言語の直下）。
# **privacy の URL は `/privacy/` で固定。** AdMob の EU 同意メッセージがこの URL を指している（2026-10-22 登録）
PAGES = {"index": "", "guide": "guide", "privacy": "privacy", "terms": "terms"}
NAV = ["guide", "privacy", "terms"]
CONTACT = "fukuidinotech@gmail.com"

# ja は repo 直下。ほかの言語は同名のサブディレクトリ
LANGS = {
    "ja": {
        "dir": "", "native": "日本語", "pick": "言語を選ぶ",
        "app": "数字記憶テスト", "tagline": "何桁まで覚えられるかを測る短期記憶テスト（iOS）",
        "guide": "使い方", "privacy": "プライバシーポリシー", "terms": "利用規約",
        "contact": "お問い合わせ",
        "theme": "表示の色", "theme_auto": "自動", "theme_light": "ライト", "theme_dark": "ダーク",
        "updated": "最終更新日", "date": "{y}年{m}月{d}日",
    },
    "en": {
        "dir": "en", "native": "English", "pick": "Choose a language",
        "app": "Digit Span", "tagline": "number memory test for iOS",
        "guide": "How to Use", "privacy": "Privacy Policy", "terms": "Terms of Use",
        "contact": "Contact",
        "theme": "Color theme", "theme_auto": "Auto", "theme_light": "Light", "theme_dark": "Dark",
        "updated": "Last updated", "date": "{month} {d}, {y}",
    },
}

# 月の名前が要る言語だけ持つ（ja は数字で書く）
MONTHS = {
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}


def page_dir(lang: str, page: str) -> str:
    """repo 直下からのディレクトリ（'' / 'privacy' / 'en' / 'en/privacy'）"""
    return "/".join(p for p in (LANGS[lang]["dir"], PAGES[page]) if p)


def url_for(lang: str, page: str) -> str:
    d = page_dir(lang, page)
    return BASE + (f"{d}/" if d else "")


def rel(from_lang: str, from_page: str, to_lang: str, to_page: str) -> str:
    """ページ間のリンク。手元で開いても辿れるよう index.html まで書く"""
    src = page_dir(from_lang, from_page) or "."
    dst = page_dir(to_lang, to_page) or "."
    return posixpath.normpath(posixpath.join(posixpath.relpath(dst, src), "index.html"))


def asset(lang: str, page: str, name: str) -> str:
    """css と画像は repo 直下に1つだけ置く"""
    src = page_dir(lang, page) or "."
    return posixpath.normpath(posixpath.join(posixpath.relpath(".", src), name))


_versions: dict[str, str] = {}


def css_version(name: str) -> str:
    """css の中身から作る短い印。**手で上げない。**

    GitHub Pages は HTML と CSS の両方に `max-age=600` を付けるので、CSS を変えた直後は
    「新しい HTML ＋ 古い CSS」で見る人が出る。URL に中身の印を入れて取り直させる。
    """
    if name not in _versions:
        _versions[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()[:8]
    return _versions[name]


def date_text(lang: str, iso: str) -> str:
    y, m, d = (int(v) for v in iso.split("-"))
    cfg = LANGS[lang]
    month = MONTHS[lang][m] if "{month}" in cfg["date"] else ""
    return f'{cfg["updated"]}: ' + cfg["date"].format(y=y, m=m, d=d, month=month)


def block_alt(lang: str, page: str) -> str:
    lines = [f'<link rel="canonical" href="{url_for(lang, page)}">']
    for other in LANGS:
        lines.append(f'<link rel="alternate" hreflang="{other}" href="{url_for(other, page)}">')
    # 一致する言語が無い人には英語を出す
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url_for("en", page)}">')
    css = "site.css" if page == "index" else "legal.css"
    lines.append(f'<link rel="stylesheet" href="{asset(lang, page, css)}?v={css_version(css)}">')
    lines.append(f'<link rel="icon" href="{asset(lang, page, "favicon.ico")}" sizes="16x16 32x32 48x48">')
    lines.append(f'<link rel="icon" type="image/png" href="{asset(lang, page, "favicon.png")}" sizes="192x192">')
    lines.append(f'<link rel="apple-touch-icon" href="{asset(lang, page, "apple-touch-icon.png")}">')
    return "\n".join(lines)


# **言語の自動振り分け（JS）は入れない。** 入口の振り分けは hreflang と言語切替に任せる
# （kakesu-lp で JS の振り分けを入れて外した経緯。外から書ける値を遷移先に使うと穴になる）


def block_nav(lang: str, page: str) -> str:
    cfg = LANGS[lang]
    out = ['<header class="topbar">',
           f'  <a class="brand" href="{rel(lang, page, lang, "index")}">'
           f'<img src="{asset(lang, page, "favicon.png")}" alt="" width="28" height="28">{cfg["app"]}</a>',
           '  <div class="display-controls">',
           f'    <nav class="langs" aria-label="{cfg["pick"]}">']
    for other, ocfg in LANGS.items():
        cur = ' aria-current="true"' if other == lang else ""
        out.append(f'      <a lang="{other}" hreflang="{other}" '
                   f'href="{rel(lang, page, other, page)}"{cur}>{ocfg["native"]}</a>')
    out.append('    </nav>')
    out.append('    <fieldset class="themes">')
    out.append(f'      <legend class="visually-hidden">{cfg["theme"]}</legend>')
    for theme in ("auto", "light", "dark"):
        checked = " checked" if theme == "auto" else ""
        out.append(f'      <input class="visually-hidden" type="radio" name="theme" '
                   f'id="theme-{theme}" value="{theme}"{checked}>')
        out.append(f'      <label for="theme-{theme}">{cfg[f"theme_{theme}"]}</label>')
    out.append('    </fieldset>')
    out.append('  </div>')
    out.append('  <nav class="pages">')
    for p in NAV:
        cur = ' aria-current="page"' if p == page else ""
        out.append(f'    <a href="{rel(lang, page, lang, p)}"{cur}>{cfg[p]}</a>')
    out.append('  </nav>')
    out.append('</header>')
    return "\n".join(out)


def block_foot(lang: str, page: str) -> str:
    cfg = LANGS[lang]
    out = ['<footer>']
    if page == "index":
        links = [f'<a href="{rel(lang, page, lang, p)}">{cfg[p]}</a>' for p in NAV]
        links.append(f'<a href="mailto:{CONTACT}">{cfg["contact"]}</a>')
        out.append('  <p>')
        out += [f'    {a}' for a in links]
        out.append('  </p>')
        out.append(f'  <p>{cfg["app"]} — {cfg["tagline"]}</p>')
    else:
        out.append(f'  <p><a href="{rel(lang, page, lang, "index")}">{cfg["app"]}</a> — {cfg["tagline"]}</p>')
        others = " / ".join(f'<a href="{rel(lang, page, lang, p)}">{cfg[p]}</a>' for p in NAV if p != page)
        out.append(f'  <p>{others}</p>')
    out.append('  <p>&copy; 2026 Toru Fukui</p>')
    out.append('</footer>')
    return "\n".join(out)


BLOCKS = {"alt": block_alt, "nav": block_nav, "foot": block_foot}


def apply(text: str, lang: str, page: str) -> str:
    for key, fn in BLOCKS.items():
        pattern = re.compile(f"(<!--chrome:{key}-->).*?(<!--/chrome:{key}-->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"目印 chrome:{key} が無い: {lang}/{page}")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{fn(lang, page)}\n{m.group(2)}", text)
    text = re.sub(r'(<p class="updated" data-updated="(\d{4}-\d{2}-\d{2})">).*?(</p>)',
                  lambda m: f"{m.group(1)}{date_text(lang, m.group(2))}{m.group(3)}", text, flags=re.S)
    text = re.sub(r'<html lang="[^"]*">', f'<html lang="{lang}">', text, count=1)
    return text


def main() -> int:
    check = "--check" in sys.argv
    stale, missing = [], []
    for lang in LANGS:
        for page in PAGES:
            d = page_dir(lang, page)
            path = ROOT / d / "index.html" if d else ROOT / "index.html"
            if not path.exists():
                missing.append(str(path.relative_to(ROOT)))
                continue
            before = path.read_text(encoding="utf-8")
            after = apply(before, lang, page)
            if before != after:
                stale.append(str(path.relative_to(ROOT)))
                if not check:
                    path.write_text(after, encoding="utf-8")

    for name in missing:
        print(f"無い: {name}")
    for name in stale:
        print(("ずれ: " if check else "直した: ") + name)
    if check and (stale or missing):
        return 1
    if missing:
        return 1
    if not stale:
        print("共通部分は全ページ一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
