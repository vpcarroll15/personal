# Claude Code Guide for This Repository

This file contains helpful context about this Django monorepo to help Claude (or other developers) work effectively with the codebase.

## Project Overview

This is a personal Django project containing multiple apps for tracking various aspects of life through SMS interactions, music reviews, prayer snippets, scavenger hunts, and daily goals.

**Tech Stack:**
- Django (Python 3.12)
- PostgreSQL (with ArrayField support)
- Twilio (SMS integration)
- Anthropic API (AI-powered daily goals)
- REST Framework

## Project Structure

### Django Apps

1. **`music/`** - Music album reviews and tracking
   - Coverage: 100%
   - Features: Album reviews (markdown), tags, comments, best-of lists
   - Key models: Music, Musician, Tag, Comment, BestOf

2. **`prayer/`** - Prayer snippet management
   - Coverage: 100%
   - Features: Prayer snippets from SMS responses, categorization (gratitude/request/praise)
   - Key models: PrayerSnippet
   - Integration: Links to SMS app via callbacks

3. **`daily_goals/`** - Daily goal tracking via SMS
   - Coverage: 100%
   - Features: AI-generated daily goals, SMS check-ins
   - Key models: User, DailyCheckin
   - Integration: Twilio + Anthropic Claude API

4. **`sms/`** - SMS-based data collection
   - Coverage: 87% (models: 100%, some view functions untested)
   - Features: Question/response tracking, scheduled SMS prompts
   - Key models: Question, User, DataPoint
   - Integration: Twilio webhooks

5. **`scavenger_hunt/`** - GPS-based scavenger hunt game
   - Coverage: 99% (41 tests)
   - Features: Location-based challenges, hints, solutions
   - Key models: Location, ScavengerHuntTemplate, ScavengerHunt
   - Uses geographiclib for distance/heading calculations

### Support Packages

6. **`twilio_managers/`** - Standalone scripts for SMS automation
   - Coverage: 0% (no tests - these are production daemon scripts)
   - `sms_app_manager_main.py`: Sends scheduled SMS questions
   - `daily_goals_app_manager_main.py`: Sends daily goal prompts with AI
   - `api_client.py`: REST API client for Django backend
   - **Note**: These run as separate processes, not within Django

## Code Quality Standards

### Type Hints
- **Modern syntax**: Use `dict[str, Any]` instead of `Dict[str, Any]`
- **Union syntax**: Use `str | None` instead of `Optional[str]`
- **All functions** should have return type annotations
- **All parameters** should have type annotations

### String Formatting
- **Always use f-strings**: `f"User {user.id}"` ✓
- **Never use .format()**: `"User {}".format(user.id)` ✗
- **Never use %**: `"User %s" % user.id` ✗

### Constants
- Extract magic numbers and strings to module-level constants
- Use UPPER_CASE naming for constants
- Group related constants together at the top of files

Example:
```python
# Constants
DEFAULT_RADIUS_METERS = 30
CYCLE_SLEEP_SECONDS = 60 * 15  # 15 minutes
```

### Model Meta Classes
All Django models should have a Meta class with:
- `ordering`: Specify default query ordering
- `verbose_name`: Human-readable singular name
- `verbose_name_plural`: Human-readable plural name
- `indexes`: Add indexes for common query patterns (if needed)

Example:
```python
class MyModel(models.Model):
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "My Model"
        verbose_name_plural = "My Models"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]
```

### Dataclasses
- Use `@dataclass` for data transfer objects (DTOs)
- Prefer dataclasses over regular classes when there's no complex behavior
- Use `__post_init__` for type conversions and validation

### Imports
- Standard library imports first
- Third-party imports second
- Local app imports last
- Use `from package import module` for internal packages
- **isort** automatically manages import ordering (configured with `--profile=black`)

## Testing

### Coverage Targets
- **Target: 100% for all apps** (or very close)
- Current status:
  - music: 100% ✓
  - prayer: 100% ✓
  - daily_goals: 100% ✓
  - scavenger_hunt: 99% ✓
  - sms: 87% (models at 100%)
  - twilio_managers: 0% (standalone scripts, not critical)

### Testing Patterns
1. **Use `setUpTestData()` for class-level fixtures**
   - More efficient than `setUp()`
   - Data created once per test class

2. **Organize tests by type**
   - `test_models.py`: Model method tests
   - `test_views.py`: View and helper function tests
   - `test_integration.py`: End-to-end tests (if needed)
   - `tests.py`: Simple apps can use a single file

3. **Test naming convention**
   - Format: `test_<what>_<condition>_<expected>`
   - Example: `test_location_is_completed_correct_solution`

4. **Use freezegun for datetime testing**
   ```python
   from freezegun import freeze_time

   @freeze_time("2024-01-15")
   def test_something():
       # ...
   ```

5. **Mock external services**
   - Use `@patch` for external API calls
   - Use Django's `Client` for view tests
   - Use `APITestCase` for REST framework views

