#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AJR Avaliação Física e Performance — Giro de Notícias
======================================================
Coleta as últimas notícias de esporte mundial e ciência da performance
via feeds RSS de grandes portais, resume o conteúdo e salva tudo em
`noticias.json` na raiz do repositório (o site lê esse arquivo).

Executado automaticamente 1x/dia pelo GitHub Actions
(.github/workflows/atualizar_noticias.yml).

Dependência: feedparser  (pip install feedparser)
"""

import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path

import feedparser

# ──────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────────

# Feeds RSS: (url, nome da fonte, categoria exibida no card)
FEEDS = [
    ("https://ge.globo.com/rss/ge/",                                        "ge (Globo Esporte)", "Esporte"),
    ("https://feeds.bbci.co.uk/sport/rss.xml",                              "BBC Sport",          "Esporte Mundial"),
    ("https://www.espn.com/espn/rss/news",                                  "ESPN",               "Esporte Mundial"),
    ("https://www.sciencedaily.com/rss/health_medicine/sports_medicine.xml","ScienceDaily",       "Ciência & Performance"),
    ("https://www.sciencedaily.com/rss/health_medicine/fitness.xml",        "ScienceDaily",       "Fitness"),
]

MAX_POR_FEED = 6          # quantas notícias pegar de cada feed
MAX_TOTAL = 24            # limite total no site
TAMANHO_RESUMO = 300      # caracteres do resumo

ARQUIVO_SAIDA = Path(__file__).resolve().parent.parent / "noticias.json"


# ──────────────────────────────────────────────────────────────
# FUNÇÕES
# ──────────────────────────────────────────────────────────────

def limpar_html(texto: str) -> str:
    """Remove tags HTML e normaliza espaços — nosso 'resumidor' de texto."""
    if not texto:
        return ""
    texto = html.unescape(texto)
    texto = re.sub(r"<[^>]+>", " ", texto)          # remove tags
    texto = re.sub(r"\s+", " ", texto).strip()      # normaliza espaços
    return texto


def resumir(texto: str, limite: int = TAMANHO_RESUMO) -> str:
    """Corta o texto no limite sem quebrar palavra, adicionando reticências.

    OBS: para resumo por IA, substitua esta função por uma chamada à API
    da Anthropic (claude-haiku) usando um secret ANTHROPIC_API_KEY.
    O resumo do próprio RSS já é curto e de qualidade editorial, então
    a versão sem IA é gratuita e 100% confiável no Actions.
    """
    texto = limpar_html(texto)
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0]
    return corte.rstrip(".,;:") + "…"


def data_iso(entry) -> str:
    """Extrai a data de publicação do item RSS em formato ISO 8601."""
    for campo in ("published_parsed", "updated_parsed"):
        t = entry.get(campo)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def coletar() -> list[dict]:
    noticias = []
    titulos_vistos = set()

    for url, fonte, categoria in FEEDS:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                print(f"  [AVISO] feed vazio/inválido: {url}")
                continue

            adicionadas = 0
            for entry in feed.entries:
                if adicionadas >= MAX_POR_FEED:
                    break

                titulo = limpar_html(entry.get("title", ""))
                link = entry.get("link", "")
                if not titulo or not link:
                    continue

                # dedupe por título normalizado
                chave = re.sub(r"\W+", "", titulo.lower())
                if chave in titulos_vistos:
                    continue
                titulos_vistos.add(chave)

                resumo = resumir(entry.get("summary", entry.get("description", "")))
                if not resumo:
                    resumo = titulo  # fallback

                noticias.append({
                    "titulo": titulo,
                    "resumo": resumo,
                    "link": link,          # link original da matéria
                    "data": data_iso(entry),
                    "fonte": fonte,
                    "categoria": categoria,
                })
                adicionadas += 1

            print(f"  [OK] {fonte}: {adicionadas} notícias")
        except Exception as e:
            # um feed fora do ar não pode derrubar a atualização inteira
            print(f"  [ERRO] {url}: {e}")

    # mais recentes primeiro, limitado ao total
    noticias.sort(key=lambda n: n["data"], reverse=True)
    return noticias[:MAX_TOTAL]


def main():
    print("Coletando notícias…")
    noticias = coletar()

    if not noticias:
        print("Nenhuma notícia coletada — mantendo o noticias.json atual.")
        return  # não sobrescreve com arquivo vazio

    dados = {
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(noticias),
        "noticias": noticias,
    }

    ARQUIVO_SAIDA.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✔ {len(noticias)} notícias salvas em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
