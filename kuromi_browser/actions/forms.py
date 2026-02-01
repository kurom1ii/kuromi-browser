"""
Form Handler Utilities for kuromi-browser.

Provides high-level APIs for interacting with HTML forms:
inputs, selects, checkboxes, radio buttons, and file uploads.
"""

from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.dom.element import Element

from kuromi_browser.actions.keyboard import KeyboardController
from kuromi_browser.actions.mouse import MouseController


class InputType(str, Enum):
    """HTML input types."""

    TEXT = "text"
    PASSWORD = "password"
    EMAIL = "email"
    NUMBER = "number"
    TEL = "tel"
    URL = "url"
    SEARCH = "search"
    DATE = "date"
    TIME = "time"
    DATETIME_LOCAL = "datetime-local"
    MONTH = "month"
    WEEK = "week"
    COLOR = "color"
    RANGE = "range"
    FILE = "file"
    HIDDEN = "hidden"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SUBMIT = "submit"
    BUTTON = "button"
    RESET = "reset"


@dataclass
class FormField:
    """Represents a form field."""

    element: "Element"
    name: str
    field_type: str
    value: Optional[str] = None
    options: List[str] = field(default_factory=list)
    is_required: bool = False
    is_disabled: bool = False


@dataclass
class SelectOption:
    """Represents a select option."""

    value: str
    text: str
    index: int
    selected: bool = False
    disabled: bool = False


