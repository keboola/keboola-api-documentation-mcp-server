"""OpenAPI/Swagger parser."""

import json
from pathlib import Path
from typing import Any, Optional

import yaml

from ..models import Endpoint, Parameter


class OpenApiParser:
    """Parser for OpenAPI/Swagger specifications."""

    HTTP_METHODS = ["get", "post", "put", "patch", "delete", "head", "options"]

    def __init__(
        self,
        api_name: str,
        auth_header: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize parser with API metadata.

        Args:
            api_name: Name of the API
            auth_header: Authentication header name
            base_url: Base URL for the API
        """
        self.api_name = api_name
        self.auth_header = auth_header
        self.base_url = base_url

    def parse(self, spec: dict[str, Any]) -> list[Endpoint]:
        """Parse OpenAPI specification and return endpoints.

        Args:
            spec: Parsed OpenAPI specification dict

        Returns:
            List of Endpoint objects
        """
        endpoints = []

        # Get base URL from spec if not provided
        base_url = self.base_url
        if not base_url:
            # OpenAPI 3.x
            if "servers" in spec and spec["servers"]:
                base_url = spec["servers"][0].get("url", "")
            # Swagger 2.x
            elif "host" in spec:
                scheme = spec.get("schemes", ["https"])[0]
                base_path = spec.get("basePath", "")
                base_url = f"{scheme}://{spec['host']}{base_path}"

        # Get paths
        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            # Get section from tags
            default_section = "General"

            for method in self.HTTP_METHODS:
                if method not in path_item:
                    continue

                operation = path_item[method]

                # Get section from tags
                tags = operation.get("tags", [])
                section = tags[0] if tags else default_section

                # Get summary and description
                summary = operation.get("summary", operation.get("operationId", f"{method.upper()} {path}"))
                description = operation.get("description", "")

                # Parse parameters
                parameters = self._parse_parameters(operation.get("parameters", []))

                # Add path-level parameters
                if "parameters" in path_item:
                    parameters.extend(self._parse_parameters(path_item["parameters"]))

                # Parse request body (OpenAPI 3.x)
                if "requestBody" in operation:
                    body_params = self._parse_request_body(operation["requestBody"])
                    parameters.extend(body_params)

                # Get examples
                request_example = self._get_request_example(operation)
                response_example = self._get_response_example(operation)

                endpoint = Endpoint(
                    api_name=self.api_name,
                    section=section,
                    path=path,
                    method=method.upper(),
                    summary=summary,
                    description=description,
                    parameters=parameters,
                    request_example=request_example,
                    response_example=response_example,
                    auth_header=self.auth_header,
                    base_url=base_url,
                )
                endpoints.append(endpoint)

        return endpoints

    def _parse_parameters(self, params: list[dict[str, Any]]) -> list[Parameter]:
        """Parse OpenAPI parameters."""
        result = []

        for param in params:
            # Handle $ref
            if "$ref" in param:
                continue  # Skip refs for now

            name = param.get("name", "")
            location = param.get("in", "query")
            required = param.get("required", False)
            description = param.get("description", "")

            # Get type from schema
            schema = param.get("schema", param)
            param_type = schema.get("type", "string")
            default = schema.get("default")
            example = schema.get("example")

            result.append(Parameter(
                name=name,
                location=location,
                type=param_type,
                required=required,
                description=description,
                default=str(default) if default is not None else None,
                example=str(example) if example is not None else None,
            ))

        return result

    def _parse_request_body(self, request_body: dict[str, Any]) -> list[Parameter]:
        """Parse OpenAPI 3.x request body."""
        params = []

        content = request_body.get("content", {})
        required = request_body.get("required", False)

        # Try JSON content type first
        for content_type in ["application/json", "application/x-www-form-urlencoded", "*/*"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                props = schema.get("properties", {})
                required_props = schema.get("required", [])

                for name, prop_schema in props.items():
                    params.append(Parameter(
                        name=name,
                        location="body",
                        type=prop_schema.get("type", "string"),
                        required=name in required_props,
                        description=prop_schema.get("description", ""),
                        default=str(prop_schema.get("default")) if prop_schema.get("default") is not None else None,
                        example=str(prop_schema.get("example")) if prop_schema.get("example") is not None else None,
                    ))
                break

        return params

    def _get_request_example(self, operation: dict[str, Any]) -> Optional[str]:
        """Get request body example."""
        if "requestBody" not in operation:
            return None

        content = operation["requestBody"].get("content", {})

        for content_type in ["application/json", "*/*"]:
            if content_type in content:
                media = content[content_type]
                if "example" in media:
                    return json.dumps(media["example"], indent=2)
                if "examples" in media:
                    first_example = next(iter(media["examples"].values()), {})
                    if "value" in first_example:
                        return json.dumps(first_example["value"], indent=2)
                # Try to get from schema
                schema = media.get("schema", {})
                if "example" in schema:
                    return json.dumps(schema["example"], indent=2)

        return None

    def _get_response_example(self, operation: dict[str, Any]) -> Optional[str]:
        """Get response example."""
        responses = operation.get("responses", {})

        # Try 200, 201, 202 in order
        for code in ["200", "201", "202", "default"]:
            if code not in responses:
                continue

            response = responses[code]
            content = response.get("content", {})

            for content_type in ["application/json", "*/*"]:
                if content_type in content:
                    media = content[content_type]
                    if "example" in media:
                        return json.dumps(media["example"], indent=2)
                    if "examples" in media:
                        first_example = next(iter(media["examples"].values()), {})
                        if "value" in first_example:
                            return json.dumps(first_example["value"], indent=2)
                    # Try schema example
                    schema = media.get("schema", {})
                    if "example" in schema:
                        return json.dumps(schema["example"], indent=2)

            # Swagger 2.x style
            if "examples" in response:
                for mime_type, example in response["examples"].items():
                    return json.dumps(example, indent=2)

        return None

    @classmethod
    def parse_file(
        cls,
        file_path: Path,
        api_name: str,
        auth_header: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> list[Endpoint]:
        """Parse an OpenAPI/Swagger file.

        Args:
            file_path: Path to the OpenAPI file (.yaml, .yml, or .json)
            api_name: Name of the API
            auth_header: Authentication header name
            base_url: Base URL for the API

        Returns:
            List of Endpoint objects
        """
        content = file_path.read_text(encoding="utf-8")

        # Parse based on file extension
        if file_path.suffix.lower() in [".yaml", ".yml"]:
            spec = yaml.safe_load(content)
        else:
            spec = json.loads(content)

        parser = cls(api_name, auth_header, base_url)
        return parser.parse(spec)
