## ADDED Requirements

### Requirement: Translation function
The system SHALL provide a `t(key)` function returning localized text for the current language (`en` or `zh`), with key-as-fallback for missing translations.

#### Scenario: Chinese translation
- **WHEN** lang is `zh` and `t('nav_dashboard')` is called
- **THEN** it SHALL return `"大盘概览"`

#### Scenario: English translation
- **WHEN** lang is `en` and `t('nav_dashboard')` is called
- **THEN** it SHALL return `"Dashboard"`

### Requirement: Language toggle UI
A pill-shaped "EN / 中文" toggle SHALL appear in the top header. Clicking it SHALL switch language and re-render all i18n-driven content without page refresh.

#### Scenario: Toggle language
- **WHEN** user clicks the language toggle while in `zh` mode
- **THEN** all `data-i18n` elements and dynamic labels SHALL re-render in English

### Requirement: Declarative i18n binding
Elements with `data-i18n="key"` SHALL have their textContent auto-updated on language switch.

#### Scenario: Auto-update
- **WHEN** language changes
- **THEN** all `data-i18n` elements SHALL reflect the new language
