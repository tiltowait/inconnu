"""Test VChar profile and image properties."""

import pytest

from constants import Damage
from models import VChar


@pytest.fixture
def vampire() -> VChar:
    """Create a vampire character for testing."""
    char = VChar(
        guild=1,
        user=1,
        name="Test Vampire",
        splat="vampire",
        humanity=7,
        health=6 * Damage.NONE,
        willpower=5 * Damage.NONE,
        potency=2,
    )
    char.pre_insert()
    return char


# PROFILE IMAGE TESTS


def test_profile_image_url_no_images(vampire):
    """Test profile_image_url returns None when no images exist."""
    assert vampire.profile.images == []
    assert vampire.profile_image_url is None


def test_profile_image_url_single_image(vampire):
    """Test profile_image_url returns the first (only) image."""
    url = "https://example.com/image1.jpg"
    vampire.profile.images.append(url)

    assert vampire.profile_image_url == url


def test_profile_image_url_multiple_images(vampire):
    """Test profile_image_url returns the first image when multiple exist."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    # Should always return the first image
    assert vampire.profile_image_url == urls[0]


def test_profile_image_url_after_adding_images(vampire):
    """Test profile_image_url updates when images are added."""
    assert vampire.profile_image_url is None

    # Add first image
    first_url = "https://example.com/first.jpg"
    vampire.profile.images.append(first_url)
    assert vampire.profile_image_url == first_url

    # Add more images - should still return first
    vampire.profile.images.append("https://example.com/second.jpg")
    vampire.profile.images.append("https://example.com/third.jpg")
    assert vampire.profile_image_url == first_url


def test_profile_image_url_after_removing_first(vampire):
    """Test profile_image_url updates when first image is removed."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    # Remove first image
    vampire.profile.images.pop(0)

    # Should now return what was the second image
    assert vampire.profile_image_url == urls[1]


def test_profile_image_url_after_clearing_images(vampire):
    """Test profile_image_url returns None after clearing all images."""
    vampire.profile.images.extend(
        [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ]
    )

    assert vampire.profile_image_url is not None

    # Clear all images
    vampire.profile.images.clear()

    assert vampire.profile_image_url is None


# RANDOM IMAGE URL TESTS


def test_random_image_url_no_images(vampire):
    """Test random_image_url returns None when no images exist."""
    assert vampire.profile.images == []
    assert vampire.random_image_url() is None


def test_random_image_url_single_image(vampire):
    """Test random_image_url returns the only image."""
    url = "https://example.com/only-image.jpg"
    vampire.profile.images.append(url)

    # With only one image, random should always return it
    assert vampire.random_image_url() == url
    assert vampire.random_image_url() == url
    assert vampire.random_image_url() == url


def test_random_image_url_multiple_images(vampire):
    """Test random_image_url returns one of the available images."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
        "https://example.com/image4.jpg",
        "https://example.com/image5.jpg",
    ]
    vampire.profile.images.extend(urls)

    # Get multiple random selections
    selections = {vampire.random_image_url() for _ in range(20)}

    # All selections should be from the available URLs
    assert selections.issubset(set(urls))

    # With 20 calls on 5 images, we should get at least 2 different ones
    # (This is probabilistic but 20 calls should definitely hit multiple images)
    assert len(selections) >= 2


def test_random_image_url_returns_valid_url(vampire):
    """Test that random_image_url always returns a valid URL from the list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    # Call it many times, all should be valid
    for _ in range(50):
        selected = vampire.random_image_url()
        assert selected in urls


def test_random_image_url_after_clearing_images(vampire):
    """Test random_image_url returns None after clearing images."""
    vampire.profile.images.extend(
        [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ]
    )

    assert vampire.random_image_url() is not None

    vampire.profile.images.clear()

    assert vampire.random_image_url() is None


# HAS BIOGRAPHY TESTS


def test_has_biography_no_content(vampire):
    """Test has_biography returns False when no biography or description exists."""
    assert vampire.profile.biography == ""
    assert vampire.profile.description == ""
    assert vampire.has_biography is False


def test_has_biography_with_biography_only(vampire):
    """Test has_biography returns True when biography is set."""
    vampire.profile.biography = "A mysterious vampire from the old country."

    assert vampire.has_biography is True


