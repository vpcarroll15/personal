import os
from datetime import datetime

from django.db import models
from django.utils.safestring import mark_safe, SafeString
from django.conf import settings
import markdown2


def convert_name_to_directory_format(name: str) -> str:
    """Returns human-readable names to a format that is friendlier for Unix directories."""
    name = "".join([x for x in name if x.isalnum() or x == " "])
    name = name.lower()
    return name.replace(" ", "_")


def convert_markdown_and_mark_safe(text: str | None) -> SafeString | None:
    """Given some input markdown, converts it to HTML and marks it as safe to render."""
    if text is None:
        return None
    review_as_html = markdown2.markdown(text)
    # We mark this as safe because we want Django to render it as HTML. This is obviously safe since I am going to
    # be the one writing the markdown. :)
    return mark_safe(review_as_html)


class Musician(models.Model):
    """Represents one musician or band."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(
        db_index=True,
        auto_now=True,  # Updates each time save() is called
    )

    name = models.CharField(max_length=100, unique=True)
    tags = models.ManyToManyField("Tag")

    def __str__(self) -> str:
        """Returns the musician name."""
        return self.name


class Music(models.Model):
    """Represents one album or piece of music."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(
        db_index=True,
        auto_now=True,  # Updates each time save() is called
    )
    album_released_date = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(default=datetime.now)

    name = models.CharField(max_length=200)
    very_short_description = models.CharField(max_length=500, null=True, blank=True)
    musician = models.ForeignKey(Musician, on_delete=models.CASCADE)
    rating = models.SmallIntegerField()

    album_of_the_month = models.BooleanField(default=False)
    exclude_from_best_of_list = models.BooleanField(default=False)

    src = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self) -> str:
        """Returns the album name prefixed with the musician name."""
        return str(self.musician) + ": " + str(self.name)

    def review(self) -> SafeString | None:
        """Returns the album review as safe HTML, or None if no review file exists."""
        return convert_markdown_and_mark_safe(self.review_txt())

    def review_txt(self) -> str | None:
        """Returns the raw markdown content of the album review, or None if file not found."""
        path_to_review = os.path.join(
            settings.BASE_DIR,
            "music/reviews/",
            convert_name_to_directory_format(self.musician.name),
            convert_name_to_directory_format(self.name) + ".md",
        )
        try:
            with open(path_to_review, encoding="utf-8") as review_file:
                review_as_markdown = review_file.read()
        except IOError:
            return None
        return review_as_markdown

    def description(self) -> str:
        """Returns a description combining tags and a clipped review (max 500 chars)."""
        # Our description of the album is the list of tags plus a shortened version of the review.
        tags = self.musician.tags.all()
        tag_names = [tag.name for tag in tags]
        if len(tag_names):
            tags_string = "(" + ", ".join(tag_names) + ")"
        else:
            tags_string = "[no tags]"

        review = self.review_txt()
        if review:
            review_clipped = review[:500]
            if len(review) != len(review_clipped):
                review_clipped += "..."
        else:
            review_clipped = "[no review]"
        return tags_string + " " + review_clipped

    def image_src(self) -> str | None:
        """Returns the relative path to the album image if it exists, otherwise None."""
        path = os.path.join(
            "music",
            "images",
            convert_name_to_directory_format(self.musician.name),
            convert_name_to_directory_format(self.name) + ".jpg",
        )
        if os.path.exists(os.path.join(settings.BASE_DIR, "music/static", path)):
            return path
        else:
            return None

    def classes(self) -> list[str]:
        """Returns a list of CSS class names derived from the musician's tags."""
        return [tag.classname() for tag in self.musician.tags.all()]


class Tag(models.Model):
    """Encapsulates a tag that can be applied to musicians to classify their work."""

    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        """Returns the tag name."""
        return self.name

    def classname(self) -> str:
        """Returns the tag name formatted as a CSS class (spaces removed)."""
        return self.name.replace(" ", "")


class Comment(models.Model):
    """A user comment on an album."""

    text = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    album = models.ForeignKey(Music, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Returns a formatted string with comment ID and author username."""
        return f"#{self.id}, author={self.author.username}"

    @property
    def display_name(self) -> str:
        """Returns a formatted display name: 'First L.' if available, otherwise username."""
        # Matt Parker will format as Matt P.
        if self.author.first_name and self.author.last_name:
            return self.author.first_name + " " + self.author.last_name[0] + "."
        return self.author.username


class BestOf(models.Model):
    """Data about albums spanning a particular period of time."""

    start_date = models.DateField()
    end_date = models.DateField()

    name = models.CharField(max_length=100)
    include_on_home_page = models.BooleanField(default=True)

    def description_txt(self) -> str | None:
        """Returns the raw markdown description from file, or None if not found."""
        path_to_description = os.path.join(
            settings.BASE_DIR,
            "music/best_of/",
            convert_name_to_directory_format(self.name) + ".md",
        )
        try:
            with open(path_to_description, encoding="utf-8") as description_file:
                description_as_markdown = description_file.read()
        except IOError:
            return None
        return description_as_markdown

    def description(self) -> SafeString | None:
        """Returns the description as safe HTML, or None if no description file exists."""
        return convert_markdown_and_mark_safe(self.description_txt())

    def __str__(self) -> str:
        """Returns a formatted string with name and date range."""
        return "{}: {} until {}".format(
            self.name, self.start_date.isoformat(), self.end_date.isoformat()
        )
