# Source ingestion and provenance

## Repository ingestion remains disabled

The public repository remains metadata-only for third-party sources. Do not store transcripts, audio, video, scraped article bodies, official IELTS test questions, answer keys, candidate responses belonging to others, official band-descriptor text, or substantial excerpts in Git, fixtures, releases, or CI artifacts.

A separate **local-only learner library** is now available for text explicitly supplied by the learner. It accepts UTF-8 text and files and stores the supplied body in a local SQLite database outside the repository's tracked files. It does not fetch URLs, scrape pages, download transcripts, or upload the database. This local capability is not permission to import any particular third-party work: the learner must determine that the proposed access and processing are lawful and permitted for their circumstances. The tool's rights-status field is descriptive metadata, not a legal decision.

The source metadata crawl workflow is deliberately manual-only. It is not run on pull requests or on a schedule. A metadata check, robots.txt response, HTTP header, public URL, or content hash is not legal permission and does not establish that a source may be accessed, copied, transformed, or republished.

## Rights review gate

Before importing or otherwise interacting with third-party material, identify the exact material, source, intended operation, storage location, and disclosure audience. Review applicable terms and rights for the specific jurisdiction and use. Distinguish viewing, automated access, metadata collection, text/data mining, extraction, transformation, quotation, private storage, publication, redistribution, and commercial use. Do not infer that permission for one activity covers another.

If rights, terms, or legal basis are unclear, do not access or use the material. The local tool's personal_copy_unverified or unknown values do not override this rule. Keep permission evidence private; never commit contracts, correspondence, contact details, or restricted source copies. Any proposed publication or sharing requires explicit maintainer review and documented permission covering the exact operation.

## Local data handling

- Default database: .local/knowledge.sqlite3. The directory is ignored by Git and uses best-effort 0700 permissions; the database uses best-effort 0600 permissions.
- These mode bits are not encryption at rest. Full-disk encryption and secure backups remain the user's responsibility.
- Do not store third-party texts, personal learner records, or private excerpts in repository fixtures, GitHub issues, workflow logs, or artifacts.
- Source deletion removes its segments, cards, and relations that touch those cards. SQLite secure_delete is enabled, but this is not a guarantee against filesystem snapshots, SSD wear-leveling, backups, or synchronized copies.
- Treat local database backups and exports as sensitive copies with the same restrictions as the source.
- Do not point the database to a shared/synchronized folder unless its privacy and retention properties have been reviewed.

## Safe project content

New repository examples and evaluation fixtures must be independently authored or synthetic. Do not imitate distinctive third-party passages or closely paraphrase protected materials. Do not use IELTS test content, paid preparation material, candidate submissions from other people, or official answer keys as fixtures. Do not use IELTS logos or imply endorsement or affiliation.

## Registry interpretation

Source registry entries are administrative metadata only. A status field is not a legal opinion or blanket clearance. The statuses cleared or licensed can only refer to a narrowly documented use after review; neither authorizes unrelated uses.

## Statuses

- pending: not reviewed.
- under_review: review underway or legal interpretation uncertain.
- cleared: reviewer approved a narrowly specified use based on a documented legal basis; not a general license.
- licensed: written permission covers the exact use and territory.
- restricted: some uses may be allowed, but publication/redistribution is not cleared.
- blocked: use is not approved.
- expired: permission or clearance expired or is no longer reliable.

## Permission record

Capture a private evidence reference, reviewer, review date, rights holder, allowed use, commercial status, redistribution, modification, attribution, territory, expiry, and conditions. Keep this evidence outside Git.