def test_has_biography_with_description_only(vampire):
    """Test has_biography returns True when description is set."""
    vampire.profile.description = "Tall, dark hair, piercing eyes"

    assert vampire.has_biography is True


def test_has_biography_with_both(vampire):
    """Test has_biography returns True when both biography and description are set."""
    vampire.profile.biography = "A mysterious vampire from the old country."
    vampire.profile.description = "Tall, dark hair, piercing eyes"

    assert vampire.has_biography is True


def test_has_biography_with_whitespace_only(vampire):
    """Test has_biography with whitespace-only strings."""
    vampire.profile.biography = "   "
    vampire.profile.description = ""

    # Python's truthiness: "   " is truthy, so has_biography should be True
    assert vampire.has_biography is True

    vampire.profile.biography = ""
    vampire.profile.description = "   "
    assert vampire.has_biography is True


def test_has_biography_empty_after_clearing(vampire):
    """Test has_biography returns False after clearing content."""
    vampire.profile.biography = "Some biography"
    vampire.profile.description = "Some description"

    assert vampire.has_biography is True

    # Clear both
    vampire.profile.biography = ""
    vampire.profile.description = ""

    assert vampire.has_biography is False


def test_has_biography_one_empty_one_full(vampire):
    """Test has_biography with one field empty and one full."""
    vampire.profile.biography = "Biography content"
    vampire.profile.description = ""
    assert vampire.has_biography is True

    vampire.profile.biography = ""
    vampire.profile.description = "Description content"
    assert vampire.has_biography is True


# PROFILE IMAGES LIST TESTS


def test_profile_images_empty_by_default(vampire):
    """Test that profile.images is empty by default."""
    assert vampire.profile.images == []
    assert len(vampire.profile.images) == 0


def test_profile_images_add_single(vampire):
    """Test adding a single image to the profile."""
    url = "https://example.com/image.jpg"
    vampire.profile.images.append(url)

    assert len(vampire.profile.images) == 1
    assert vampire.profile.images[0] == url


def test_profile_images_add_multiple(vampire):
    """Test adding multiple images to the profile."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.png",
        "https://example.com/image3.gif",
    ]

    for url in urls:
        vampire.profile.images.append(url)

    assert len(vampire.profile.images) == 3
    assert vampire.profile.images == urls


def test_profile_images_extend(vampire):
    """Test extending the images list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]

    vampire.profile.images.extend(urls)

    assert len(vampire.profile.images) == 3
    assert vampire.profile.images == urls


def test_profile_images_remove(vampire):
    """Test removing images from the profile."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    vampire.profile.images.remove(urls[1])

    assert len(vampire.profile.images) == 2
    assert urls[1] not in vampire.profile.images
    assert vampire.profile.images == [urls[0], urls[2]]


def test_profile_images_pop(vampire):
    """Test popping images from the profile."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    # Pop last
    last = vampire.profile.images.pop()
    assert last == urls[2]
    assert len(vampire.profile.images) == 2

    # Pop specific index
    first = vampire.profile.images.pop(0)
    assert first == urls[0]
    assert len(vampire.profile.images) == 1
    assert vampire.profile.images[0] == urls[1]


def test_profile_images_clear(vampire):
    """Test clearing all images from the profile."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
    ]
    vampire.profile.images.extend(urls)

    assert len(vampire.profile.images) == 2

    vampire.profile.images.clear()

    assert len(vampire.profile.images) == 0
    assert vampire.profile.images == []


def test_profile_images_indexing(vampire):
    """Test indexing into the images list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    assert vampire.profile.images[0] == urls[0]
    assert vampire.profile.images[1] == urls[1]
    assert vampire.profile.images[2] == urls[2]
    assert vampire.profile.images[-1] == urls[2]


def test_profile_images_slicing(vampire):
    """Test slicing the images list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
        "https://example.com/image4.jpg",
    ]
    vampire.profile.images.extend(urls)

    assert vampire.profile.images[1:3] == [urls[1], urls[2]]
    assert vampire.profile.images[:2] == [urls[0], urls[1]]
    assert vampire.profile.images[2:] == [urls[2], urls[3]]


def test_profile_images_iteration(vampire):
    """Test iterating over the images list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg",
    ]
    vampire.profile.images.extend(urls)

    collected = []
    for url in vampire.profile.images:
        collected.append(url)

    assert collected == urls


