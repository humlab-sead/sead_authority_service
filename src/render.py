from psycopg.rows import dict_row


async def render_preview(id: str, id_base: str, cursor) -> ValueError | str:
    """Provides a generic HTML preview for a given entity ID."""

    if not id.startswith(id_base):
        raise ValueError("Invalid ID format", status_code=400)

    parts: list[str] = id.replace(id_base, "").split("/")
    if len(parts) != 2:
        raise ValueError("Invalid ID path", status_code=400)

    entity_path, entity_id_str = parts

    strategy = next(
        (s for s in app.state.strategies.values() if s.get_id_path() == entity_path),
        None,
    )

    if not strategy:
        raise ValueError(f"Unknown entity type: {entity_path}", status_code=404)

    try:
        async with cursor(row_factory=dict_row) as cur:
            details = await strategy.get_details(entity_id_str, cur)

        if not details:
            raise ValueError(
                f"Entity with ID {entity_id_str} not found or preview not implemented.",
                status_code=404,
            )

        html = "<div style='padding:10px; font:14px sans-serif; line-height:1.6;'>"
        # Use 'Name' or 'label' for the title, falling back to the first value
        title = (
            details.get("Name")
            or details.get("label")
            or next(iter(details.values()), "Details")
        )
        html += f"<h3 style='margin-top:0;'>{title}</h3>"

        for key, value in details.items():
            if value is not None and str(value).strip() != "":
                html += f"<div style='margin-bottom:5px;'>"
                html += f"<strong style='color:#333; min-width:100px; display:inline-block;'>{key}:</strong> "
                html += f"<span>{value}</span>"
                html += "</div>"

        html += "</div>"
        return html

    except Exception as e:
        raise ValueError(f"Error fetching preview: {str(e)}", status_code=500)
