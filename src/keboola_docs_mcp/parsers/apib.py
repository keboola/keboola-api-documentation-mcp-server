"""API Blueprint (.apib) parser."""

import re
from pathlib import Path
from typing import Optional

from ..models import Endpoint, Parameter


class ApibParser:
    """Parser for API Blueprint format (.apib files)."""

    # Regex patterns
    GROUP_PATTERN = re.compile(r"^# Group (.+)$", re.MULTILINE)

    # Resource: ## Name [/path] or ## Name [METHOD /path]
    RESOURCE_PATTERN = re.compile(
        r"^## (.+?) \[(?:(GET|POST|PUT|PATCH|DELETE) )?([^\]]+)\]",
        re.MULTILINE,
    )

    # Action: ### Name [METHOD] or ### Name [METHOD /path]
    ACTION_PATTERN = re.compile(
        r"^### (.+?) \[(GET|POST|PUT|PATCH|DELETE)(?: ([^\]]+))?\]",
        re.MULTILINE,
    )

    # Parameter: + name (type, required/optional) - description
    PARAM_PATTERN = re.compile(
        r"^\s+\+ (\w+)(?: \(([^)]+)\))?(?: - (.+))?$",
        re.MULTILINE,
    )

    # Attribute: + name (type, optional) - description
    ATTR_PATTERN = re.compile(
        r"^\s+\+ (\w+(?:\[\w*\])?)(?: \(([^)]+)\))?(?: - (.+))?$",
        re.MULTILINE,
    )

    def __init__(
        self,
        api_name: str,
        auth_header: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize parser with API metadata.

        Args:
            api_name: Name of the API (e.g., "Storage API")
            auth_header: Authentication header name
            base_url: Base URL for the API
        """
        self.api_name = api_name
        self.auth_header = auth_header
        self.base_url = base_url

    def parse(self, content: str) -> list[Endpoint]:
        """Parse API Blueprint content and return endpoints.

        Args:
            content: API Blueprint file content

        Returns:
            List of Endpoint objects
        """
        endpoints = []

        # Split content by groups
        group_splits = self.GROUP_PATTERN.split(content)

        # First part is the intro (before first group)
        group_splits[0] if group_splits else ""

        # Process groups (pairs of group_name, group_content)
        for i in range(1, len(group_splits), 2):
            group_name = group_splits[i].strip()
            group_content = group_splits[i + 1] if i + 1 < len(group_splits) else ""

            # Find all resources in the group
            endpoints.extend(self._parse_group(group_name, group_content))

        return endpoints

    def _parse_group(self, group_name: str, content: str) -> list[Endpoint]:
        """Parse a group section."""
        endpoints = []

        # Find resources
        resource_matches = list(self.RESOURCE_PATTERN.finditer(content))

        for i, match in enumerate(resource_matches):
            resource_name = match.group(1).strip()
            resource_method = match.group(2)  # May be None
            resource_path = match.group(3).strip()

            # Get content until next resource
            start = match.end()
            end = resource_matches[i + 1].start() if i + 1 < len(resource_matches) else len(content)
            resource_content = content[start:end]

            # If resource has a method, it's also an endpoint
            if resource_method:
                endpoint = self._create_endpoint(
                    group_name,
                    resource_name,
                    resource_method,
                    resource_path,
                    resource_content,
                )
                endpoints.append(endpoint)

            # Find actions within the resource
            action_matches = list(self.ACTION_PATTERN.finditer(resource_content))

            for j, action_match in enumerate(action_matches):
                action_name = action_match.group(1).strip()
                action_method = action_match.group(2)
                action_path = action_match.group(3)

                # Use action path if provided, otherwise use resource path
                path = action_path.strip() if action_path else resource_path

                # Get content until next action
                action_start = action_match.end()
                action_end = (
                    action_matches[j + 1].start()
                    if j + 1 < len(action_matches)
                    else len(resource_content)
                )
                action_content = resource_content[action_start:action_end]

                # Use action name or combine with resource name
                name = action_name if action_name else resource_name

                endpoint = self._create_endpoint(
                    group_name,
                    name,
                    action_method,
                    path,
                    action_content,
                )
                endpoints.append(endpoint)

        return endpoints

    def _create_endpoint(
        self,
        section: str,
        name: str,
        method: str,
        path: str,
        content: str,
    ) -> Endpoint:
        """Create an Endpoint from parsed data."""
        # Extract parameters
        parameters = self._parse_parameters(content)

        # Extract attributes (body parameters)
        attributes = self._parse_attributes(content)
        parameters.extend(attributes)

        # Extract request/response examples
        request_example = self._extract_example(content, "Request")
        response_example = self._extract_example(content, "Response")

        # Get description (first paragraph after the header)
        description = self._extract_description(content)

        return Endpoint(
            api_name=self.api_name,
            section=section,
            path=path,
            method=method,
            summary=name,
            description=description,
            parameters=parameters,
            request_example=request_example,
            response_example=response_example,
            auth_header=self.auth_header,
            base_url=self.base_url,
        )

    def _parse_parameters(self, content: str) -> list[Parameter]:
        """Extract parameters from content."""
        parameters = []

        # Find Parameters section
        params_match = re.search(r"\+ Parameters\s*\n((?:\s+\+.+\n?)+)", content)
        if not params_match:
            return parameters

        params_content = params_match.group(1)

        for match in self.PARAM_PATTERN.finditer(params_content):
            name = match.group(1)
            type_info = match.group(2) or ""
            description = match.group(3) or ""

            # Parse type info (e.g., "required, number")
            required = "required" in type_info.lower()
            param_type = "string"
            for t in ["number", "integer", "boolean", "string", "array", "object"]:
                if t in type_info.lower():
                    param_type = t
                    break

            parameters.append(
                Parameter(
                    name=name,
                    location="path" if "{" + name + "}" in content else "query",
                    type=param_type,
                    required=required,
                    description=description.strip(),
                )
            )

        return parameters

    def _parse_attributes(self, content: str) -> list[Parameter]:
        """Extract body attributes from content."""
        parameters = []

        # Find Attributes section
        attrs_match = re.search(r"\+ Attributes\s*\n((?:\s+\+.+\n?)+)", content)
        if not attrs_match:
            return parameters

        attrs_content = attrs_match.group(1)

        for match in self.ATTR_PATTERN.finditer(attrs_content):
            name = match.group(1)
            type_info = match.group(2) or ""
            description = match.group(3) or ""

            # Parse type info
            required = "required" in type_info.lower()
            optional = "optional" in type_info.lower()
            param_type = "string"
            for t in ["number", "integer", "boolean", "string", "array", "object"]:
                if t in type_info.lower():
                    param_type = t
                    break

            parameters.append(
                Parameter(
                    name=name,
                    location="body",
                    type=param_type,
                    required=required and not optional,
                    description=description.strip(),
                )
            )

        return parameters

    def _extract_example(self, content: str, section: str) -> Optional[str]:
        """Extract request or response example."""
        # Look for + Request or + Response followed by Body
        pattern = rf"\+ {section}.*?\n.*?\+ Body\s*\n((?:\s+.+\n?)+)"
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Clean up the indentation
            example = match.group(1)
            lines = example.split("\n")
            # Remove common leading whitespace
            if lines:
                min_indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
                cleaned = "\n".join(
                    line[min_indent:] if len(line) > min_indent else line for line in lines
                )
                return cleaned.strip()

        return None

    def _extract_description(self, content: str) -> str:
        """Extract description (text before any + markers)."""
        lines = []
        for line in content.split("\n"):
            if line.strip().startswith("+") or line.strip().startswith("#"):
                break
            if line.strip():
                lines.append(line.strip())
        return " ".join(lines)

    @classmethod
    def parse_file(
        cls,
        file_path: Path,
        api_name: str,
        auth_header: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> list[Endpoint]:
        """Parse an API Blueprint file.

        Args:
            file_path: Path to the .apib file
            api_name: Name of the API
            auth_header: Authentication header name
            base_url: Base URL for the API

        Returns:
            List of Endpoint objects
        """
        content = file_path.read_text(encoding="utf-8")
        parser = cls(api_name, auth_header, base_url)
        return parser.parse(content)
