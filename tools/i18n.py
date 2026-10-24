#!/usr/bin/env python3
"""digitspan-lp の共通部分（head の alternate・言語切替・フッター・更新日）を
全言語ぶん書き戻す。旧 `en/` の URL の受け皿（直下の英語ページへ飛ばす）もここで書く。sumflash-lp の tools/i18n.py をもとに、ページをディレクトリ型
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
# **privacy の URL は `/privacy/` で固定。** AdMob の EU 同意メッセージがこの URL を指している（2026-10-22 登録。
# 2026-10-23 に en を直下へ移してからは英語版）
PAGES = {"index": "", "guide": "guide", "privacy": "privacy", "terms": "terms"}
NAV = ["guide", "privacy", "terms"]
CONTACT = "fukuidinotech@gmail.com"

# **en は repo 直下（既定の言語）。ほかの言語は同名のサブディレクトリ**（2026-10-23〜。それまでは ja が直下で en は `en/`）。
# 言語切替もこの順に並ぶ
LANGS = {
    "en": {
        "dir": "", "locale": "en_US", "native": "English", "pick": "Choose a language",
        "app": "Digit Span", "tagline": "number memory test for iOS",
        "home": "Home", "guide": "How to Use", "privacy": "Privacy Policy", "terms": "Terms of Use",
        "contact": "Contact",
        "theme": "Color theme", "theme_auto": "Auto", "theme_light": "Light", "theme_dark": "Dark",
        "updated": "Last updated", "date": "{month} {d}, {y}",
    },
    "ja": {
        "dir": "ja", "locale": "ja_JP", "native": "日本語", "pick": "言語を選ぶ",
        "app": "数字記憶テスト", "tagline": "何桁まで覚えられるかを測る短期記憶テスト（iOS）",
        "home": "トップ", "guide": "使い方", "privacy": "プライバシーポリシー", "terms": "利用規約",
        "contact": "お問い合わせ",
        "theme": "表示の色", "theme_auto": "自動", "theme_light": "ライト", "theme_dark": "ダーク",
        "updated": "最終更新日", "date": "{y}年{m}月{d}日",
    },
    "de": {
        "dir": "de", "locale": "de_DE",
        "native": "Deutsch", "pick": "Sprache wählen", "app": "Digit Span", "tagline": "Zahlengedächtnistest für iOS", "home": "Startseite", "guide": "Anleitung", "privacy": "Datenschutzerklärung", "terms": "Nutzungsbedingungen", "contact": "Kontakt", "theme": "Farbschema", "theme_auto": "Automatisch", "theme_light": "Hell", "theme_dark": "Dunkel", "updated": "Zuletzt aktualisiert", "date": "{d}. {month} {y}",
    },
    "fr": {
        "dir": "fr", "locale": "fr_FR", "sep": "\u202f: ",
        "native": "Français", "pick": "Choisir la langue", "app": "Digit Span", "tagline": "test de mémoire des chiffres pour iOS", "home": "Accueil", "guide": "Mode d’emploi", "privacy": "Politique de confidentialité", "terms": "Conditions d’utilisation", "contact": "Nous contacter", "theme": "Thème d’affichage", "theme_auto": "Auto", "theme_light": "Clair", "theme_dark": "Sombre", "updated": "Dernière mise à jour", "date": "{d} {month} {y}",
    },
    "es": {
        "dir": "es", "locale": "es_ES",
        "native": "Español", "pick": "Elegir idioma", "app": "Digit Span", "tagline": "prueba de memoria de números para iOS", "home": "Inicio", "guide": "Cómo se usa", "privacy": "Política de privacidad", "terms": "Términos de uso", "contact": "Contacto", "theme": "Tema", "theme_auto": "Automático", "theme_light": "Claro", "theme_dark": "Oscuro", "updated": "Última actualización", "date": "{d} de {month} de {y}",
    },
    "it": {
        "dir": "it", "locale": "it_IT",
        "native": "Italiano", "pick": "Scegli la lingua", "app": "Digit Span", "tagline": "test di memoria numerica per iOS", "home": "Home", "guide": "Come si usa", "privacy": "Informativa sulla privacy", "terms": "Termini di utilizzo", "contact": "Contattaci", "theme": "Tema dei colori", "theme_auto": "Automatico", "theme_light": "Chiaro", "theme_dark": "Scuro", "updated": "Ultimo aggiornamento", "date": "{d} {month} {y}",
    },
    "pt-BR": {
        "dir": "pt-BR", "locale": "pt_BR",
        "native": "Português (Brasil)", "pick": "Escolha o idioma", "app": "Digit Span", "tagline": "teste de memória numérica para iOS", "home": "Início", "guide": "Como usar", "privacy": "Política de Privacidade", "terms": "Termos de Uso", "contact": "Contato", "theme": "Tema de cores", "theme_auto": "Automático", "theme_light": "Claro", "theme_dark": "Escuro", "updated": "Última atualização", "date": "{d} de {month} de {y}",
    },
    "nl": {
        "dir": "nl", "locale": "nl_NL",
        "native": "Nederlands", "pick": "Kies een taal", "app": "Digit Span", "tagline": "cijfergeheugentest voor iOS", "home": "Home", "guide": "Uitleg", "privacy": "Privacybeleid", "terms": "Gebruiksvoorwaarden", "contact": "Contact", "theme": "Kleurenschema", "theme_auto": "Automatisch", "theme_light": "Licht", "theme_dark": "Donker", "updated": "Laatst bijgewerkt", "date": "{d} {month} {y}",
    },
    "pl": {
        "dir": "pl", "locale": "pl_PL",
        "native": "Polski", "pick": "Wybierz język", "app": "Digit Span", "tagline": "test pamięci cyfr na iOS", "home": "Strona główna", "guide": "Jak korzystać", "privacy": "Polityka prywatności", "terms": "Regulamin", "contact": "Kontakt", "theme": "Motyw kolorystyczny", "theme_auto": "Auto", "theme_light": "Jasny", "theme_dark": "Ciemny", "updated": "Ostatnia aktualizacja", "date": "{d} {month} {y}",
    },
    "ru": {
        "dir": "ru", "locale": "ru_RU",
        "native": "Русский", "pick": "Выберите язык", "app": "Digit Span", "tagline": "тест памяти на цифры для iOS", "home": "Главная", "guide": "Как пользоваться", "privacy": "Политика конфиденциальности", "terms": "Условия использования", "contact": "Связаться с нами", "theme": "Цветовая тема", "theme_auto": "Авто", "theme_light": "Светлая", "theme_dark": "Тёмная", "updated": "Последнее обновление", "date": "{d} {month} {y} г.",
    },
    "ar": {
        "dir": "ar", "locale": "ar_AR", "rtl": True,
        "native": "العربية", "pick": "اختيار اللغة", "app": "Digit Span", "tagline": "اختبار ذاكرة الأرقام لنظام iOS", "home": "الرئيسية", "guide": "طريقة الاستخدام", "privacy": "سياسة الخصوصية", "terms": "شروط الخدمة", "contact": "التواصل معنا", "theme": "سمة العرض", "theme_auto": "تلقائي", "theme_light": "فاتح", "theme_dark": "داكن", "updated": "آخر تحديث", "date": "{d} {month} {y}",
    },
    "he": {
        "dir": "he", "locale": "he_IL", "rtl": True,
        "native": "עברית", "pick": "בחירת שפה", "app": "Digit Span", "tagline": "מבחן זיכרון מספרים ל-iOS", "home": "דף הבית", "guide": "איך משתמשים", "privacy": "מדיניות פרטיות", "terms": "תנאי שימוש", "contact": "יצירת קשר", "theme": "ערכת נושא", "theme_auto": "אוטומטי", "theme_light": "בהיר", "theme_dark": "כהה", "updated": "עודכן לאחרונה", "date": "{d} ב{month} {y}",
    },
    "ko": {
        "dir": "ko", "locale": "ko_KR",
        "native": "한국어", "pick": "언어 선택", "app": "Digit Span", "tagline": "iOS용 숫자 기억 테스트", "home": "홈", "guide": "사용 방법", "privacy": "개인정보 처리방침", "terms": "이용약관", "contact": "문의하기", "theme": "화면 색상", "theme_auto": "자동", "theme_light": "라이트", "theme_dark": "다크", "updated": "최종 업데이트", "date": "{y}년 {m}월 {d}일",
    },
    "vi": {
        "dir": "vi", "locale": "vi_VN",
        "native": "Tiếng Việt", "pick": "Chọn ngôn ngữ", "app": "Digit Span", "tagline": "bài kiểm tra trí nhớ số cho iOS", "home": "Trang chủ", "guide": "Cách sử dụng", "privacy": "Chính sách quyền riêng tư", "terms": "Điều khoản sử dụng", "contact": "Liên hệ", "theme": "Màu hiển thị", "theme_auto": "Tự động", "theme_light": "Sáng", "theme_dark": "Tối", "updated": "Cập nhật lần cuối", "date": "{d} tháng {m} năm {y}",
    },
    "zh-Hans": {
        "dir": "zh-Hans", "locale": "zh_CN",
        "native": "简体中文", "pick": "选择语言", "app": "Digit Span", "tagline": "iOS 数字记忆测试", "home": "首页", "guide": "使用说明", "privacy": "隐私政策", "terms": "使用条款", "contact": "联系我们", "theme": "配色", "theme_auto": "自动", "theme_light": "浅色", "theme_dark": "深色", "updated": "最后更新", "date": "{y}年{m}月{d}日",
    },
    "zh-Hant": {
        "dir": "zh-Hant", "locale": "zh_TW",
        "native": "繁體中文", "pick": "選擇語言", "app": "Digit Span", "tagline": "iOS 數字記憶測驗", "home": "首頁", "guide": "使用說明", "privacy": "隱私權政策", "terms": "使用條款", "contact": "聯絡我們", "theme": "顯示配色", "theme_auto": "自動", "theme_light": "淺色", "theme_dark": "深色", "updated": "最後更新日期", "date": "{y}年{m}月{d}日",
    },

}

# 月の名前が要る言語だけ持つ（ja は数字で書く）
MONTHS = {
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "de": ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "es": ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "it": ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "pt-BR": ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "nl": ["", "januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
    "pl": ["", "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"],
    "ru": ["", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    "ar": ["", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    "he": ["", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"],
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
    # 見出しと日付のあいだ。fr はコロンの前に U+202F（狭い空白）を置く
    # fr は1日だけ序数（1er octobre）
    day = "1er" if lang == "fr" and d == 1 else d
    return cfg["updated"] + cfg.get("sep", ": ") + cfg["date"].format(y=y, m=m, d=day, month=month)


# **この LP で置く JS はこれだけ**（2026-10-23 ユーザー判断で「ページに JS を置かない」の例外）。
# 上のバーの「自動 / ライト / ダーク」の選択を端末（localStorage）に覚え、ページを移っても・再読み込みしても保つ。
# 読むのは light / dark の2値だけで、ほかの値は捨てる。外へは何も送らない。JS が無くても切り替え自体は CSS だけで動く
THEME_SCRIPT = """<script>
(function () {
  var KEY = "digitspan-lp-theme", root = document.documentElement;
  function saved() {
    try { var v = localStorage.getItem(KEY); return v === "light" || v === "dark" ? v : "auto"; } catch (e) { return "auto"; }
  }
  function apply(v) {
    if (v === "auto") { root.removeAttribute("data-scheme"); } else { root.setAttribute("data-scheme", v); }
    var radio = document.getElementById("theme-" + v);
    if (radio) { radio.checked = true; }
  }
  apply(saved());
  document.addEventListener("DOMContentLoaded", function () {
    apply(saved());
    var radios = document.querySelectorAll('input[name="theme"]');
    for (var i = 0; i < radios.length; i++) {
      radios[i].addEventListener("change", function (event) {
        var v = event.target.value === "light" || event.target.value === "dark" ? event.target.value : "auto";
        apply(v);
        try { if (v === "auto") { localStorage.removeItem(KEY); } else { localStorage.setItem(KEY, v); } } catch (e) {}
      });
    }
  });
  // 「戻る」で前のページがそのまま出たとき（bfcache）も、いまの選択に合わせ直す
  window.addEventListener("pageshow", function () { apply(saved()); });
})();
</script>"""


def block_alt(lang: str, page: str) -> str:
    lines = [THEME_SCRIPT, f'<link rel="canonical" href="{url_for(lang, page)}">']
    for other in LANGS:
        lines.append(f'<link rel="alternate" hreflang="{other}" href="{url_for(other, page)}">')
    # 一致する言語が無い人には英語を出す
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url_for("en", page)}">')
    css = "site.css" if page == "index" else "legal.css"
    lines.append(f'<link rel="stylesheet" href="{asset(lang, page, css)}?v={css_version(css)}">')
    lines.append(f'<link rel="icon" href="{asset(lang, page, "favicon.ico")}" sizes="16x16 32x32 48x48">')
    lines.append(f'<link rel="icon" type="image/png" href="{asset(lang, page, "favicon.png")}" sizes="192x192">')
    lines.append(f'<link rel="apple-touch-icon" href="{asset(lang, page, "apple-touch-icon.png")}">')
    # SNS で共有されたときの情報。og:title / description / image は各ページで手書きする
    lines.append(f'<meta property="og:url" content="{url_for(lang, page)}">')
    lines.append(f'<meta property="og:site_name" content="{LANGS[lang]["app"]}">')
    lines.append(f'<meta property="og:locale" content="{LANGS[lang]["locale"]}">')
    for other in LANGS:
        if other != lang:
            lines.append(f'<meta property="og:locale:alternate" content="{LANGS[other]["locale"]}">')
    lines.append('<meta name="twitter:card" content="summary">')
    return "\n".join(lines)


# **言語の自動振り分け（JS）は入れない。** 入口の振り分けは hreflang と言語切替に任せる
# （JS はテーマの選択を覚える THEME_SCRIPT だけ）
# （kakesu-lp で JS の振り分けを入れて外した経緯。外から書ける値を遷移先に使うと穴になる）


def block_nav(lang: str, page: str) -> str:
    cfg = LANGS[lang]
    out = ['<header class="topbar">',
           f'  <a class="brand" href="{rel(lang, page, lang, "index")}">'
           f'<img src="{asset(lang, page, "favicon.png")}" alt="" width="28" height="28">{cfg["app"]}</a>',
           '  <div class="display-controls">',
           # 16言語は横に並べると本文の幅を突き抜けるので、今の言語だけを出して開閉する（N-Back の LP と同じ。JS なし）
           f'    <nav class="langs" aria-label="{cfg["pick"]}">',
           '      <details class="langpick">',
           f'        <summary>{cfg["native"]}</summary>',
           '        <ul>']
    for other, ocfg in LANGS.items():
        cur = ' aria-current="true"' if other == lang else ""
        out.append(f'          <li><a lang="{other}" hreflang="{other}" '
                   f'href="{rel(lang, page, other, page)}"{cur}>{ocfg["native"]}</a></li>')
    out += ['        </ul>', '      </details>', '    </nav>']
    out.append('    <fieldset class="themes">')
    out.append(f'      <legend class="visually-hidden">{cfg["theme"]}</legend>')
    for theme in ("auto", "light", "dark"):
        checked = " checked" if theme == "auto" else ""
        out.append(f'      <input class="visually-hidden" type="radio" name="theme" '
                   f'id="theme-{theme}" value="{theme}" autocomplete="off"{checked}>')
        out.append(f'      <label for="theme-{theme}">{cfg[f"theme_{theme}"]}</label>')
    out.append('    </fieldset>')
    out.append('  </div>')
    out.append('  <nav class="pages">')
    # 先頭の「トップ」はアイコンとアプリ名のリンクと同じ行き先。リンクに見えにくいので文字でも出す
    for p in ["index", *NAV]:
        cur = ' aria-current="page"' if p == page else ""
        label = cfg["home"] if p == "index" else cfg[p]
        out.append(f'    <a href="{rel(lang, page, lang, p)}"{cur}>{label}</a>')
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

# 2026-10-23 まで en を置いていた `en/` の URL。外（ストアの登録・共有されたリンク・TestFlight 版のアプリ）から
# 開かれても迷わないよう、直下の英語ページへ飛ばす受け皿を置く。**消さない**（公開済みの URL は消さない決まり）
OLD_EN_DIR = "en"


def redirect_page(page: str) -> str:
    """JS を使わない受け皿（meta refresh ＋ canonical ＋ noindex ＋ 手で辿れるリンク）"""
    target = url_for("en", page)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<title>{LANGS["en"]["app"]}</title>
</head>
<body>
<p>This page has moved: <a href="{target}">{target}</a></p>
</body>
</html>
"""


