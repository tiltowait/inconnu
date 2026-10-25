# /post

With the `/post` command, you can post a message "from" your character rather than your Discord username. Called Roleposting, this feature ties in to your **Inconnu** characters' current stats and offers a number of advanced features, such as tagging, bookmarking, and searching.

When you use `/post`, the bot presents a modal dialogue where you can enter your text. You may enter a post as long as **8000 characters** spread across two text fields; **Inconnu** will intelligently split them across multiple posts as necessary.

![/post uses Discord's modal dialogue.](../../assets/post_example.png "/post uses Discord's modal dialogue.")

> [!NOTE]
> **Tip:** Write your post in an external editor or in the main Discord textbox. This will let you reference other posts without losing your progress.

### Optional parameters

| Option | Description | Notes | Required |
|---|---|---|---|
| **character** | The character to post as |  | No |
| **mentions** | Users, roles, and channels to mention | Start with `@` or `#` | No |
| **blush** | Is Blush of Life active? | Only affects this post | No |
| **hunger** | The vampire's Hunger level | Only affects this post | No |
| **location** | Where the scene is taking place | Only affects this post | No |
| **merits** | Obvious/important merits | Only affects this post | No |
| **flaws** | Obvious/important flaws | Only affects this post | No |
| **temporary** | Temporary effects | Only affects this post | No |
| **display_header** | Whether to display the RP header above the post | Defaults to "true" | No |

> [!NOTE]
> **For options that "only affect this post",** you may set the value permanently by [updating the header](../../command-reference/characters/rp-headers.md#setting-the-header).

![An example using the "mentions" option.](../../assets/post_mentions.png "An example using the \"mentions\" option.")

### Bookmark title

If you set a _bookmark title_ in the modal dialogue, then you can use [`/bookmarks`](bookmarks.md) to quickly view it later.

### Tags

A single post may have multiple _tags_, separated by semicolons, for lookup with the [`/tags`](tags.md) command. Many users use tags for tracking awakening scenes, Discipline use, when specific traits have been rolled, scenes with specific characters, and more.

### Editing & deleting

You may edit or delete a post by right-clicking the message and navigating to `Apps -> Post: Edit` or `Apps -> Post: Delete`. On mobile, long-press the message, then tap on `Apps` to bring up the menu.

> [!TIP]
> **If your premium membership lapses, you still have access to your old posts!** You can edit/delete them and view bookmarks/tags without issue.
