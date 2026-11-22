# Source ingestion and provenance

## Default: no third-party content ingestion

The public repository is metadata-only for third-party sources. Do not store transcripts, audio, video, scraped article bodies, official test questions, answer keys, candidate responses belonging to others, official band-descriptor text, or substantial excerpts.

The source metadata crawl workflow is deliberately manual-only. It is not run on pull requests or on a schedule. No crawl was executed as part of the current maintenance work. A metadata check, robots.txt response, HTTP header, public URL, or content hash is not legal permission and does not establish that a source may be accessed, copied, transformed, or republished.

## Rights review gate

Before any proposed interaction with a third-party source, identify the exact material and intended operation. Review applicable terms and rights for the specific jurisdiction and use. Distinguish viewing, automated access, metadata collection, text/data mining, extraction, transformation, quotation, publication, redistribution, and commercial use. Do not infer that permission for one activity covers another.

If rights, terms, or legal basis are unclear, do not access or use the material. Keep permission evidence private; never commit contracts, correspondence, contact details, or restricted source copies. Any future exception requires explicit maintainer approval and documented permission covering the exact operation.

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
