import json
import os

import httpx
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(page_title="Synergo lokale chatbot", layout="wide")
st.title("Synergo - Lokale chatbot met kennisbank")
st.caption("100% lokaal - geen data verlaat je machine")

if not API_KEY:
    st.error("API_KEY ontbreekt. Configureer .env en herstart de containers.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []


def fetch_documents() -> list[dict]:
    try:
        r = httpx.get(f"{BACKEND_URL}/api/kb/documents", headers=HEADERS, timeout=10.0)
        if r.status_code == 200:
            return r.json()
    except httpx.HTTPError:
        pass
    return []


with st.sidebar:
    st.header("Kennisbank")
    use_kb = st.toggle("Gebruik kennisbank bij beantwoorden", value=True)

    uploaded = st.file_uploader(
        "Upload document",
        type=["pdf", "txt", "md"],
        help="Toegestane formaten: PDF, TXT, MD. Max 25 MB.",
    )
    if uploaded is not None:
        if st.button("Indexeren", type="primary"):
            with st.spinner(f"Bezig met indexeren van {uploaded.name}..."):
                try:
                    r = httpx.post(
                        f"{BACKEND_URL}/api/kb/upload",
                        headers=HEADERS,
                        files={"file": (uploaded.name, uploaded.getvalue())},
                        timeout=600.0,
                    )
                    if r.status_code == 200:
                        info = r.json()
                        st.success(
                            f"Toegevoegd: {info['doc_name']} ({info['chunks']} chunks)"
                        )
                        st.rerun()
                    else:
                        try:
                            detail = r.json().get("detail", r.text)
                        except Exception:
                            detail = r.text
                        st.error(f"Upload mislukt ({r.status_code}): {detail}")
                except httpx.HTTPError as e:
                    st.error(f"Verbinding met backend mislukt: {e}")

    st.divider()
    st.subheader("Documenten in kennisbank")
    docs = fetch_documents()
    if not docs:
        st.caption("Nog geen documenten geindexeerd.")
    for d in docs:
        col1, col2 = st.columns([5, 1])
        col1.write(d["doc_name"])
        if col2.button("X", key=f"del-{d['doc_id']}", help="Verwijder uit kennisbank"):
            try:
                httpx.delete(
                    f"{BACKEND_URL}/api/kb/documents/{d['doc_id']}",
                    headers=HEADERS,
                    timeout=30.0,
                )
            except httpx.HTTPError as e:
                st.error(f"Verwijderen mislukt: {e}")
            st.rerun()

    st.divider()
    if st.button("Wis chatgeschiedenis"):
        st.session_state.messages = []
        st.rerun()


for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander(f"Bronnen ({len(m['sources'])})"):
                for s in m["sources"]:
                    st.caption(
                        f"- {s.get('doc_name', 'onbekend')} (afstand: {s.get('distance', 0):.3f})"
                    )


prompt = st.chat_input("Stel je vraag...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full = ""
        sources: list[dict] = []
        error: str | None = None
        payload = {
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            "use_kb": use_kb,
        }
        try:
            with httpx.stream(
                "POST",
                f"{BACKEND_URL}/api/chat",
                headers={**HEADERS, "Content-Type": "application/json"},
                json=payload,
                timeout=httpx.Timeout(600.0, read=None),
            ) as resp:
                if resp.status_code != 200:
                    body = resp.read().decode("utf-8", errors="ignore")
                    error = f"Backend fout {resp.status_code}: {body}"
                    placeholder.error(error)
                else:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            evt = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        kind = evt.get("type")
                        if kind == "token":
                            full += evt.get("data", "")
                            placeholder.markdown(full + " |")
                        elif kind == "sources":
                            sources = evt.get("data", []) or []
                        elif kind == "error":
                            error = evt.get("data", "Onbekende fout")
                            placeholder.error(error)
                        elif kind == "done":
                            placeholder.markdown(full)
        except httpx.HTTPError as e:
            error = f"Verbinding met backend mislukt: {e}"
            placeholder.error(error)

        if not error:
            placeholder.markdown(full)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": full or (error or ""),
            "sources": sources,
        }
    )
    if sources:
        st.rerun()
