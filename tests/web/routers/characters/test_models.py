"""Tests for character API models (Pydantic validation)."""

import pytest
from pydantic import ValidationError

from models.vchardocs import VCharSplat, VCharTrait
from web.routers.characters.models import CreationBody


def valid_creation_data(**overrides):
    """Generate valid CreationBody data with optional overrides."""
    base_data = {
        "name": "Test Character",
        "splat": VCharSplat.VAMPIRE,
        "health": 6,
        "willpower": 5,
        "humanity": 7,
        "blood_potency": 1,
        "convictions": ["Never harm innocents"],
        "biography": "A compelling backstory",
        "description": "A brief description",
        "traits": [
            VCharTrait(name="Strength", rating=3, type=VCharTrait.Type.ATTRIBUTE),
            VCharTrait(
                name="Athletics", rating=2, type=VCharTrait.Type.SKILL, raw_subtraits=["Running"]
            ),
        ],
    }
    base_data.update(overrides)
    return base_data


class TestNameValidation:
    """Tests for character name validation."""

    def test_valid_name(self):
        """Valid name passes validation."""
        data = valid_creation_data(name="John O'Brien")
        body = CreationBody(**data)
        assert body.name == "John O'Brien"

    def test_name_normalized_whitespace(self):
        """Multiple spaces normalized to single space."""
        data = valid_creation_data(name="John    Doe")
        body = CreationBody(**data)
        assert body.name == "John Doe"

    def test_name_too_long(self):
        """Name longer than 30 characters rejected."""
        data = valid_creation_data(name="A" * 31)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "Invalid name" in str(exc_info.value)

    def test_name_empty(self):
        """Empty name rejected."""
        data = valid_creation_data(name="")
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "Invalid name" in str(exc_info.value)

    def test_name_only_whitespace(self):
        """Name with only whitespace rejected."""
        data = valid_creation_data(name="   ")
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "Invalid name" in str(exc_info.value)

    def test_name_invalid_characters(self):
        """Name with invalid characters rejected."""
        data = valid_creation_data(name="Test@Character#")
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "Invalid name" in str(exc_info.value)


class TestNumericFieldValidation:
    """Tests for numeric field range validation."""

    def test_health_min_boundary(self):
        """Health at minimum (4) passes."""
        data = valid_creation_data(health=4)
        body = CreationBody(**data)
        assert body.health == 4

    def test_health_max_boundary(self):
        """Health at maximum (20) passes."""
        data = valid_creation_data(health=20)
        body = CreationBody(**data)
        assert body.health == 20

    def test_health_below_min(self):
        """Health below 4 rejected."""
        data = valid_creation_data(health=3)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "health" in str(exc_info.value).lower()

    def test_health_above_max(self):
        """Health above 20 rejected."""
        data = valid_creation_data(health=21)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "health" in str(exc_info.value).lower()

    def test_willpower_range(self):
        """Willpower range (2-10) enforced."""
        # Valid
        for val in [2, 5, 10]:
            data = valid_creation_data(willpower=val)
            body = CreationBody(**data)
            assert body.willpower == val

        # Invalid
        for val in [1, 11]:
            data = valid_creation_data(willpower=val)
            with pytest.raises(ValidationError):
                CreationBody(**data)

    def test_humanity_range(self):
        """Humanity range (0-10) enforced."""
        # Valid
        for val in [0, 5, 10]:
            data = valid_creation_data(humanity=val)
            body = CreationBody(**data)
            assert body.humanity == val

        # Invalid
        for val in [-1, 11]:
            data = valid_creation_data(humanity=val)
            with pytest.raises(ValidationError):
                CreationBody(**data)

    def test_blood_potency_vampire_range(self):
        """Blood potency for vampires (0-10) enforced."""
        # Valid
        for val in [0, 5, 10]:
            data = valid_creation_data(splat=VCharSplat.VAMPIRE, blood_potency=val)
            body = CreationBody(**data)
            assert body.blood_potency == val

        # Invalid
        for val in [-1, 11]:
            data = valid_creation_data(splat=VCharSplat.VAMPIRE, blood_potency=val)
            with pytest.raises(ValidationError):
                CreationBody(**data)


class TestBloodPotencySplatValidation:
    """Tests for blood potency validation based on splat."""

    def test_mortal_requires_zero_potency(self):
        """Mortals must have blood potency 0."""
        # Valid
        data = valid_creation_data(splat=VCharSplat.MORTAL, blood_potency=0)
        body = CreationBody(**data)
        assert body.blood_potency == 0

        # Invalid
        data = valid_creation_data(splat=VCharSplat.MORTAL, blood_potency=1)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "mortal" in str(exc_info.value).lower()

    def test_ghoul_requires_zero_potency(self):
        """Ghouls must have blood potency 0."""
        # Valid
        data = valid_creation_data(splat=VCharSplat.GHOUL, blood_potency=0)
        body = CreationBody(**data)
        assert body.blood_potency == 0

        # Invalid
        data = valid_creation_data(splat=VCharSplat.GHOUL, blood_potency=1)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "ghoul" in str(exc_info.value).lower()

    def test_thin_blood_potency_range(self):
        """Thin-bloods must have blood potency 0-2."""
        # Valid
        for val in [0, 1, 2]:
            data = valid_creation_data(splat=VCharSplat.THIN_BLOOD, blood_potency=val)
            body = CreationBody(**data)
            assert body.blood_potency == val

        # Invalid
        data = valid_creation_data(splat=VCharSplat.THIN_BLOOD, blood_potency=3)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "thin-blood" in str(exc_info.value).lower()


