"""vr/rollparser.py - Define a class for parsing user roll input."""

import ast
import operator as op
import re

import inconnu
from inconnu.models.vchardocs import VCharTrait
from logger import Logger


class RollParser:
    """Parse user roll input."""

    def __init__(self, character, raw_syntax, expand_only=False, power_bonus=True):
        self.character = character
        self._parameters = {}
        self.expand_only = expand_only
        self.power_bonus = power_bonus

        # Convert the syntax into tokens, if necessary
        if isinstance(raw_syntax, str):
            if self.has_invalid_characters(raw_syntax):
                raise SyntaxError("Invalid syntax.")

            # Fix spacing
            if VCharTrait.DELIMITER == ".":
                # Period matches any character in regex, so we have to escape it
                pat = r"\s*\.\s*"
            else:
                pat = r"\s*" + VCharTrait.DELIMITER + r"\s*"
            syntax = re.sub(pat, VCharTrait.DELIMITER, raw_syntax)
            syntax = re.sub(r"\s*([+-])\s*", r" \g<1> ", syntax)

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
            # Traits weren't used
            return None

        if string[0] == "+":
            # Lop off leading plus sign and the following space
            string = string[2:]
        if string[0] == "-":
            # Remove space between negative sign and trait/number
            string = string.replace(" ", "", 1)

        return string

    @property
    def hunger(self):
        """The int value of the roll's hunger."""
        if self.character is None or self.character.is_vampire:
            return self._parameters["eval_hunger"]
        return 0

    @property
    def difficulty(self):
        """The int value of the roll's difficulty."""
        return self._parameters["eval_difficulty"]

    def _create_stacks(self):
        """Create both the fully qualified stacks and the interpolated stacks."""
        using_discipline = False

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

            if token == "current_hunger":
                token = "hunger" if self.character.is_vampire else "0"

            if token.isdigit():
                # Digits require no interpolation, so just add it to the stacks
                current_qualified.append(token)
                current_interpolated.append(token)
            else:
                # We have a character trait, which needs to be qualified and
                # interpolated before adding it to the stacks
                trait = self.character.find_trait(token)
                if self.expand_only:
                    current_qualified.append(trait.key)
                else:
                    current_qualified.append(trait.name)

                current_interpolated.append(str(trait.rating))

                if trait.discipline:
                    Logger.debug("ROLLPARSER: Discipline detected")
                    using_discipline = True

            expecting_operand = False

        qualified_stacks.append(current_qualified)
        interpolated_stacks.append(current_interpolated)

        # Determine which stack is which. Order goes pool, hunger, difficulty.

        if not qualified_stacks:
            # This shouldn't be possible to reach, but just in case ...
            raise SyntaxError("You have to supply roll syntax!")

        self._parameters["q_pool_stack"] = qualified_stacks.pop(0)
        self._parameters["i_pool_stack"] = interpolated_stacks.pop(0)

        if self.power_bonus and using_discipline and self.character.power_bonus > 0:
            Logger.debug("ROLLPARSER: Adding power bonus")
            self._parameters["q_pool_stack"].extend(["+", "PowerBonus"])
            self._parameters["i_pool_stack"].extend(["+", str(self.character.power_bonus)])

        if "Hunger" in self.pool_stack:
            errmsg = "Hunger can't be a part of your pool.\n*Hint: Write `hunger`, not `+ hunger`.*"
            raise inconnu.errors.HungerInPool(errmsg)

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
        if self.character is None or self.character.is_vampire:
            self._parameters["q_hunger_stack"] = qualified_stacks.pop(0)
            self._parameters["i_hunger_stack"] = interpolated_stacks.pop(0)
        else:
            # This is a mortal character. Mortals don't have Hunger, so we'll
            # ignore it and set it to 0; however, many players are used to
            # inputting Hunger on all rolls and may have put a 0 for Hunger.
            # In that case, we will remove the 0 at the top of the stack.
            self._parameters["q_hunger_stack"] = ["0"]
            self._parameters["i_hunger_stack"] = ["0"]

            if interpolated_stacks[0] == ["0"]:
                del qualified_stacks[0]
                del interpolated_stacks[0]

        if not qualified_stacks:
            # Difficulty was not provided
            self._parameters["q_difficulty_stack"] = ["0"]
            self._parameters["i_difficulty_stack"] = ["0"]
            return

        # They gave us all three (pool, hunger, and difficulty)
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
            extra = f"**Unexpected extra parameter(s):** `{extra}`"

            err = "Too many roll parameters given. Interpretation based on input:"
            raise inconnu.errors.TooManyParameters(
                3 + len(qualified_stacks), f"{err}\n\n{interpretation}\n\n{extra}"
            )

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
        return re.search(r"[^\w\+\-\s" + VCharTrait.DELIMITER + "]", syntax) is not None

    @classmethod
    def possible_spec_use(cls, syntax: str) -> bool:
        """Check if the user might be trying to use a spec."""
        return re.search(r"\(.*\)", syntax) is not None


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