def apply(text: str, lang: str, page: str) -> str:
    for key, fn in BLOCKS.items():
        pattern = re.compile(f"(<!--chrome:{key}-->).*?(<!--/chrome:{key}-->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"目印 chrome:{key} が無い: {lang}/{page}")
        text = pattern.sub(lambda m: f"{m.group(1)}\n{fn(lang, page)}\n{m.group(2)}", text)
    text = re.sub(r'(<p class="updated" data-updated="(\d{4}-\d{2}-\d{2})">).*?(</p>)',
                  lambda m: f"{m.group(1)}{date_text(lang, m.group(2))}{m.group(3)}", text, flags=re.S)
    # 右から左の言語（ar・he）は dir を付ける。ほかは付けない（付いていたら外す）
    direction = ' dir="rtl"' if LANGS[lang].get("rtl") else ""
    text = re.sub(r'<html lang="[^"]*"(?: dir="[^"]*")?>', f'<html lang="{lang}"{direction}>', text, count=1)
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

    for page in PAGES:
        d = "/".join(p for p in (OLD_EN_DIR, PAGES[page]) if p)
        path = ROOT / d / "index.html"
        want = redirect_page(page)
        if not path.exists() or path.read_text(encoding="utf-8") != want:
            stale.append(str(path.relative_to(ROOT)))
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(want, encoding="utf-8")

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
