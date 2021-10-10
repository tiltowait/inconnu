# Miscellaneous

The following commands have no direct gameplay effect and are provided for convenience, fun, or both.

## Coin Flip

```
/coinflip
```

Need a quick coin toss? This will generate heads or tails.

## Probability Calculation

You can calculate roll outcome probabilities using the `/probability` command.

```
/probability roll:<roll> character:[character]
```

The `roll` parameter can be any valid roll, such as `7 3 2` (pool 7, hunger 3, difficulty 2) or even a trait-based roll like `Resolve + Academics 2 4`.

?> `character` is only necessary if you're invoking character traits.

## Random Numbers

A random number between 1 and `ceiling` (default `100`) may be rolled with the `/percentile` command.

## Statistics

Want to see how many rolls you've made? How many successes, crits, bestial failures, and the like? How many times you've used a Willpower re-roll? The `/statistics` command will show all of this information for each of your characters on the server.