### Running Tests
```bash
# Single app
python manage.py test music

# All apps
python manage.py test

# With coverage
coverage run --source=music manage.py test music
coverage report -m --include="music/*"
```

## Pre-commit Hooks

Configured hooks (automatically run on commit):
1. **trailing-whitespace**: Remove trailing whitespace
2. **end-of-file-fixer**: Ensure files end with newline
3. **check-yaml**: Validate YAML files
4. **isort**: Sort imports (with `--profile=black`)
5. **black**: Format code
6. **mypy**: Type checking (for specified apps only)

### Mypy Configuration
- **File**: `mypy.ini`
- **Philosophy**: Check all code by default, with Django-friendly settings
- **Global settings**: `check_untyped_defs = True`
- **Excludes**: Migrations, virtual env, test files
- **Type stubs**: Added `types-python-dateutil`, `types-pytz`, `types-requests`

**Important**: The mypy config is now **global by default** - no need to add per-module configuration for new files!

## Django Patterns

### Model Methods
Common methods to implement:
- `__str__()`: String representation (always include, always type as `-> str`)
- `to_dict_for_api()`: Serialization for API responses (type as `-> dict[str, Any]`)
- `clean()`: Model validation (type as `-> None`)

### API Views
- Use REST Framework's `APIView` for class-based views
- Create permission classes in `permissions.py`
- Common pattern:
  ```python
  class MyView(APIView):
      permission_classes = [IsAuthenticated, MyCustomPermission]

      def get(self, request: HttpRequest) -> Response:
          # ...
  ```

### Callbacks Pattern
SMS app uses a callback pattern for triggered actions:
- Callbacks defined as module-level functions
- Registered in `callbacks_pool` dict
- Referenced by string name in database
- Triggered in model `save()` method

Example from `sms/models.py`:
```python
def create_prayer_snippet(prayer_type: str, data_point: "DataPoint") -> None:
    # ... implementation

callbacks_pool = {
    "create_gratitude_prayer_snippet": create_gratitude_prayer_snippet,
}
```

## Common Pitfalls

1. **Don't use .format() or %** - Always use f-strings
2. **Don't skip type hints** - All functions need return types
3. **Don't use old Union syntax** - Use `str | None` not `Optional[str]`
4. **Don't use Dict/List/Tuple** - Use `dict`/`list`/`tuple` (lowercase)
5. **Don't manually update mypy.ini** - Global config applies to all files now
6. **Don't forget Model Meta classes** - All models should have them
7. **Don't skip tests** - Aim for 100% coverage on all new code
8. **Don't use naive datetimes** - Always use timezone-aware (you'll see warnings)

## File Patterns

### Imports in twilio_managers
These are standalone scripts, so they use package-relative imports:
```python
from twilio_managers.api_client import TwilioManagerApiClient
from twilio_managers.platform_info import install_environment_variables
```

### Dataclass Converters
Pattern for converting serialized data:
```python
def datetime_converter(value: str | datetime) -> datetime:
    if isinstance(value, str):
        return dateutil.parser.parse(value)
    return value

@dataclass
class User:
    created_at: datetime

    def __post_init__(self) -> None:
        self.created_at = datetime_converter(self.created_at)
```

## Development Workflow

1. **Make changes** to code
2. **Run tests**: `python manage.py test <app_name>`
3. **Check coverage**: `coverage run --source=<app> manage.py test <app> && coverage report`
4. **Commit**: Pre-commit hooks automatically run isort, black, and mypy
5. **If hooks fail**: Fix issues and commit again

## Key Files

- `mypy.ini`: Type checking configuration (global settings only now)
- `.pre-commit-config.yaml`: Pre-commit hook configuration
- `requirements.txt`: Python dependencies
- `website/settings.py`: Django settings
- `website/urls.py`: URL routing

## Environment Variables (for twilio_managers)

The standalone scripts require these env vars:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_SMS_APP_PHONE_NUMBER`
- `TWILIO_DAILY_GOALS_APP_PHONE_NUMBER`
- `SMS_SENDER_API_USERNAME`
- `SMS_SENDER_API_PASSWORD`
- `ANTHROPIC_API_KEY`
- `API_PROTOCOL` (default: "http")
- `API_DOMAIN` (default: "localhost:8000")

Loaded from `/home/ubuntu/environment.env` in production.

## Recent Improvements

All apps have been recently modernized with:
- ✅ Comprehensive test coverage (target: 100%)
- ✅ Modern type hints (Python 3.10+ syntax)
- ✅ F-string migration (no more .format())
- ✅ Constants extraction
- ✅ Model Meta classes
- ✅ Global mypy configuration
- ✅ Pre-commit hooks (isort, black, mypy)

## Questions?

If you're Claude Code working on this repository, you now have all the context you need! Follow the patterns above, maintain the quality standards, and you'll do great. 🚀
