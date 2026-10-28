"""vr/rollparser.py - Define a class for parsing user roll input."""

import ast
import operator as op
import re
from itertools import chain
from typing import cast

from loguru import logger

import errors
from models.vchardocs import VCharTrait

DELIMITER = re.escape(VCharTrait.DELIMITER)


class RollParser:
    """Parse user roll input."""

    def __init__(self, character, raw_syntax, expand_only=False, power_bonus=True):
        self.character = character
        self._parameters = {}
        self.expand_only = expand_only
        self.power_bonus = power_bonus

        # Convert the syntax into tokens, if necessary
        if isinstance(raw_syntax, str):
            self.tokens = self.tokenize(raw_syntax)
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
        # A "fully qualified" stack has the canonical names of the character's
        # traits. For instance, `wi` will be interpreted to Wits, and `aw` will
        # become Awareness.
        #
        # An "interpolated" stack replaces the trait names with the ratings.
        #
        # Order goes pool, hunger, difficulty. Only the pool may contain any
        # trait; hunger may only contain Hunger, and difficulty only numbers.

        stacks = self._split_stacks(self.tokens)
        q_pool, i_pool, using_discipline = self._qualify(stacks.pop(0))
        self._parameters["q_pool_stack"] = q_pool
        self._parameters["i_pool_stack"] = i_pool

        if self.power_bonus and using_discipline and self.character.power_bonus > 0:
            logger.debug("ROLLPARSER: Adding power bonus")
            self._parameters["q_pool_stack"].extend(["+", "PowerBonus"])
            self._parameters["i_pool_stack"].extend(["+", str(self.character.power_bonus)])

        if "Hunger" in self.pool_stack:
            errmsg = "Hunger can't be a part of your pool.\n*Hint: Write `hunger`, not `+ hunger`.*"
            raise errors.HungerInPool(errmsg)

        # Only the pool is required, so we need to provide defaults if the other
        # stacks aren't given
        for stack in (
            "q_hunger_stack",
            "i_hunger_stack",
            "q_difficulty_stack",
            "i_difficulty_stack",
        ):
            self._parameters[stack] = ["0"]

        if not stacks:
            # They only gave us a pool
            return

        # The user provided pool and hunger
        if self.character is None or self.character.is_vampire:
            q_hunger, i_hunger, _ = self._qualify(stacks.pop(0))
            for token in q_hunger:
                if not (token in "+-" or token.isdigit() or token == "Hunger"):
                    raise errors.HungerIsntHunger(
                        f"Hunger must be a number or `hunger`, not **{token}**."
                    )

            self._parameters["q_hunger_stack"] = q_hunger
            self._parameters["i_hunger_stack"] = i_hunger
        else:
            # This is a mortal character. Mortals don't have Hunger, so asking
            # for it is an error.
            for token in chain.from_iterable(stacks):
                if token and "hunger".startswith(token.lower()):
                    raise errors.TraitNotFound(self.character, token)

            # However, many players are used to inputting Hunger on all rolls
            # and may have put a 0 for Hunger. In that case, we will remove the
            # 0 at the top of the stack.
            if stacks[0] in (["0"], ["current_hunger"]):
                del stacks[0]

        if not stacks:
            # Difficulty was not provided
            return

        # They gave us all three (pool, hunger, and difficulty)
        difficulty = stacks.pop(0)

        if stacks:
            # They gave us too many stacks! Show our interpretation as well as the extra
            # First, get human-readable representations of the stacks
            _pool = self.pool_str or " ".join(self._parameters["q_pool_stack"])
            if (_hunger := " ".join(self._parameters["q_hunger_stack"])) == "Hunger":
                _hunger = "Current Hunger"
            _difficulty = " ".join(difficulty)

            interpretation = (
                f"***Pool:*** `{_pool}`\n"
                f"***Hunger:*** `{_hunger}`\n"
                f"***Difficulty:*** `{_difficulty}`"
            )
            extra = " ".join(chain.from_iterable(stacks))
            extra = f"**Unexpected extra parameter(s):** `{extra}`"

            err = "Too many roll parameters given. Interpretation based on input:"
            raise errors.TooManyParameters(3 + len(stacks), f"{err}\n\n{interpretation}\n\n{extra}")

        if not all(token in "+-" or token.isdigit() for token in difficulty):
            raise errors.InvalidDifficulty(
                f"Difficulty must be a number, not `{' '.join(difficulty)}`."
            )

        self._parameters["q_difficulty_stack"] = difficulty
        self._parameters["i_difficulty_stack"] = difficulty

    @staticmethod
    def _split_stacks(tokens) -> list[list[str]]:
        """Split the tokens into stacks. When we encounter two operands in a
        row, the user has switched parameter types (e.g. pool -> hunger ->
        difficulty), so we wrap up the current stack and start a new one."""
        stacks = [[]]
        expecting_operand = True

        for token in tokens:
            if token in "+-":
                # We don't prevent anyone from using multiple operators in a
                # row, so they could technically write 3 + - + - 2, and it will
                # work despite being somewhat nonsensical.
                expecting_operand = True
            elif not expecting_operand:
                stacks.append([])
            else:
                expecting_operand = False
            stacks[-1].append(token)

        return stacks

    def _qualify(self, stack: list[str]) -> tuple[list[str], list[str], bool]:
        """Qualify and interpolate a stack. Returns the qualified stack, the
        interpolated stack, and whether a Discipline was used."""
        qualified = []
        interpolated = []
        using_discipline = False

        for token in stack:
            if token == "current_hunger":
                token = "hunger" if self.character.is_vampire else "0"

            if token in "+-" or token.isdigit():
                # Operators and digits require no interpolation
                qualified.append(token)
                interpolated.append(token)
            else:
                # We have a character trait, which needs to be qualified and
                # interpolated before adding it to the stacks
                trait = self.character.find_trait(token)
                qualified.append(trait.key if self.expand_only else trait.name)
                interpolated.append(str(trait.rating))

                if trait.discipline:
                    logger.debug("ROLLPARSER: Discipline detected")
                    using_discipline = True

        return qualified, interpolated, using_discipline

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
    def tokenize(cls, syntax: str) -> list[str]:
        """Split roll syntax into operators and operands. Raises SyntaxError if
        the syntax has invalid characters."""
        if cls.has_invalid_characters(syntax):
            raise SyntaxError("Invalid syntax.")

        # Whitespace around the delimiter is ignored, so "brawl . kindred" is
        # one operand
        syntax = re.sub(rf"\s*{DELIMITER}\s*", VCharTrait.DELIMITER, syntax)
        return re.findall(r"[+-]|[^\s+-]+", syntax)

    @classmethod
    def has_invalid_characters(cls, syntax) -> bool:
        """Check whether the roll has invalid characters."""
        return re.search(rf"[^\w+\-\s{DELIMITER}]", syntax) is not None

    @classmethod
    def possible_spec_use(cls, syntax: str) -> bool:
        """Check if the user might be trying to use a spec."""
        return re.search(r"\(.*\)", syntax) is not None


# Math Helpers

# We could use pandas for this, but this is built-in and considerably faster,
# which makes a difference when calculating probabilities.

OPERATORS = {ast.Add: op.add, ast.Sub: op.sub, ast.UAdd: op.pos, ast.USub: op.neg}


def eval_expr(expr: str) -> int:
    """Evaluate a mathematical string expression. Safer than using eval."""
    return eval_(ast.parse(expr, mode="eval").body)


def eval_(node: ast.expr) -> int:
    """Recursively evaluate a mathematical expression. Only handles +/-."""
    if isinstance(node, ast.Constant):
        return cast(int, node.value)

    if isinstance(node, ast.BinOp):
        return OPERATORS[type(node.op)](eval_(node.left), eval_(node.right))

    if isinstance(node, ast.UnaryOp):
        return OPERATORS[type(node.op)](eval_(node.operand))

    raise TypeError(node)
