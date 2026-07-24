"""
Integration tests for GET /api/v1/projects/{project_id}/export/markdown.

Written against the conventions described in ARCHITECTURE.md §9: real
httpx.AsyncClient against the actual app, a `make_user` fixture that
registers a fresh user via the real /api/v1/auth/register endpoint per call,
and the standard 404-vs-403 ownership distinction. Adjust the exact
`make_user` / `client` fixture signatures below if they differ slightly from
what's shown here (e.g. whether make_user returns auth headers directly or a
token to build them from) — the assertions are the part that matters.
"""
import pytest


@pytest.mark.asyncio
async def test_export_markdown_includes_notes_links_and_highlights(client, make_user):
    _ , headers = await make_user()

    project_resp = await client.post(
        "/api/v1/projects",
        json={"name": "AI Research", "description": "Collecting papers on LLMs"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    link_resp = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={
            "url": "https://arxiv.org/abs/1706.03762",
            "title": "Attention Is All You Need",
            "snippet": "The dominant sequence transduction models...",
        },
        headers=headers,
    )
    assert link_resp.status_code == 201
    link_id = link_resp.json()["id"]

    note_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={
            "title": "Key takeaway",
            "content": "Self-attention replaces recurrence entirely.",
            "source_link_id": link_id,
        },
        headers=headers,
    )
    assert note_resp.status_code == 201

    resp = await client.get(
        f"/api/v1/projects/{project_id}/export/markdown", headers=headers
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "attachment" in resp.headers["content-disposition"]
    assert ".md" in resp.headers["content-disposition"]

    body = resp.text
    assert "# AI Research" in body
    assert "Collecting papers on LLMs" in body
    assert "## Notes" in body
    assert "Key takeaway" in body
    assert "Self-attention replaces recurrence entirely." in body
    assert "## Links" in body
    assert "Attention Is All You Need" in body
    assert "https://arxiv.org/abs/1706.03762" in body


@pytest.mark.asyncio
async def test_export_markdown_empty_project(client, make_user):
    _ , headers = await make_user()

    project_resp = await client.post(
        "/api/v1/projects", json={"name": "Empty Project"}, headers=headers
    )
    project_id = project_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/export/markdown", headers=headers
    )

    assert resp.status_code == 200
    body = resp.text
    assert "_No notes yet._" in body
    assert "_No links saved yet._" in body


@pytest.mark.asyncio
async def test_export_markdown_requires_ownership(client, make_user):
    _, owner_headers = await make_user()
    _, other_headers = await make_user()

    project_resp = await client.post(
        "/api/v1/projects", json={"name": "Private Project"}, headers=owner_headers
    )
    project_id = project_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/export/markdown", headers=other_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_export_markdown_404_for_unknown_project(client, make_user):
    _ , headers = await make_user()

    resp = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/export/markdown",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_markdown_requires_auth(client):
    resp = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/export/markdown"
    )
    assert resp.status_code == 401