class FormHandler:
    """High-level form interaction handler.

    Provides utilities for filling forms, handling various input types,
    and submitting forms.

    Example:
        form = FormHandler(cdp_session)
        await form.fill_input(email_input, "user@example.com")
        await form.select_option(country_select, "US")
        await form.check(terms_checkbox)
        await form.submit(submit_button)
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        *,
        human_like: bool = True,
    ) -> None:
        """Initialize FormHandler.

        Args:
            cdp_session: CDP session for sending commands.
            human_like: Use human-like interactions.
        """
        self._session = cdp_session
        self._human_like = human_like
        self._mouse = MouseController(cdp_session, human_like=human_like)
        self._keyboard = KeyboardController(cdp_session, human_like=human_like)

    # Input handling

    async def fill(
        self,
        element: "Element",
        value: str,
        *,
        clear_first: bool = True,
        use_keyboard: bool = True,
    ) -> None:
        """Fill an input or textarea with text.

        Args:
            element: Input element to fill.
            value: Value to fill.
            clear_first: Clear existing content first.
            use_keyboard: Use keyboard typing (more human-like).
        """
        await element.scroll_into_view()
        await asyncio.sleep(0.1)

        if use_keyboard and self._human_like:
            await self._keyboard.type_into(element, value, clear_first=clear_first)
        else:
            await element.fill(value)

    async def fill_input(
        self,
        element: "Element",
        value: str,
        *,
        validate: bool = False,
    ) -> None:
        """Fill a text input field.

        Args:
            element: Input element.
            value: Value to fill.
            validate: Trigger validation events.
        """
        await self.fill(element, value)

        if validate:
            # Trigger blur to validate
            await element._call_function(
                "function() { this.dispatchEvent(new Event('blur', { bubbles: true })); }"
            )

    async def fill_password(
        self,
        element: "Element",
        password: str,
    ) -> None:
        """Fill a password field.

        Args:
            element: Password input element.
            password: Password to fill.
        """
        # Use direct fill for password (no typing visible anyway)
        await element.fill(password)

    async def fill_number(
        self,
        element: "Element",
        value: Union[int, float],
        *,
        use_arrows: bool = False,
    ) -> None:
        """Fill a number input.

        Args:
            element: Number input element.
            value: Numeric value.
            use_arrows: Use arrow keys to adjust (more human-like).
        """
        if use_arrows:
            # Get current value and adjust
            current = await element.property("value")
            try:
                current_num = float(current) if current else 0
            except ValueError:
                current_num = 0

            diff = int(value - current_num)
            if diff != 0:
                await element.focus()
                key = "ArrowUp" if diff > 0 else "ArrowDown"
                for _ in range(abs(diff)):
                    await self._keyboard.press(key)
                    await asyncio.sleep(0.05)
        else:
            await self.fill(element, str(value))

    async def fill_date(
        self,
        element: "Element",
        value: str,
    ) -> None:
        """Fill a date input.

        Args:
            element: Date input element.
            value: Date value in format YYYY-MM-DD.
        """
        # Date inputs need direct value setting
        await element._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )

    async def fill_time(
        self,
        element: "Element",
        value: str,
    ) -> None:
        """Fill a time input.

        Args:
            element: Time input element.
            value: Time value in format HH:MM or HH:MM:SS.
        """
        await element._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )

    async def fill_color(
        self,
        element: "Element",
        color: str,
    ) -> None:
        """Fill a color input.

        Args:
            element: Color input element.
            color: Color value in hex format (#RRGGBB).
        """
        await element._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            color,
        )

    async def fill_range(
        self,
        element: "Element",
        value: Union[int, float],
    ) -> None:
        """Fill a range slider.

        Args:
            element: Range input element.
            value: Value within the range.
        """
        await element._call_function(
            """function(value) {
                this.value = value;
                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            value,
        )

    # Select handling

    async def get_select_options(
        self,
        element: "Element",
    ) -> List[SelectOption]:
        """Get all options from a select element.

        Args:
            element: Select element.

        Returns:
            List of SelectOption objects.
        """
        options = await element._call_function(
            """function() {
                return Array.from(this.options).map((opt, idx) => ({
                    value: opt.value,
                    text: opt.text,
                    index: idx,
                    selected: opt.selected,
                    disabled: opt.disabled
                }));
            }"""
        )
        return [SelectOption(**opt) for opt in (options or [])]

    async def select_by_value(
        self,
        element: "Element",
        value: str,
    ) -> None:
        """Select option by value attribute.

        Args:
            element: Select element.
            value: Value to select.
        """
        await element.select_option(value)

    async def select_by_text(
        self,
        element: "Element",
        text: str,
    ) -> None:
        """Select option by visible text.

        Args:
            element: Select element.
            text: Visible text to select.
        """
        await element._call_function(
            """function(text) {
                for (const option of this.options) {
                    if (option.text === text || option.text.trim() === text) {
                        option.selected = true;
                        this.dispatchEvent(new Event('input', { bubbles: true }));
                        this.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }
                return false;
            }""",
            text,
        )

    async def select_by_index(
        self,
        element: "Element",
        index: int,
    ) -> None:
        """Select option by index.

        Args:
            element: Select element.
            index: Index of option to select.
        """
        await element._call_function(
            """function(index) {
                if (index >= 0 && index < this.options.length) {
                    this.selectedIndex = index;
                    this.dispatchEvent(new Event('input', { bubbles: true }));
                    this.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
            }""",
            index,
        )

    async def select_multiple(
        self,
        element: "Element",
        values: Sequence[str],
    ) -> List[str]:
        """Select multiple options (for multi-select).

        Args:
            element: Multi-select element.
            values: Values to select.

        Returns:
            List of actually selected values.
        """
        return await element.select_option(*values)

    async def deselect_all(
        self,
        element: "Element",
    ) -> None:
        """Deselect all options in a multi-select.

        Args:
            element: Multi-select element.
        """
        await element._call_function(
            """function() {
                for (const option of this.options) {
                    option.selected = false;
                }
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }"""
        )

    # Checkbox and Radio handling

    async def check(
        self,
        element: "Element",
        *,
        use_click: bool = True,
    ) -> None:
        """Check a checkbox or radio button.

        Args:
            element: Checkbox or radio element.
            use_click: Use mouse click (more human-like).
        """
        is_checked = await element.is_checked()
        if not is_checked:
            if use_click and self._human_like:
                await self._mouse.click_element(element)
            else:
                await element._call_function(
                    """function() {
                        this.checked = true;
                        this.dispatchEvent(new Event('input', { bubbles: true }));
                        this.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )

    async def uncheck(
        self,
        element: "Element",
        *,
        use_click: bool = True,
    ) -> None:
        """Uncheck a checkbox.

        Args:
            element: Checkbox element.
            use_click: Use mouse click (more human-like).
        """
        is_checked = await element.is_checked()
        if is_checked:
            if use_click and self._human_like:
                await self._mouse.click_element(element)
            else:
                await element._call_function(
                    """function() {
                        this.checked = false;
                        this.dispatchEvent(new Event('input', { bubbles: true }));
                        this.dispatchEvent(new Event('change', { bubbles: true }));
                    }"""
                )

    async def toggle(
        self,
        element: "Element",
    ) -> bool:
        """Toggle a checkbox state.

        Args:
            element: Checkbox element.

        Returns:
            New checked state.
        """
        is_checked = await element.is_checked()
        if is_checked:
            await self.uncheck(element)
        else:
            await self.check(element)
        return not is_checked

    async def select_radio(
        self,
        element: "Element",
    ) -> None:
        """Select a radio button.

        Args:
            element: Radio button element.
        """
        await self.check(element)

    async def select_radio_by_value(
        self,
        container: "Element",
        name: str,
        value: str,
    ) -> None:
        """Select a radio button by its value in a group.

        Args:
            container: Container element with radio group.
            name: Name attribute of radio group.
            value: Value to select.
        """
        radio = await container.query(f'input[type="radio"][name="{name}"][value="{value}"]')
        if radio:
            await self.check(radio)

    # File upload handling

    async def upload_file(
        self,
        element: "Element",
        file_path: Union[str, Path],
    ) -> None:
        """Upload a file through a file input.

        Args:
            element: File input element.
            file_path: Path to file to upload.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # Get the node for file selection
        node_id = element.node_id

        await self._session.send(
            "DOM.setFileInputFiles",
            {
                "nodeId": node_id,
                "files": [str(path)],
            },
        )

    async def upload_files(
        self,
        element: "Element",
        file_paths: Sequence[Union[str, Path]],
    ) -> None:
        """Upload multiple files through a file input.

        Args:
            element: File input element (with multiple attribute).
            file_paths: Paths to files to upload.
        """
        paths = []
        for fp in file_paths:
            path = Path(fp).resolve()
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            paths.append(str(path))

        node_id = element.node_id

        await self._session.send(
            "DOM.setFileInputFiles",
            {
                "nodeId": node_id,
                "files": paths,
            },
        )

    async def upload_file_data(
        self,
        element: "Element",
        filename: str,
        data: bytes,
        mime_type: str = "application/octet-stream",
    ) -> None:
        """Upload file from raw bytes data.

        Args:
            element: File input element.
            filename: Name for the file.
            data: File content as bytes.
            mime_type: MIME type of the file.
        """
        # Create a data transfer with the file
        b64_data = base64.b64encode(data).decode("utf-8")

        await element._call_function(
            """function(filename, b64Data, mimeType) {
                const byteChars = atob(b64Data);
                const byteNumbers = new Array(byteChars.length);
                for (let i = 0; i < byteChars.length; i++) {
                    byteNumbers[i] = byteChars.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const file = new File([byteArray], filename, { type: mimeType });

                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                this.files = dataTransfer.files;

                this.dispatchEvent(new Event('input', { bubbles: true }));
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            filename,
            b64_data,
            mime_type,
        )

    async def clear_file_input(
        self,
        element: "Element",
    ) -> None:
        """Clear a file input.

        Args:
            element: File input element.
        """
        await element._call_function(
            """function() {
                this.value = '';
                this.dispatchEvent(new Event('change', { bubbles: true }));
            }"""
        )

    # Form submission

    async def submit(
        self,
        element: "Element",
        *,
        use_click: bool = True,
    ) -> None:
        """Submit a form or click a submit button.

        Args:
            element: Form element or submit button.
            use_click: Click submit button (vs form.submit()).
        """
        tag_name = await element.tag_name()

        if tag_name == "form":
            if use_click:
                # Find and click submit button
                submit_btn = await element.query('input[type="submit"], button[type="submit"], button:not([type])')
                if submit_btn:
                    await self._mouse.click_element(submit_btn)
                else:
                    await element._call_function("function() { this.submit(); }")
            else:
                await element._call_function("function() { this.submit(); }")
        else:
            # Assume it's a button
            if use_click and self._human_like:
                await self._mouse.click_element(element)
            else:
                await element.click(force=True)

    async def reset(
        self,
        form_element: "Element",
    ) -> None:
        """Reset a form to its initial values.

        Args:
            form_element: Form element.
        """
        await form_element._call_function("function() { this.reset(); }")

    # Form analysis

    async def get_form_fields(
        self,
        form_element: "Element",
    ) -> List[FormField]:
        """Get all fields in a form.

        Args:
            form_element: Form element.

        Returns:
            List of FormField objects.
        """
        fields_data = await form_element._call_function(
            """function() {
                const fields = [];
                const elements = this.elements;

                for (let i = 0; i < elements.length; i++) {
                    const el = elements[i];
                    const field = {
                        name: el.name || '',
                        field_type: el.type || el.tagName.toLowerCase(),
                        value: el.value || '',
                        is_required: el.required || false,
                        is_disabled: el.disabled || false,
                        options: []
                    };

                    if (el.tagName === 'SELECT') {
                        field.options = Array.from(el.options).map(o => o.value);
                    }

                    fields.push(field);
                }

                return fields;
            }"""
        )

        # Now get actual elements
        result = []
        elements = await form_element.query_all("input, select, textarea, button")

        for i, field_data in enumerate(fields_data or []):
            if i < len(elements):
                result.append(FormField(
                    element=elements[i],
                    name=field_data.get("name", ""),
                    field_type=field_data.get("field_type", ""),
                    value=field_data.get("value"),
                    options=field_data.get("options", []),
                    is_required=field_data.get("is_required", False),
                    is_disabled=field_data.get("is_disabled", False),
                ))

        return result

    async def fill_form(
        self,
        form_element: "Element",
        data: Dict[str, Any],
        *,
        submit: bool = False,
    ) -> None:
        """Fill an entire form with data.

        Args:
            form_element: Form element.
            data: Dictionary of field name -> value.
            submit: Submit the form after filling.
        """
        fields = await self.get_form_fields(form_element)

        for field in fields:
            if field.name not in data or field.is_disabled:
                continue

            value = data[field.name]

            if field.field_type in ("text", "password", "email", "tel", "url", "search"):
                await self.fill(field.element, str(value))

            elif field.field_type == "number":
                await self.fill_number(field.element, value)

            elif field.field_type in ("date", "datetime-local", "month", "week"):
                await self.fill_date(field.element, str(value))

            elif field.field_type == "time":
                await self.fill_time(field.element, str(value))

            elif field.field_type == "color":
                await self.fill_color(field.element, str(value))

            elif field.field_type == "range":
                await self.fill_range(field.element, value)

            elif field.field_type == "checkbox":
                if value:
                    await self.check(field.element)
                else:
                    await self.uncheck(field.element)

            elif field.field_type == "radio":
                if str(value) == await field.element.property("value"):
                    await self.check(field.element)

            elif field.field_type == "select-one":
                await self.select_by_value(field.element, str(value))

            elif field.field_type == "select-multiple":
                if isinstance(value, (list, tuple)):
                    await self.select_multiple(field.element, [str(v) for v in value])
                else:
                    await self.select_by_value(field.element, str(value))

            elif field.field_type == "textarea":
                await self.fill(field.element, str(value))

            elif field.field_type == "file":
                if isinstance(value, (str, Path)):
                    await self.upload_file(field.element, value)
                elif isinstance(value, (list, tuple)):
                    await self.upload_files(field.element, value)

            # Small delay between fields
            if self._human_like:
                await asyncio.sleep(0.1)

        if submit:
            await self.submit(form_element)

    async def get_form_data(
        self,
        form_element: "Element",
    ) -> Dict[str, Any]:
        """Get current form data as dictionary.

        Args:
            form_element: Form element.

        Returns:
            Dictionary of field name -> value.
        """
        return await form_element._call_function(
            """function() {
                const formData = new FormData(this);
                const data = {};
                for (const [key, value] of formData.entries()) {
                    if (key in data) {
                        if (Array.isArray(data[key])) {
                            data[key].push(value);
                        } else {
                            data[key] = [data[key], value];
                        }
                    } else {
                        data[key] = value;
                    }
                }
                return data;
            }"""
        )

    async def validate_form(
        self,
        form_element: "Element",
    ) -> bool:
        """Check if form passes HTML5 validation.

        Args:
            form_element: Form element.

        Returns:
            True if form is valid.
        """
        return await form_element._call_function(
            "function() { return this.checkValidity(); }"
        )

    async def get_validation_message(
        self,
        element: "Element",
    ) -> str:
        """Get validation message for an input.

        Args:
            element: Input element.

        Returns:
            Validation message or empty string.
        """
        return await element._call_function(
            "function() { return this.validationMessage || ''; }"
        )


__all__ = ["FormHandler", "FormField", "SelectOption", "InputType"]