def test_profile_images_contains(vampire):
    """Test checking if an image URL is in the list."""
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
    ]
    vampire.profile.images.extend(urls)

    assert "https://example.com/image1.jpg" in vampire.profile.images
    assert "https://example.com/image2.jpg" in vampire.profile.images
    assert "https://example.com/image3.jpg" not in vampire.profile.images


# PROFILE BIOGRAPHY/DESCRIPTION TESTS


def test_profile_biography_default_empty(vampire):
    """Test that biography is empty by default."""
    assert vampire.profile.biography == ""


def test_profile_description_default_empty(vampire):
    """Test that description is empty by default."""
    assert vampire.profile.description == ""


def test_profile_biography_set(vampire):
    """Test setting the biography."""
    bio = "A mysterious figure from the dark ages."
    vampire.profile.biography = bio

    assert vampire.profile.biography == bio


def test_profile_description_set(vampire):
    """Test setting the description."""
    desc = "Tall, pale, with haunting eyes."
    vampire.profile.description = desc

    assert vampire.profile.description == desc


def test_profile_biography_multiline(vampire):
    """Test setting a multiline biography."""
    bio = """Born in 1345 in Prague.
Embraced during the Anarch Revolt.
Now residing in modern-day New York."""
    vampire.profile.biography = bio

    assert vampire.profile.biography == bio
    assert "\n" in vampire.profile.biography


def test_profile_biography_unicode(vampire):
    """Test biography with Unicode characters."""
    bio = "Né à Paris, transformé à Москва, vivant à 東京"
    vampire.profile.biography = bio

    assert vampire.profile.biography == bio


def test_profile_description_long(vampire):
    """Test setting a long description."""
    desc = "A" * 1000  # 1000 character description
    vampire.profile.description = desc

    assert vampire.profile.description == desc
    assert len(vampire.profile.description) == 1000


def test_profile_both_biography_and_description(vampire):
    """Test setting both biography and description."""
    bio = "Biography content"
    desc = "Description content"

    vampire.profile.biography = bio
    vampire.profile.description = desc

    assert vampire.profile.biography == bio
    assert vampire.profile.description == desc
    # They should be independent
    assert vampire.profile.biography != vampire.profile.description


def test_profile_clear_biography(vampire):
    """Test clearing the biography."""
    vampire.profile.biography = "Some content"
    assert vampire.profile.biography != ""

    vampire.profile.biography = ""
    assert vampire.profile.biography == ""


def test_profile_clear_description(vampire):
    """Test clearing the description."""
    vampire.profile.description = "Some content"
    assert vampire.profile.description != ""

    vampire.profile.description = ""
    assert vampire.profile.description == ""


# INTEGRATION TESTS


def test_profile_complete_setup(vampire):
    """Test setting up a complete profile with all fields."""
    vampire.profile.biography = "A vampire from the Renaissance period."
    vampire.profile.description = "Elegant, well-dressed, charismatic."
    vampire.profile.images.extend(
        [
            "https://example.com/portrait.jpg",
            "https://example.com/fullbody.jpg",
            "https://example.com/action.jpg",
        ]
    )

    # Verify all fields
    assert vampire.has_biography is True
    assert vampire.profile.biography != ""
    assert vampire.profile.description != ""
    assert len(vampire.profile.images) == 3
    assert vampire.profile_image_url == "https://example.com/portrait.jpg"
    assert vampire.random_image_url() in vampire.profile.images


def test_profile_partial_setup(vampire):
    """Test setting up a partial profile."""
    vampire.profile.biography = "Brief bio"
    vampire.profile.images.append("https://example.com/image.jpg")

    # Biography set, description empty
    assert vampire.has_biography is True
    assert vampire.profile.biography != ""
    assert vampire.profile.description == ""
    assert len(vampire.profile.images) == 1


def test_profile_images_only(vampire):
    """Test profile with only images, no text."""
    vampire.profile.images.extend(
        [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ]
    )

    assert vampire.has_biography is False
    assert len(vampire.profile.images) == 2
    assert vampire.profile_image_url is not None


def test_profile_biography_only(vampire):
    """Test profile with only biography, no images."""
    vampire.profile.biography = "A mysterious vampire."

    assert vampire.has_biography is True
    assert len(vampire.profile.images) == 0
    assert vampire.profile_image_url is None
    assert vampire.random_image_url() is None
