# /search

The `/post` command uses webhooks, which Discord's standard search feature has trouble with. In particular, you can't use the `from:` filter with webhook messages. **Inconnu's** `/search` feature bridges the gap and offers a number of options for finding your (or another player's) posts.

> [!TIP]
> This command **does not** require premium! Any user may use `/search` to find a premium user's posts. This holds true even if your own membership lapses.

When you `/search`, a window will pop up showing matching posts (presentation depends on whether you enable `summary` mode, below). Clicking the character name or the summary snippet will take you to that post.

![An example of the "summary" mode.](../../assets/search_demo.png "An example of the \"summary\" mode.")

| Option | Description | Required | Notes |
|---|---|---|---|
| **user** | The user who made the post | Yes |  |
| **content** | Text that appears in the post | No | If this option is used, results will be sorted by relavency rather than date |
| **character** | The name of the character in the post | No | This is the name when the post was made |
| **mentioning** | A user the author pinged with the post | No | The author must have used the `mentioning` parameter |
| **hidden** | If true, only you may see the search results | No | Defaults to "true" |
| **summary** | If true, display a list of posts with a short snippet from each | No | Defaults to "false" |

> [!WARNING]
> **If a post was deleted,** it will not show in `/search` results.
