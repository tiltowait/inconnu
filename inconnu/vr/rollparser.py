"""vr/rollparser.py - Define a class for parsing user roll input."""

import ast
import operator as op
import re


class RollParser:
    """Parse user roll input."""

    def __init__(self, character, raw_syntax):
        self.character = character
        self._parameters = {}

        # Convert the syntax into tokens, if necessary
        if isinstance(raw_syntax, str):
            if not re.match(r"^[\w\s\+-]+$", raw_syntax):
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
    def pool_stack(self):
        """The fully qualified pool stack."""
        return self._parameters["q_pool_stack"]

    @property
    def pool_str(self):
        """The pool's attribute+skill string."""
        string = " ".join(self.pool_stack)

        if not re.search(r"[A-Za-z_]", string):
            return None

        if string[0] == "+":
            string = string[2:]  # Just lop off the leading plus sign
        if string[0] == "-":
            string = string.replace(" ", "", 1)  # First item is negative, not subtracting

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

        # A "fully qualified" stack has the canonical names of the character's
        # traits. For instance, `wi` will be interpreted to Wits, and `aw` will
        # become Awareness.
        #
        # An "interpolated" stack replaces the trait names with the ratings.

        qualified_stacks = []
        interpolated_stacks = []

        # When we encounter two operands in a row, the user has switched
        # parameter types (e.g. pool -> hunger -> difficulty). When this
        # happens, we wrap up the current stack and start a new one.

        current_qualified = []
        current_interpolated = []
        expecting_operand = True

        for token in self.tokens:
            if token in ["+", "-"]:
                # We don't prevent anyone from using multiple operators in a
                # row, so they could technically write 3 + - + - 2, and it will
                # work despite being somewhat nonsensical.
                current_qualified.append(token)
                current_interpolated.append(token)
                expecting_operand = True
                continue

            if not expecting_operand:
                # We expected +/-. Since we didn't get one, we're looking at the
                # next parameter type. Start up and begin processing the next
                # stack.
                qualified_stacks.append(current_qualified)
                interpolated_stacks.append(current_interpolated)

                current_qualified = []
                current_interpolated = []

            if token.isdigit():
                # Digits require no interpolation, so just add it to the stacks
                current_qualified.append(token)
                current_interpolated.append(token)
            else:
                # We have a character trait, which needs to be qualified and
                # interpolated before adding it to the stacks
                trait = self.character.find_trait(token)
                current_qualified.append(trait.name)
                current_interpolated.append(str(trait.rating))

            expecting_operand = False

        qualified_stacks.append(current_qualified)
        interpolated_stacks.append(current_interpolated)

        # Determine which stack is which. Order goes pool, hunger, difficulty.

        if not qualified_stacks:
            # This shouldn't be possible to reach, but just in case ...
            raise SyntaxError("You have to supply roll syntax!")

        self._parameters["q_pool_stack"] = qualified_stacks.pop(0)
        self._parameters["i_pool_stack"] = interpolated_stacks.pop(0)

        if "Hunger" in self.pool_stack:
            errmsg = "Hunger can't be a part of your pool.\n*Hint: Write `hunger`, not `+ hunger`.*"
            raise SyntaxError(errmsg)

        # Only the pool is required, so we need to provide defaults if the other
        # stacks aren't given

        if not qualified_stacks:
            # They only gave us a pool
            self._parameters["q_hunger_stack"] = ["0"]
            self._parameters["i_hunger_stack"] = ["0"]
            self._parameters["q_difficulty_stack"] = ["0"]
            self._parameters["i_difficulty_stack"] = ["0"]
            return

        # The user provided pool and hunger
        self._parameters["q_hunger_stack"] = qualified_stacks.pop(0)
        self._parameters["i_hunger_stack"] = interpolated_stacks.pop(0)

        if not qualified_stacks:
            # Difficulty was not provided
            self._parameters["q_difficulty_stack"] = ["0"]
            self._parameters["i_difficulty_stack"] = ["0"]
            return

        # They gave us all three
        self._parameters["q_difficulty_stack"] = qualified_stacks.pop(0)
        self._parameters["i_difficulty_stack"] = interpolated_stacks.pop(0)

        if qualified_stacks:
            # They gave us too many stacks! Show our interpretation as well as the extra
            # First, get human-readable representations of the stacks
            _pool = self.pool_str or " ".join(self._parameters["q_pool_stack"])
            if (_hunger := " ".join(self._parameters["q_hunger_stack"])) == "Hunger":
                _hunger = "Current Hunger "
            _difficulty = " ".join(self._parameters["q_difficulty_stack"])

            interpretation = (
                f"***Pool:*** `{_pool}`\n"
                f"***Hunger:*** `{_hunger}`\n"
                f"***Difficulty:*** `{_difficulty}`"
            )
            extra = " ".join(sum(qualified_stacks, []))
            extra = f"**Unexpected parameter(s):** `{extra}`"

            err = "Too many roll parameters given. Interpretation based on input:"
            raise SyntaxError(f"{err}\n\n{interpretation}\n\n{extra}")

    def _evaluate_stacks(self):
        """Convert the pool, hunger, and difficulty into values."""
        pool = " ".join(self._parameters["i_pool_stack"])
        hunger = " ".join(self._parameters["i_hunger_stack"])
        difficulty = " ".join(self._parameters["i_difficulty_stack"])

        # We can just use eval for this rather than looping through
        try:
            self._parameters["eval_pool"] = eval_expr(pool)
            self._parameters["eval_hunger"] = eval_expr(hunger)
            self._parameters["eval_difficulty"] = eval_expr(difficulty)
        except SyntaxError as err:
            raise SyntaxError("Invalid syntax!") from err

    @classmethod
    def has_invalid_characters(cls, syntax) -> bool:
        """Check whether the roll has invalid characters."""
        return re.search(r"[^\w\+\-\s]", syntax) is not None


# Math Helpers

# We could use pandas for this, but this is built-in and considerably faster,
# which makes a difference when calculating probabilities.

OPERATORS = {ast.Add: op.add, ast.Sub: op.sub, ast.UAdd: op.pos, ast.USub: op.neg}


def eval_expr(expr):
    """Evaluate a mathematical string expression. Safer than using eval."""
    return eval_(ast.parse(expr, mode="eval").body)


def eval_(node):
    """Recursively evaluate a mathematical expression. Only handles +/-."""
    if isinstance(node, ast.Num):
        return node.n

    if isinstance(node, ast.BinOp):
        return OPERATORS[type(node.op)](eval_(node.left), eval_(node.right))

    if isinstance(node, ast.UnaryOp):
        return OPERATORS[type(node.op)](eval_(node.operand))

    raise TypeError(node)
