"""vr/rollparser.py - Define a class for parsing user roll input."""

import re


class RollParser:
    """Parse user roll input."""

    def __init__(self, character, raw_syntax):
        self.character = character
        self._parameters = {}

        # Convert the syntax into tokens, if necessary
        if isinstance(raw_syntax, str):
            if not re.match(r"^[\w\d\s\+-]+$", raw_syntax):
                raise SyntaxError("Invalid syntax.")

            syntax = re.sub(r"\s*([+-])\s*", r" \g<1> ", raw_syntax)

            self.tokens = syntax.split()
        else:
            self.tokens = map(str, raw_syntax)

        self._create_stacks()
        self._evaluate_stacks()


    @property
    def pool(self):
        """The int value of the roll's pool."""
        return self._parameters["eval_pool"]


    @property
    def pool_str(self):
        """The pool's attribute+skill string."""
        string = " ".join(self._parameters["q_pool_stack"])

        if not re.search(r"[A-Za-z_]", string):
            return None

        if string[0] == "+":
            string = string[2:] # Just lop off the leading plus sign
        if string[0] == "-":
            string = string.replace(" ", "", 1) # First item is negative, not subtracting

        return string


    @property
    def hunger(self):
        """The int value of the roll's hunger."""
        return self._parameters["eval_hunger"]


    @property
    def difficulty(self):
        """The int value of the roll's difficulty."""
        return self._parameters["eval_difficulty"]


    def _create_stacks(self):
        """Create both the fully qualified stacks and the interpolated stacks."""
        qualified_stacks = []
        interpolated_stacks = []

        current_qualified = []
        current_interpolated = []
        expecting_operand = True

        for token in self.tokens:
            if token in ["+", "-"]:
                current_qualified.append(token)
                current_interpolated.append(token)
                expecting_operand = True
                continue

            if not expecting_operand:
                # We expected +/-. Since we didn't get one, we're looking at the next parameter type
                qualified_stacks.append(current_qualified)
                current_qualified = []
                interpolated_stacks.append(current_interpolated)
                current_interpolated = []

            if token.isdigit():
                # Digits require no interpolation
                current_qualified.append(token)
                current_interpolated.append(token)
            else:
                # We have a character trait
                trait = self.character.find_trait(token)
                current_qualified.append(trait.name)
                current_interpolated.append(str(trait.rating))

            expecting_operand = False

        qualified_stacks.append(current_qualified)
        interpolated_stacks.append(current_interpolated)

        # Determine which stack is which
        if not qualified_stacks:
            raise SyntaxError("You have to supply roll syntax!")

        self._parameters["q_pool_stack"] = qualified_stacks.pop(0)
        self._parameters["i_pool_stack"] = interpolated_stacks.pop(0)

        if "Hunger" in self._parameters["q_pool_stack"]:
            errmsg = "Hunger can't be a part of your pool.\n*Hint: Write `hunger`, not `+ hunger`.*"
            raise SyntaxError(errmsg)

        if not qualified_stacks:
            # They only gave us a pool
            self._parameters["q_hunger_stack"] = ["0"]
            self._parameters["i_hunger_stack"] = ["0"]
            self._parameters["q_difficulty_stack"] = ["0"]
            self._parameters["i_difficulty_stack"] = ["0"]
            return

        self._parameters["q_hunger_stack"] = qualified_stacks.pop(0)
        self._parameters["i_hunger_stack"] = interpolated_stacks.pop(0)

        if not qualified_stacks:
            # They gave us a pool and Hunger
            self._parameters["q_difficulty_stack"] = ["0"]
            self._parameters["i_difficulty_stack"] = ["0"]
            return

        # They gave us all three
        self._parameters["q_difficulty_stack"] = qualified_stacks.pop(0)
        self._parameters["i_difficulty_stack"] = interpolated_stacks.pop(0)

        if qualified_stacks:
            # They gave us too much!
            extra = sum(qualified_stacks, [])
            extra = " ".join(extra)
            err = f"Expected pool, hunger, difficulty. Not sure what to do with `{extra}`!"
            raise SyntaxError(err)


    def _evaluate_stacks(self):
        """Convert the pool, hunger, and difficulty into values."""
        pool = " ".join(self._parameters["i_pool_stack"])
        hunger = " ".join(self._parameters["i_hunger_stack"])
        difficulty = " ".join(self._parameters["i_difficulty_stack"])

        # We can just use eval for this rather than looping through
        try:
            self._parameters["eval_pool"] = eval(pool)
            self._parameters["eval_hunger"] = eval(hunger)
            self._parameters["eval_difficulty"] = eval(difficulty)
        except SyntaxError as err:
            raise SyntaxError("Invalid syntax!") from err
