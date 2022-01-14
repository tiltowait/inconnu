# Server Settings

**Inconnu's** has a few customizable behaviors. These are adjustable using the `/set` command and *can only be managed by server administrators.* Anyone can use the `/settings` command to see the server's current configuration.

## Parameters:

### `accessibility`

?> **Default:** `No`

This enables or disables [accessibility mode](accessibility.md) for the entire server. Users may not override this parameter if set to `Yes`.

---

### `oblivion_stains`

?> **Default:** `10s and 1s`

When making a Rouse check, you may have noticed a message occasionally coming up informing you to apply a stain if it was an Oblivion roll. This is due to the rule introduced in *Chicago by Night* and *Cults of the Blood Gods* that a Rouse check for an Oblivion power, ritual, or ceremony gives a stain to the character on a 1 or a 10.

With the `oblivion_stains` parameter, you may customize this behavior to only show the message on 10s, 1s, or never.

!> **This parameter has an effect on macros.** Macros created with the `staining` parameter set to `Yes` will automatically apply a stain should the Rouse check result in the value chosen here.