class TestConvictionsValidation:
    """Tests for convictions validation."""

    def test_valid_convictions(self):
        """Valid convictions list passes."""
        data = valid_creation_data(convictions=["First", "Second", "Third"])
        body = CreationBody(**data)
        assert len(body.convictions) == 3

    def test_empty_convictions(self):
        """Empty convictions list allowed."""
        data = valid_creation_data(convictions=[])
        body = CreationBody(**data)
        assert body.convictions == []

    def test_too_many_convictions(self):
        """More than 3 convictions rejected."""
        data = valid_creation_data(convictions=["First", "Second", "Third", "Fourth"])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "convictions" in str(exc_info.value).lower()

    def test_conviction_too_long(self):
        """Conviction longer than 200 characters rejected."""
        data = valid_creation_data(convictions=["A" * 201])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "200 characters" in str(exc_info.value)

    def test_conviction_max_length(self):
        """Conviction at 200 characters passes."""
        data = valid_creation_data(convictions=["A" * 200])
        body = CreationBody(**data)
        assert len(body.convictions[0]) == 200


class TestTextFieldValidation:
    """Tests for biography and description validation."""

    def test_biography_max_length(self):
        """Biography at 1024 characters passes."""
        data = valid_creation_data(biography="A" * 1024)
        body = CreationBody(**data)
        assert len(body.biography) == 1024

    def test_biography_too_long(self):
        """Biography longer than 1024 characters rejected."""
        data = valid_creation_data(biography="A" * 1025)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "biography" in str(exc_info.value).lower()

    def test_description_max_length(self):
        """Description at 24 characters passes."""
        data = valid_creation_data(description="A" * 1024)
        body = CreationBody(**data)
        assert len(body.description) == 1024

    def test_description_too_long(self):
        """Description longer than 24 characters rejected."""
        data = valid_creation_data(description="A" * 1025)
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "description" in str(exc_info.value).lower()


class TestTraitNameValidation:
    """Tests for trait name validation."""

    def test_valid_trait_name(self):
        """Valid trait names pass."""
        trait = VCharTrait(name="Strength", rating=3, type=VCharTrait.Type.ATTRIBUTE)
        data = valid_creation_data(traits=[trait])
        body = CreationBody(**data)
        assert len(body.traits) == 1

    def test_trait_name_with_underscore(self):
        """Trait names with underscores allowed."""
        trait = VCharTrait(name="Animal_Ken", rating=2, type=VCharTrait.Type.SKILL)
        data = valid_creation_data(traits=[trait])
        body = CreationBody(**data)
        assert body.traits[0].name == "Animal_Ken"

    def test_trait_name_too_long(self):
        """Trait name longer than 20 characters rejected."""
        trait = VCharTrait(name="A" * 21, rating=3, type=VCharTrait.Type.CUSTOM)
        data = valid_creation_data(traits=[trait])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "too long" in str(exc_info.value).lower()

    def test_trait_name_invalid_characters(self):
        """Trait names with invalid characters rejected."""
        data = valid_creation_data()
        data["traits"].append(
            {
                "name": "Strength-Plus",
                "rating": 3,
                "type": VCharTrait.Type.CUSTOM,
                "subtraits": [],
            }
        )
        with pytest.raises((ValidationError, SyntaxError)) as exc_info:
            CreationBody(**data)
        assert "letters and underscores" in str(exc_info.value).lower()

    def test_trait_name_with_apostrophe_rejected(self):
        """Trait names with apostrophes rejected."""
        data = valid_creation_data()
        data["traits"].append(
            {
                "name": "O'Strength",
                "rating": 3,
                "type": VCharTrait.Type.CUSTOM,
                "subtraits": [],
            }
        )
        with pytest.raises((ValidationError, SyntaxError)) as exc_info:
            CreationBody(**data)
        assert "letters and underscores" in str(exc_info.value).lower()

    def test_reserved_trait_rejected(self):
        """Reserved trait names rejected."""
        data = valid_creation_data()
        data["traits"].append(
            {
                "name": "Willpower",  # Use a definitely reserved trait
                "rating": 6,
                "type": VCharTrait.Type.CUSTOM,
                "subtraits": [],
            }
        )
        with pytest.raises((ValidationError, ValueError)) as exc_info:
            CreationBody(**data)
        assert "reserved" in str(exc_info.value).lower() or "adjust" in str(exc_info.value).lower()

    def test_duplicate_trait_names_rejected(self):
        """Duplicate trait names rejected."""
        data = valid_creation_data()
        data["traits"].append(
            {
                "name": "Strength",  # Duplicate of existing trait
                "rating": 4,
                "type": VCharTrait.Type.ATTRIBUTE,
                "subtraits": [],
            }
        )
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_duplicate_trait_names_case_insensitive(self):
        """Duplicate trait names rejected (case-insensitive)."""
        data = valid_creation_data()
        data["traits"].append(
            {
                "name": "STRENGTH",  # Duplicate with different case
                "rating": 4,
                "type": VCharTrait.Type.ATTRIBUTE,
                "subtraits": [],
            }
        )
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "duplicate" in str(exc_info.value).lower()


