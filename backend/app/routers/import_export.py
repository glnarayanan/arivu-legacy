"""
Import/export router - extracted from server.py (Phase 6, Plan 03).

Provides bookmark import (HTML/CSV/text), export, backup,
and import job tracking endpoints.
"""

import csv
import io
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response

from app.core.database import get_database
from app.core.dependencies import get_current_user, limiter
from app.models.import_job import BackupRequest
from app.services.ai_service import generate_ai_summaries
from app.services.content_service import calculate_reading_time, fetch_webpage_content

logger = logging.getLogger(__name__)

router = APIRouter(tags=["import-export"])


async def process_bulk_import(import_job_id: str, bookmark_ids: list[str], user_id: str):
    """Background task to process bulk import in two phases"""
    try:
        # Get own db reference inside background task
        db = get_database()

        total = len(bookmark_ids)
        logger.info(f"Starting bulk import processing for job {import_job_id}: {total} bookmarks")

        # Phase 1: Fast content fetching (no rate limit)
        content_fetched = 0
        failed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark:
                    continue

                content = await fetch_webpage_content(bookmark["url"])
                reading_time = calculate_reading_time(content.get("text_content", ""))

                await db.bookmarks.update_one(
                    {"id": bookmark_id},
                    {
                        "$set": {
                            "title": content.get("title"),
                            "description": content.get("description"),
                            "favicon": content.get("favicon"),
                            "thumbnail": content.get("thumbnail"),
                            "html_content": content.get("html_content"),
                            "text_content": content.get("text_content"),
                            "domain": content.get("domain"),
                            "reading_time": reading_time,
                            "updated_at": datetime.now(UTC).isoformat(),
                        }
                    },
                )
                content_fetched += 1

                # Update progress every 10 bookmarks
                if content_fetched % 10 == 0:
                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {
                            "$set": {
                                "content_fetched": content_fetched,
                                "updated_at": datetime.now(UTC).isoformat(),
                            }
                        },
                    )
            except Exception:
                failed += 1
                logger.exception(f"Error fetching content for bookmark {bookmark_id}")

        # Update after Phase 1 completion
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "content_fetched": content_fetched,
                    "failed": failed,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            },
        )

        logger.info(f"Phase 1 complete for job {import_job_id}: {content_fetched}/{total} fetched, {failed} failed")

        # Phase 2: Rate-limited AI processing
        ai_processed = 0

        for bookmark_id in bookmark_ids:
            try:
                bookmark = await db.bookmarks.find_one({"id": bookmark_id})
                if not bookmark or not bookmark.get("text_content"):
                    continue

                result = await generate_ai_summaries(bookmark["text_content"], bookmark_id)
                if result.get("processing_status") == "completed":
                    ai_processed += 1
                else:
                    failed += 1

                # Update progress every 5 AI processes
                if ai_processed % 5 == 0:
                    # Calculate ETA
                    elapsed = (
                        datetime.now(UTC)
                        - datetime.fromisoformat((await db.import_jobs.find_one({"id": import_job_id}))["created_at"])
                    ).total_seconds()
                    remaining = total - ai_processed
                    eta = datetime.now(UTC) + timedelta(
                        seconds=((elapsed / ai_processed) * remaining if ai_processed > 0 else 0)
                    )

                    await db.import_jobs.update_one(
                        {"id": import_job_id},
                        {
                            "$set": {
                                "ai_processed": ai_processed,
                                "failed": failed,
                                "estimated_completion_time": eta.isoformat(),
                                "updated_at": datetime.now(UTC).isoformat(),
                            }
                        },
                    )
            except Exception:
                failed += 1
                logger.exception(f"Error processing AI for bookmark {bookmark_id}")

        # Mark job as completed
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "ai_processed": ai_processed,
                    "failed": failed,
                    "status": "completed",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            },
        )

        logger.info(f"Bulk import completed for job {import_job_id}: {ai_processed}/{total} AI processed")

    except Exception:
        logger.exception(f"Error in bulk import job {import_job_id}")
        db = get_database()
        await db.import_jobs.update_one(
            {"id": import_job_id},
            {
                "$set": {
                    "status": "failed",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            },
        )


@router.post("/bookmarks/import")
@limiter.limit("3/hour")  # Limit imports to prevent abuse
async def import_bookmarks(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Import bookmarks from browser HTML file"""
    try:
        from bs4 import BeautifulSoup

        db = get_database()

        # Read file content from request body
        file = await request.body()

        # Validate file exists
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")

        # Validate file size (max 10MB)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if len(file) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")

        # Decode and validate file is valid UTF-8 HTML
        try:
            html_content = file.decode("utf-8") if isinstance(file, bytes) else file
        except UnicodeDecodeError as err:
            logger.warning(f"User {current_user['id']} attempted to import non-UTF-8 file")
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded HTML") from err

        # Validate file contains content
        if not html_content or len(html_content.strip()) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # Detect file format: HTML bookmark file, CSV, or plain text URL list
        html_lower = html_content.lower()
        is_html_format = "<a" in html_lower or "<A" in html_lower

        # Detect CSV format (looks for comma-separated values)
        lines = html_content.strip().split("\n")
        is_csv_format = False
        if not is_html_format and len(lines) > 0:
            # Check if first few lines contain commas (likely CSV)
            first_lines = lines[:5]
            comma_count = sum(1 for line in first_lines if "," in line)
            is_csv_format = comma_count >= len(first_lines) * 0.5  # At least 50% have commas

        urls_to_import = []
        MAX_BOOKMARKS_PER_IMPORT = 1000

        if is_html_format:
            # Process HTML bookmark file (browser export format)
            soup = BeautifulSoup(html_content, "html.parser")
            links = soup.find_all("a")

            if not links or len(links) == 0:
                logger.warning(f"User {current_user['id']} imported HTML file with no parseable bookmarks")
                raise HTTPException(status_code=400, detail="No bookmarks found in HTML file")

            for link in links[:MAX_BOOKMARKS_PER_IMPORT]:
                url = link.get("href")
                title = link.get_text(strip=True)

                if url and url.startswith("http"):
                    urls_to_import.append({"url": url, "title": title or urlparse(url).netloc})

        elif is_csv_format:
            # Process CSV file (URL in first column, optional title in second column)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                line = line.strip()
                if not line:
                    continue

                # Split by comma
                parts = [p.strip().strip('"').strip("'") for p in line.split(",")]

                if len(parts) == 0:
                    continue

                url = parts[0]
                title = parts[1] if len(parts) > 1 and parts[1] else None

                # Skip header row (common CSV headers)
                if url.lower() in ["url", "link", "website", "address", "bookmark"]:
                    continue

                # Only import valid HTTP(S) URLs
                if url and url.startswith("http"):
                    urls_to_import.append({"url": url, "title": title or urlparse(url).netloc})

        else:
            # Process plain text URL list (one URL per line)
            for line in lines[:MAX_BOOKMARKS_PER_IMPORT]:
                url = line.strip()

                # Skip empty lines and non-URL lines
                if not url or not url.startswith("http"):
                    continue

                urls_to_import.append({"url": url, "title": urlparse(url).netloc})

        # Validate at least one URL was found
        if not urls_to_import:
            raise HTTPException(status_code=400, detail="No valid URLs found in file")

        logger.info(f"User {current_user['id']} importing {len(urls_to_import)} bookmarks")

        # Create import job
        import_job = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "total_bookmarks": len(urls_to_import),
            "content_fetched": 0,
            "ai_processed": 0,
            "failed": 0,
            "status": "processing",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "estimated_completion_time": None,
        }
        await db.import_jobs.insert_one(import_job)

        # Create placeholder bookmarks
        bookmark_ids = []
        imported_count = 0

        for item in urls_to_import:
            url = item["url"]
            title = item["title"]

            if url and url.startswith("http"):
                bookmark = {
                    "id": str(uuid.uuid4()),
                    "user_id": current_user["id"],
                    "url": url,
                    "title": title or urlparse(url).netloc,
                    "description": None,
                    "favicon": None,
                    "thumbnail": None,
                    "html_content": None,
                    "text_content": None,
                    "domain": urlparse(url).netloc,
                    "reading_time": None,
                    "read_status": False,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                    "version": 1,  # Optimistic locking (REL-03)
                }

                await db.bookmarks.insert_one(bookmark)

                ai_summary = {
                    "id": str(uuid.uuid4()),
                    "bookmark_id": bookmark["id"],
                    "processing_status": "pending",
                    "created_at": datetime.now(UTC).isoformat(),
                }
                await db.ai_summaries.insert_one(ai_summary)

                bookmark_ids.append(bookmark["id"])
                imported_count += 1

        # Start background bulk processing
        if background_tasks and bookmark_ids:
            background_tasks.add_task(process_bulk_import, import_job["id"], bookmark_ids, current_user["id"])

        logger.info(f"Successfully imported {imported_count} bookmarks for user {current_user['id']}")
        return {
            "message": f"Imported {imported_count} bookmarks",
            "count": imported_count,
            "import_job_id": import_job["id"],
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are validation errors with proper messages)
        raise
    except Exception as e:
        logger.exception(f"Error importing bookmarks for user {current_user['id']}")
        raise HTTPException(status_code=500, detail=f"Failed to import bookmarks: {str(e)}") from e


@router.get("/import-jobs/{job_id}")
async def get_import_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get import job progress"""
    db = get_database()
    job = await db.import_jobs.find_one({"id": job_id, "user_id": current_user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job


@router.get("/import-jobs")
async def get_import_jobs(current_user: dict = Depends(get_current_user)):
    """Get all import jobs for user"""
    db = get_database()
    jobs = (
        await db.import_jobs.find({"user_id": current_user["id"]}, {"_id": 0})
        .sort("created_at", -1)
        .limit(50)
        .to_list(None)
    )
    return jobs


@router.get("/bookmarks/export")
async def export_bookmarks(current_user: dict = Depends(get_current_user)):
    """Export bookmarks as browser-compatible HTML"""
    db = get_database()
    projection = {"_id": 0, "url": 1, "title": 1, "created_at": 1}
    bookmarks = (
        await db.bookmarks.find({"user_id": current_user["id"]}, projection)
        .sort("created_at", -1)
        .limit(5000)
        .to_list(None)
    )

    html_parts = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Arivu Bookmarks</TITLE>",
        "<H1>Arivu Bookmarks</H1>",
        "<DL><p>",
    ]

    for bookmark in bookmarks:
        add_date = int(datetime.fromisoformat(bookmark["created_at"]).timestamp())
        title = bookmark.get("title", bookmark.get("url", "Untitled"))
        url = bookmark.get("url", "")
        html_parts.append(f'    <DT><A HREF="{url}" ADD_DATE="{add_date}">{title}</A>')

    html_parts.append("</DL><p>")

    return Response(
        content="\n".join(html_parts),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="arivu_bookmarks_{datetime.now().strftime("%Y%m%d")}.html"'
        },
    )


@router.post("/bookmarks/backup")
async def backup_bookmarks(
    backup_request: BackupRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a comprehensive backup of bookmarks with options.

    Formats:
    - html: Browser-compatible bookmark file
    - json: Full data export with nested AI summaries and notes
    - csv: Spreadsheet-friendly format
    """
    db = get_database()

    # Build query with date filtering
    query = {"user_id": current_user["id"]}
    if backup_request.date_from:
        query["created_at"] = {"$gte": backup_request.date_from.isoformat()}
    if backup_request.date_to:
        if "created_at" in query:
            query["created_at"]["$lte"] = backup_request.date_to.isoformat()
        else:
            query["created_at"] = {"$lte": backup_request.date_to.isoformat()}

    # Fetch bookmarks
    bookmarks = (
        await db.bookmarks.find(query, {"_id": 0, "embedding": 0, "html_content": 0})
        .sort("created_at", -1)
        .limit(10000)
        .to_list(None)
    )

    # Optionally fetch AI summaries
    if backup_request.include_ai_summaries and bookmarks:
        bookmark_ids = [b["id"] for b in bookmarks]
        summaries = await db.ai_summaries.find({"bookmark_id": {"$in": bookmark_ids}}, {"_id": 0}).to_list(None)
        summaries_map = {s["bookmark_id"]: s for s in summaries}

        for bookmark in bookmarks:
            if bookmark["id"] in summaries_map:
                bookmark["ai_summary"] = summaries_map[bookmark["id"]]

    # Optionally fetch notes
    if backup_request.include_notes and bookmarks:
        bookmark_ids = [b["id"] for b in bookmarks]
        notes = await db.notes.find(
            {"bookmark_id": {"$in": bookmark_ids}, "user_id": current_user["id"]},
            {"_id": 0},
        ).to_list(None)
        notes_map = {}
        for note in notes:
            bid = note["bookmark_id"]
            if bid not in notes_map:
                notes_map[bid] = []
            notes_map[bid].append(note)

        for bookmark in bookmarks:
            if bookmark["id"] in notes_map:
                bookmark["notes"] = notes_map[bookmark["id"]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate output based on format
    if backup_request.format == "json":
        content = json.dumps(
            {
                "exported_at": datetime.now(UTC).isoformat(),
                "total_bookmarks": len(bookmarks),
                "include_notes": backup_request.include_notes,
                "include_ai_summaries": backup_request.include_ai_summaries,
                "bookmarks": bookmarks,
            },
            indent=2,
            default=str,
        )

        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.json"'},
        )

    elif backup_request.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = [
            "url",
            "title",
            "domain",
            "created_at",
            "read_status",
            "reading_time",
        ]
        if backup_request.include_ai_summaries:
            headers.extend(["summary", "tags"])
        if backup_request.include_notes:
            headers.append("notes")
        writer.writerow(headers)

        # Data rows
        for b in bookmarks:
            row = [
                b.get("url", ""),
                b.get("title", ""),
                b.get("domain", ""),
                b.get("created_at", ""),
                b.get("read_status", False),
                b.get("reading_time", ""),
            ]
            if backup_request.include_ai_summaries:
                ai = b.get("ai_summary", {})
                row.append(ai.get("one_sentence", ""))
                row.append(", ".join(ai.get("suggested_tags", [])))
            if backup_request.include_notes:
                notes = b.get("notes", [])
                row.append(" | ".join([n.get("content", "") for n in notes]))
            writer.writerow(row)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.csv"'},
        )

    else:  # HTML format (default)
        html_parts = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Arivu Bookmarks Backup</TITLE>",
            "<H1>Arivu Bookmarks Backup</H1>",
            f"<!-- Exported: {datetime.now(UTC).isoformat()} -->",
            f"<!-- Total: {len(bookmarks)} bookmarks -->",
            "<DL><p>",
        ]

        for bookmark in bookmarks:
            add_date = int(datetime.fromisoformat(bookmark["created_at"]).timestamp())
            title = bookmark.get("title", bookmark.get("url", "Untitled"))
            url = bookmark.get("url", "")
            tags = ""
            if backup_request.include_ai_summaries:
                ai = bookmark.get("ai_summary", {})
                tag_list = ai.get("suggested_tags", [])
                if tag_list:
                    tags = f' TAGS="{",".join(tag_list)}"'
            html_parts.append(f'    <DT><A HREF="{url}" ADD_DATE="{add_date}"{tags}>{title}</A>')

        html_parts.append("</DL><p>")

        return Response(
            content="\n".join(html_parts),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="arivu_backup_{timestamp}.html"'},
        )
