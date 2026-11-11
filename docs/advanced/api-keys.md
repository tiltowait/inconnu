# API Keys

Sign in on the website, open your account menu, and choose **API Keys**. Create a key for one ordinary server text channel where you are a Storyteller and can read message history. Save its secret when it is first shown; it cannot be displayed again. Each account can have five active keys. Keys expire after 90 days by default; choose 1–90 days or explicitly select **Never expires**. We recommend an expiration date.

Keys grant only `rolls:read`. They cannot access character sheets or modify data. Every request requires your current server membership, Storyteller status and channel permissions. Losing access prevents further requests. Leaving the server or removing the bot revokes its keys; returning does not reactivate them. Revoking a key cannot remove data already exported. Revoked and expired key records are cleaned up after thirty days.

Rolls excluded from statistics are never returned. Hidden rolls are included and marked with `hidden`. Exports include Discord user IDs of roll owners and character IDs, including those of players who did not create the key. Share a key only with an integration you trust.

## Read rolls

Send `GET /api/v1/rolls` on the website with `Authorization: Bearer <key>`.

| Parameter | Meaning |
| --- | --- |
| `start` | Inclusive UTC timestamp, such as `2026-06-01T18:00:00Z` |
| `end` | Exclusive UTC timestamp; the window must be at most 24 hours |
| `limit` | Page size, from 1 to 100; defaults to 100 |
| `cursor` | The previous response's `next_cursor`; keep the same time window |

The response contains `rolls` and `next_cursor` (`null` on the last page). Each roll contains `id`, `created_at`, nullable `character_id`, `owner_id`, `original_outcome`, `final_outcome`, `rerolled`, `hidden`, nullable `difficulty` and `margin`, `impaired`, and the `normal_dice` and `hunger_dice` results. Rerolled rolls also include `reroll_strategy`, `reroll_margin`, and the rerolled `reroll_dice`; these are `null` otherwise. IDs are strings. Outcomes are `critical`, `messy`, `success`, `fail`, `total_fail`, or `bestial`. `owner_id` identifies the character's owner, who may differ from the person making the roll.

Results reflect current stored outcomes, ordered by creation time and ID. This is not a snapshot or change feed: rerolls and exclusions can change results. Reimport the complete window to reconcile them. Do not count an original result and its final reroll as separate rolls.

Respect `429` and its `Retry-After` header. Limits are 30 requests per key and 60 per account per minute, with additional service-wide admission limits. Send one request at a time per account.
