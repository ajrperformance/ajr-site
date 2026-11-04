#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AJR Performance — Agenda dos pacotes de personal (/personal/<slug>)
====================================================================
Lê a configuração em _personal/alunos.json, busca os eventos de cada aluno
na Google Agenda (conta de serviço, somente leitura) e gera:

  personal/dados/<slug>.json   dados que a página do aluno exibe
  personal/<slug>/index.html   cópia do modelo personal/aluno.html

O histórico fixo (já conferido) nunca é alterado; as regras só valem para
eventos depois de historico.conferido_ate.

Uso:
  python3 scripts/agenda_personal.py                # lê a Google Agenda
  python3 scripts/agenda_personal.py --eventos arq.json   # teste local, sem Google
  python3 scripts/agenda_personal.py --agora 2026-11-04T21:17:00-03:00

Credencial: variável de ambiente GOOGLE_SERVICE_ACCOUNT_JSON com o conteúdo
da chave da conta de serviço (secret do GitHub). Nunca versionar a chave.
"""

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "_personal" / "alunos.json"
MODELO = RAIZ / "personal" / "aluno.html"
SAIDA_DADOS = RAIZ / "personal" / "dados"
BRT = timezone(timedelta(hours=-3))  # Brasil sem horário de verão desde 2019

DIAS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "sáb": 5, "dom": 6}


def norm(txt):
    """minúsculas, sem acento, espaços simples — para comparar textos."""
    txt = unicodedata.normalize("NFKD", txt or "")
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", txt).strip().lower()


# ──────────────────────────────────────────────────────────────
# Google Agenda
# ──────────────────────────────────────────────────────────────
def buscar_eventos_google(agenda, inicio, fim, fuso):
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    bruto = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not bruto:
        sys.exit("ERRO: GOOGLE_SERVICE_ACCOUNT_JSON não definido (secret do GitHub).")
    cred = service_account.Credentials.from_service_account_info(
        json.loads(bruto),
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    cred.refresh(Request())

    url = f"https://www.googleapis.com/calendar/v3/calendars/{requests.utils.quote(agenda)}/events"
    params = {
        "timeMin": inicio.isoformat(),
        "timeMax": fim.isoformat(),
        "singleEvents": "true",
        "orderBy": "startTime",
        "timeZone": fuso,
        "maxResults": 2500,
    }
    eventos = []
    while True:
        r = requests.get(url, params=params, headers={"Authorization": f"Bearer {cred.token}"}, timeout=30)
        if r.status_code != 200:
            sys.exit(f"ERRO Google Calendar {r.status_code}: {r.text[:300]}")
        dados = r.json()
        eventos += dados.get("items", [])
        if not dados.get("nextPageToken"):
            return eventos
        params["pageToken"] = dados["nextPageToken"]


# ──────────────────────────────────────────────────────────────
# Regras
# ──────────────────────────────────────────────────────────────
def quando(campo):
    """start/end/originalStartTime → datetime com fuso (dia inteiro = 00:00)."""
    if not campo:
        return None
    if "dateTime" in campo:
        return datetime.fromisoformat(campo["dateTime"].replace("Z", "+00:00")).astimezone(BRT)
    if "date" in campo:
        return datetime.fromisoformat(campo["date"]).replace(tzinfo=BRT)
    return None


def ler_checkin(descricao):
    """Devolve ('realizada'|'nao', motivo) ou (None, None)."""
    texto = re.sub(r"<[^>]+>", "\n", descricao or "")  # descrição pode vir em HTML
    for linha in texto.splitlines():
        n = norm(linha)
        if "[check-in]" not in n:
            continue
        partes = [p.strip() for p in re.split(r"[·•|]", n.split("[check-in]", 1)[1])]
        if partes and partes[0].startswith("realizada"):
            return "realizada", None
        if partes and partes[0].startswith("nao aconteceu"):
            return "nao", (partes[1] if len(partes) > 1 else "")
    return None, None


def motivo_publico(motivo, titulo):
    """Nunca expõe o motivo literal; só categorias neutras."""
    m = norm(f"{motivo} {titulo}")
    if "feriado" in m or "finados" in m:
        return "feriado"
    if re.search(r"\b(professor|prof|aldemir|minha falha|falha minha|imprevisto meu)\b", m):
        return "imprevisto do professor"
    if re.search(r"\b(aluna|aluno|desmarc|cancelou|nao veio|faltou|nao pode)", m):
        return "desmarcada pela aluna"
    return "remarcada"


def processar_aluno(aluno, eventos, agora):
    total = int(aluno["total"])
    hist = aluno.get("historico", {})
    corte = date.fromisoformat(hist.get("conferido_ate", aluno["pacote_inicio"]))
    dias_fixos = {DIAS[norm(d)[:3]] for d in aluno.get("dias_fixos", [])}
    filtro = norm(aluno["filtro"])

    aulas = {}        # data → aula
    remarcadas = {}   # data → item
    for a in hist.get("aulas", []):
        aulas[a["data"]] = {"data": a["data"], "status": "feita", "hora": a.get("hora"), "obs": a.get("obs")}
    for r in hist.get("remarcadas", []):
        remarcadas[r["data"]] = {"data": r["data"], "motivo": r.get("motivo") or "remarcada"}

    for ev in eventos:
        titulo = ev.get("summary") or ""
        if ev.get("status") == "cancelled" or filtro not in norm(titulo):
            continue
        ini, fim = quando(ev.get("start")), quando(ev.get("end"))
        if not ini:
            continue
        dia = ini.date()
        if dia <= corte or dia < date.fromisoformat(aluno["pacote_inicio"]):
            continue
        chave = dia.isoformat()
        hora = ini.strftime("%H:%M") if "dateTime" in ev["start"] else None

        checkin, motivo = ler_checkin(ev.get("description"))
        if checkin == "nao" or titulo.strip().upper().startswith("X "):
            if chave not in aulas:
                remarcadas.setdefault(chave, {"data": chave, "motivo": motivo_publico(motivo or "", titulo)})
            continue

        orig = quando(ev.get("originalStartTime"))
        movido = orig is not None and orig != ini
        obs = "reposição" if (dias_fixos and dia.weekday() not in dias_fixos and (movido or not ev.get("recurringEventId"))) else None

        passou = (fim or ini) <= agora
        status = "feita" if (checkin == "realizada" or passou) else "agendada"
        atual = aulas.get(chave)
        if atual and atual["status"] == "feita":
            continue  # sem datas duplicadas; feita vale mais que agendada
        aulas[chave] = {"data": chave, "status": status, "hora": hora, "obs": obs}
        remarcadas.pop(chave, None)

    lista = sorted(aulas.values(), key=lambda a: a["data"])[:total]
    for i, a in enumerate(lista, 1):
        a["n"] = i
    feitas = sum(1 for a in lista if a["status"] == "feita")
    vence = lista[-1]["data"] if len(lista) == total else None
    limite = vence or "9999-12-31"
    remarc = sorted((r for r in remarcadas.values() if r["data"] <= limite), key=lambda r: r["data"])

    return {
        "nome": aluno["nome"],
        "local": aluno.get("local", ""),
        "horarios": aluno.get("horarios", ""),
        "pacote_inicio": aluno["pacote_inicio"],
        "total": total,
        "feitas": feitas,
        "faltam": total - feitas,
        "vence": vence,
        "concluido": feitas >= total,
        "aulas": [{k: v for k, v in a.items() if v is not None} for a in lista],
        "remarcadas": remarc,
    }


# ──────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eventos", help="arquivo JSON com eventos (teste local, sem Google)")
    ap.add_argument("--agora", help="data/hora ISO para simular o momento da execução")
    args = ap.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    agora = datetime.fromisoformat(args.agora).astimezone(BRT) if args.agora else datetime.now(BRT)
    agora = agora.replace(microsecond=0)
    modelo = MODELO.read_text(encoding="utf-8")
    SAIDA_DADOS.mkdir(parents=True, exist_ok=True)

    slugs = set()
    for aluno in cfg["alunos"]:
        slug = aluno["slug"]
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*-[a-z0-9]{8}", slug):
            sys.exit(f"ERRO: slug inválido '{slug}' (use nome-sobrenome-xxxxxxxx).")
        if slug in slugs:
            sys.exit(f"ERRO: slug repetido '{slug}'.")
        slugs.add(slug)

        inicio = datetime.fromisoformat(aluno["pacote_inicio"]).replace(tzinfo=BRT)
        fim = agora + timedelta(days=int(cfg.get("dias_a_frente", 21)))
        if args.eventos:
            eventos = json.loads(Path(args.eventos).read_text(encoding="utf-8")).get("items", [])
        else:
            eventos = buscar_eventos_google(cfg["agenda"], inicio, fim, cfg.get("fuso", "America/Sao_Paulo"))
        eventos = [e for e in eventos if (quando(e.get("start")) or agora) <= fim]

        dados = processar_aluno(aluno, eventos, agora)

        # Só regrava se algo mudou (o carimbo de hora sozinho não conta)
        arq = SAIDA_DADOS / f"{slug}.json"
        antigo = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
        antigo.pop("atualizado", None)
        if antigo != dados:
            dados["atualizado"] = agora.isoformat()
            arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{slug}: atualizado ({dados['feitas']}/{dados['total']} feitas, vence {dados['vence']})")
        else:
            print(f"{slug}: sem mudanças")

        pagina = RAIZ / "personal" / slug / "index.html"
        pagina.parent.mkdir(parents=True, exist_ok=True)
        if not pagina.exists() or pagina.read_text(encoding="utf-8") != modelo:
            pagina.write_text(modelo, encoding="utf-8")

    # Remove páginas/dados de slugs que saíram da configuração
    for p in (RAIZ / "personal").iterdir():
        if p.is_dir() and p.name not in slugs and p.name != "dados":
            shutil.rmtree(p)
    for p in SAIDA_DADOS.glob("*.json"):
        if p.stem not in slugs:
            p.unlink()


if __name__ == "__main__":
    main()
