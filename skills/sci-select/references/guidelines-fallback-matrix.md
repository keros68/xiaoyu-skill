# Guideline Retrieval Fallback

Read this file only when an official Author Guidelines page is blocked, thin, or a hub. It is an operating fallback, not a promise that any provider will work today.

## Sequence

1. Resolve journal identity, publisher, article type, and the official Author Guidelines URL. Follow official subpages when the first page is a hub.
2. Retrieve the official page with an available no-key scraper or reader. A Firecrawl scrape may be used when available; do not require user setup or consume a quota when a simpler reader works.
3. If `TAVILY_API_KEY` already exists, try Tavily extract for the official URL. Never expose or write the key.
4. Try the lightweight reader cascade for the official URL: Jina, then Defuddle, then `agent-fetch` only if it is already available. Do not make Node/npm installation a prerequisite.
5. Search for official mirrors or publisher help pages. Only then use a clearly identified third-party guideline summary as tentative evidence.
6. If usable official evidence is still unavailable, ask the user to paste the relevant current guideline text.

## Accept and label evidence

Accept a page only when it has substantial body text and guideline signals such as `abstract`, `manuscript`, `word`, `figure`, `reference`, `submission`, or `author guidelines`. Reject security-verification, cookie, login, access-denied, 404, navigation-only, or near-empty output. Record `partial` when an official page has some relevant text but lacks the needed requirement.

| Evidence type | May support |
|---|---|
| Official page or user-pasted official text | confirmed requirement and P0 finding |
| Official hub/subpage with incomplete text | only the explicit content; otherwise `Unable to assess` |
| Third-party summary or search snippet | tentative direction and verification request, never confirmed P0 |

Use source status precisely: `succeeded` for a completed retrieval (including a confirmed no-match), `partial` for incomplete usable content, `attempted` for a failed/unusable retrieval, and `skipped` for an intentional non-query. Include the reason and the next fallback; do not report a blocked page as missing requirement.
