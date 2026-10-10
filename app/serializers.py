from app.models import Message, Project, Share, Version


def version_out(v: Version, include_files: bool = True) -> dict:
    data = {
        "id": v.id,
        "number": v.number,
        "source": v.source,
        "label": v.label,
        "summary": v.summary,
        "file_count": len(v.files),
        "created_at": v.created_at.isoformat(),
    }
    if include_files:
        data["files"] = v.files
    return data


def message_out(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "agent": m.agent,
        "content": m.content,
        "version_id": m.version_id,
        "created_at": m.created_at.isoformat(),
    }


def project_summary(p: Project) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
        "version_count": len(p.versions),
    }


def share_out(s: Share) -> dict:
    return {
        "slug": s.slug,
        "version_id": s.version_id,
        "version_number": s.version.number,
        "views": s.views,
        "updated_at": s.updated_at.isoformat(),
    }