class TestSpecialtyValidation:
    """Tests for specialty (subtrait) validation."""

    def test_valid_specialty_on_skill(self):
        """Specialties on skills allowed."""
        trait = VCharTrait(
            name="Athletics",
            rating=2,
            type=VCharTrait.Type.SKILL,
            raw_subtraits=["Running", "Climbing"],
        )
        data = valid_creation_data(traits=[trait])
        body = CreationBody(**data)
        assert len(body.traits[0].raw_subtraits) == 2

    def test_valid_specialty_on_custom_trait(self):
        """Specialties on custom traits allowed."""
        trait = VCharTrait(
            name="CustomTrait",
            rating=3,
            type=VCharTrait.Type.CUSTOM,
            raw_subtraits=["SpecialtyOne"],
        )
        data = valid_creation_data(traits=[trait])
        body = CreationBody(**data)
        assert len(body.traits[0].raw_subtraits) == 1

    def test_specialty_on_attribute_rejected(self):
        """Specialties on attributes rejected."""
        trait = VCharTrait(
            name="Strength",
            rating=3,
            type=VCharTrait.Type.ATTRIBUTE,
            raw_subtraits=["Lifting"],
        )
        data = valid_creation_data(traits=[trait])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "cannot have subtraits" in str(exc_info.value).lower()

    def test_powers_on_discipline_allowed(self):
        """Subtraits (powers) on disciplines allowed."""
        trait = VCharTrait(
            name="Auspex",
            rating=2,
            type=VCharTrait.Type.DISCIPLINE,
            raw_subtraits=["Heightened_Senses"],
        )
        data = valid_creation_data(traits=[trait])
        body = CreationBody(**data)
        assert len(body.traits[0].raw_subtraits) == 1

    def test_specialty_name_too_long(self):
        """Specialty name longer than 20 characters rejected."""
        trait = VCharTrait(
            name="Athletics",
            rating=2,
            type=VCharTrait.Type.SKILL,
            raw_subtraits=["A" * 21],
        )
        data = valid_creation_data(traits=[trait])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "too long" in str(exc_info.value).lower()

    def test_specialty_name_invalid_characters(self):
        """Specialty names with invalid characters rejected."""
        data = valid_creation_data()
        # Replace Athletics trait with one having invalid specialty
        data["traits"][1] = VCharTrait(
            name="Athletics",
            rating=2,
            type=VCharTrait.Type.SKILL,
            raw_subtraits=["Running-Fast"],
        )
        with pytest.raises((ValidationError, SyntaxError)) as exc_info:
            CreationBody(**data)
        assert "letters and underscores" in str(exc_info.value).lower()

    def test_duplicate_specialty_names_rejected(self):
        """Duplicate specialty names on same trait rejected."""
        trait = VCharTrait(
            name="Athletics",
            rating=2,
            type=VCharTrait.Type.SKILL,
            raw_subtraits=["Running", "Running"],
        )
        data = valid_creation_data(traits=[trait])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "duplicate" in str(exc_info.value).lower()

    def test_duplicate_specialty_names_case_insensitive(self):
        """Duplicate specialty names rejected (case-insensitive)."""
        trait = VCharTrait(
            name="Athletics",
            rating=2,
            type=VCharTrait.Type.SKILL,
            raw_subtraits=["Running", "RUNNING"],
        )
        data = valid_creation_data(traits=[trait])
        with pytest.raises(ValidationError) as exc_info:
            CreationBody(**data)
        assert "duplicate" in str(exc_info.value).lower()


class TestCompleteValidation:
    """Tests for complete CreationBody validation."""

    def test_minimal_valid_character(self):
        """Minimal valid character data passes."""
        data = {
            "name": "Simple",
            "splat": VCharSplat.MORTAL,
            "health": 5,
            "willpower": 3,
            "humanity": 7,
            "blood_potency": 0,
            "convictions": [],
            "biography": "",
            "description": "",
            "traits": [],
        }
        body = CreationBody(**data)
        assert body.name == "Simple"

    def test_complete_valid_vampire(self):
        """Complete valid vampire passes all validations."""
        data = valid_creation_data()
        body = CreationBody(**data)
        assert body.splat == VCharSplat.VAMPIRE
        assert body.health == 6
        assert len(body.traits) == 2
