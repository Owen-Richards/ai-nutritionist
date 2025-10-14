#!/usr/bin/env python3
"""
API Documentation Generator

Generates comprehensive API documentation from code:
- Extracts FastAPI routes and schemas
- Generates OpenAPI specifications
- Creates human-readable documentation
- Generates client SDKs
- Updates API versioning
"""

import os
import sys
import ast
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import importlib.util
import inspect
from datetime import datetime
import argparse


class APIDocumentationGenerator:
    """Generates API documentation from FastAPI code"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.api_dir = project_root / "src" / "api"
        self.docs_dir = project_root / "docs" / "api"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Discovered API components
        self.routes = []
        self.schemas = []
        self.models = []
        self.dependencies = []
        
    def generate_complete_documentation(self) -> bool:
        """Generate complete API documentation"""
        try:
            print("📚 Generating API documentation...")
            
            # Discover API components
            print("🔍 Discovering API components...")
            self._discover_routes()
            self._discover_schemas()
            self._discover_models()
            self._discover_dependencies()
            
            # Generate OpenAPI specification
            print("📝 Generating OpenAPI specification...")
            openapi_spec = self._generate_openapi_spec()
            self._save_openapi_spec(openapi_spec)
            
            # Generate human-readable documentation
            print("📖 Generating human-readable documentation...")
            self._generate_markdown_docs()
            
            # Generate endpoint documentation
            print("🔗 Generating endpoint documentation...")
            self._generate_endpoint_docs()
            
            # Generate schema documentation
            print("📋 Generating schema documentation...")
            self._generate_schema_docs()
            
            # Generate client examples
            print("💡 Generating client examples...")
            self._generate_client_examples()
            
            # Generate postman collection
            print("📮 Generating Postman collection...")
            self._generate_postman_collection()
            
            print("✅ API documentation generated successfully!")
            return True
            
        except Exception as e:
            print(f"❌ API documentation generation failed: {e}")
            return False
    
    def _discover_routes(self):
        """Discover FastAPI routes from code"""
        routes_dir = self.api_dir / "routes"
        if not routes_dir.exists():
            return
        
        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("__"):
                continue
            
            routes = self._extract_routes_from_file(route_file)
            self.routes.extend(routes)
    
    def _extract_routes_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract route definitions from a Python file"""
        routes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has route decorators
                    route_info = self._extract_route_info(node)
                    if route_info:
                        route_info['file'] = str(file_path.relative_to(self.project_root))
                        route_info['function_name'] = node.name
                        route_info['docstring'] = ast.get_docstring(node)
                        route_info['parameters'] = self._extract_function_parameters(node)
                        routes.append(route_info)
        
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        
        return routes
    
    def _extract_route_info(self, func_node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Extract route information from function decorators"""
        route_info = {}
        
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # @router.get(), @router.post(), etc.
                    if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                        route_info['method'] = decorator.func.attr.upper()
                        
                        # Extract path
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Str):
                                route_info['path'] = decorator.args[0].s
                            elif isinstance(decorator.args[0], ast.Constant):
                                route_info['path'] = decorator.args[0].value
                        
                        # Extract keyword arguments
                        for keyword in decorator.keywords:
                            if keyword.arg == 'response_model':
                                route_info['response_model'] = self._extract_ast_value(keyword.value)
                            elif keyword.arg == 'status_code':
                                route_info['status_code'] = self._extract_ast_value(keyword.value)
                            elif keyword.arg == 'tags':
                                route_info['tags'] = self._extract_ast_value(keyword.value)
                            elif keyword.arg == 'summary':
                                route_info['summary'] = self._extract_ast_value(keyword.value)
                            elif keyword.arg == 'description':
                                route_info['description'] = self._extract_ast_value(keyword.value)
        
        return route_info if 'method' in route_info and 'path' in route_info else None
    
    def _extract_ast_value(self, node) -> Any:
        """Extract value from AST node"""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.List):
            return [self._extract_ast_value(item) for item in node.elts]
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return str(node)
    
    def _extract_function_parameters(self, func_node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Extract function parameters and their types"""
        parameters = []
        
        for arg in func_node.args.args:
            param_info = {
                'name': arg.arg,
                'type': None,
                'default': None,
                'annotation': None
            }
            
            # Extract type annotation
            if arg.annotation:
                param_info['annotation'] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
            
            parameters.append(param_info)
        
        # Handle defaults
        defaults = func_node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                param_index = len(parameters) - len(defaults) + i
                if param_index >= 0:
                    parameters[param_index]['default'] = self._extract_ast_value(default)
        
        return parameters
    
    def _discover_schemas(self):
        """Discover Pydantic schemas"""
        schemas_dir = self.api_dir.parent / "schemas"
        if schemas_dir.exists():
            for schema_file in schemas_dir.rglob("*.py"):
                if schema_file.name.startswith("__"):
                    continue
                schemas = self._extract_schemas_from_file(schema_file)
                self.schemas.extend(schemas)
    
    def _extract_schemas_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract Pydantic schema definitions"""
        schemas = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class inherits from BaseModel
                    if self._inherits_from_basemodel(node):
                        schema_info = {
                            'name': node.name,
                            'file': str(file_path.relative_to(self.project_root)),
                            'docstring': ast.get_docstring(node),
                            'fields': self._extract_pydantic_fields(node)
                        }
                        schemas.append(schema_info)
        
        except Exception as e:
            print(f"Warning: Could not parse schema file {file_path}: {e}")
        
        return schemas
    
    def _inherits_from_basemodel(self, class_node: ast.ClassDef) -> bool:
        """Check if class inherits from Pydantic BaseModel"""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                return True
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                return True
        return False
    
    def _extract_pydantic_fields(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract Pydantic field definitions"""
        fields = []
        
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign):
                field_info = {
                    'name': node.target.id if isinstance(node.target, ast.Name) else str(node.target),
                    'type': ast.unparse(node.annotation) if hasattr(ast, 'unparse') else str(node.annotation),
                    'default': self._extract_ast_value(node.value) if node.value else None
                }
                fields.append(field_info)
        
        return fields
    
    def _discover_models(self):
        """Discover data models"""
        models_dir = self.api_dir.parent / "models"
        if models_dir.exists():
            for model_file in models_dir.rglob("*.py"):
                if model_file.name.startswith("__"):
                    continue
                models = self._extract_models_from_file(model_file)
                self.models.extend(models)
    
    def _extract_models_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract model definitions"""
        # Similar to schema extraction but for domain models
        return []
    
    def _discover_dependencies(self):
        """Discover FastAPI dependencies"""
        # Extract dependency functions and classes
        pass
    
    def _generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification"""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "AI Nutritionist API",
                "description": "Comprehensive API for AI-powered nutrition assistance",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@ai-nutritionist.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "https://api.ai-nutritionist.com/v1",
                    "description": "Production server"
                },
                {
                    "url": "https://staging-api.ai-nutritionist.com/v1",
                    "description": "Staging server"
                },
                {
                    "url": "http://localhost:8000/v1",
                    "description": "Development server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            },
            "security": [
                {"BearerAuth": []}
            ],
            "tags": []
        }
        
        # Add paths from discovered routes
        for route in self.routes:
            path = route['path']
            method = route['method'].lower()
            
            if path not in spec['paths']:
                spec['paths'][path] = {}
            
            operation = {
                "summary": route.get('summary', route.get('function_name', '')),
                "description": route.get('description') or route.get('docstring', ''),
                "operationId": f"{method}_{route['function_name']}",
                "tags": route.get('tags', []),
                "parameters": self._generate_openapi_parameters(route),
                "responses": self._generate_openapi_responses(route)
            }
            
            # Add request body for POST/PUT/PATCH
            if method in ['post', 'put', 'patch']:
                operation["requestBody"] = self._generate_openapi_request_body(route)
            
            spec['paths'][path][method] = operation
        
        # Add schemas from discovered Pydantic models
        for schema in self.schemas:
            spec['components']['schemas'][schema['name']] = self._generate_openapi_schema(schema)
        
        # Extract unique tags
        all_tags = set()
        for route in self.routes:
            if 'tags' in route:
                all_tags.update(route['tags'])
        
        spec['tags'] = [{"name": tag} for tag in sorted(all_tags)]
        
        return spec
    
    def _generate_openapi_parameters(self, route: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate OpenAPI parameters from route info"""
        parameters = []
        
        # Extract path parameters
        path = route.get('path', '')
        import re
        path_params = re.findall(r'{(\w+)}', path)
        
        for param in path_params:
            parameters.append({
                "name": param,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": f"{param} parameter"
            })
        
        # Add query parameters based on function parameters
        for param in route.get('parameters', []):
            if param['name'] not in ['self'] + path_params:
                param_def = {
                    "name": param['name'],
                    "in": "query",
                    "required": param.get('default') is None,
                    "schema": self._get_openapi_type(param.get('annotation', 'str'))
                }
                
                if param.get('default') is not None:
                    param_def["schema"]["default"] = param['default']
                
                parameters.append(param_def)
        
        return parameters
    
    def _generate_openapi_responses(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAPI responses"""
        responses = {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            },
            "400": {
                "description": "Bad request"
            },
            "401": {
                "description": "Unauthorized"
            },
            "422": {
                "description": "Validation error"
            },
            "500": {
                "description": "Internal server error"
            }
        }
        
        # Override with specific status code if defined
        if 'status_code' in route:
            status_code = str(route['status_code'])
            if status_code in responses:
                responses[status_code] = responses.pop("200")
        
        # Add response model if defined
        if 'response_model' in route:
            responses["200"]["content"]["application/json"]["schema"] = {
                "$ref": f"#/components/schemas/{route['response_model']}"
            }
        
        return responses
    
    def _generate_openapi_request_body(self, route: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAPI request body"""
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            }
        }
    
    def _generate_openapi_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAPI schema from Pydantic model"""
        schema_def = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        if schema.get('docstring'):
            schema_def["description"] = schema['docstring']
        
        for field in schema.get('fields', []):
            field_schema = self._get_openapi_type(field['type'])
            
            if field.get('default') is not None:
                field_schema["default"] = field['default']
            else:
                schema_def["required"].append(field['name'])
            
            schema_def["properties"][field['name']] = field_schema
        
        return schema_def
    
    def _get_openapi_type(self, type_annotation: str) -> Dict[str, Any]:
        """Convert Python type annotation to OpenAPI type"""
        type_mapping = {
            'str': {"type": "string"},
            'int': {"type": "integer"},
            'float': {"type": "number"},
            'bool': {"type": "boolean"},
            'list': {"type": "array", "items": {"type": "string"}},
            'dict': {"type": "object"},
            'datetime': {"type": "string", "format": "date-time"},
            'date': {"type": "string", "format": "date"},
            'Optional[str]': {"type": "string", "nullable": True},
            'Optional[int]': {"type": "integer", "nullable": True},
        }
        
        return type_mapping.get(type_annotation, {"type": "string"})
    
    def _save_openapi_spec(self, spec: Dict[str, Any]):
        """Save OpenAPI specification to files"""
        # Save as JSON
        json_file = self.docs_dir / "openapi.json"
        with open(json_file, 'w') as f:
            json.dump(spec, f, indent=2)
        
        # Save as YAML
        yaml_file = self.docs_dir / "openapi.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
        
        print(f"OpenAPI specification saved to {json_file} and {yaml_file}")
    
    def _generate_markdown_docs(self):
        """Generate human-readable Markdown documentation"""
        
        # Main API documentation
        api_doc = [
            "# AI Nutritionist API Documentation",
            "",
            f"Generated on: {datetime.utcnow().isoformat()}",
            "",
            "## Overview",
            "",
            "The AI Nutritionist API provides comprehensive nutrition assistance through AI-powered meal planning, recipe recommendations, and personalized dietary guidance.",
            "",
            "## Base URLs",
            "",
            "- **Production**: `https://api.ai-nutritionist.com/v1`",
            "- **Staging**: `https://staging-api.ai-nutritionist.com/v1`",
            "- **Development**: `http://localhost:8000/v1`",
            "",
            "## Authentication",
            "",
            "All API endpoints require authentication using JWT tokens passed in the Authorization header:",
            "",
            "```",
            "Authorization: Bearer <your_jwt_token>",
            "```",
            "",
            "## Rate Limiting",
            "",
            "API requests are rate limited to prevent abuse:",
            "",
            "- **Standard endpoints**: 100 requests per minute",
            "- **AI generation endpoints**: 10 requests per minute",
            "- **Bulk operations**: 5 requests per minute",
            "",
            "## Endpoints",
            ""
        ]
        
        # Group routes by tags
        routes_by_tag = {}
        for route in self.routes:
            tags = route.get('tags', ['General'])
            for tag in tags:
                if tag not in routes_by_tag:
                    routes_by_tag[tag] = []
                routes_by_tag[tag].append(route)
        
        # Generate documentation for each tag
        for tag, tag_routes in sorted(routes_by_tag.items()):
            api_doc.extend([
                f"### {tag}",
                ""
            ])
            
            for route in tag_routes:
                api_doc.extend([
                    f"#### {route['method']} {route['path']}",
                    "",
                    route.get('docstring', 'No description available.'),
                    "",
                    f"**Function**: `{route['function_name']}`",
                    f"**File**: `{route['file']}`",
                    ""
                ])
                
                # Parameters
                if route.get('parameters'):
                    api_doc.extend([
                        "**Parameters**:",
                        ""
                    ])
                    
                    for param in route['parameters']:
                        param_type = param.get('annotation', 'unknown')
                        default = f" (default: {param['default']})" if param.get('default') is not None else ""
                        api_doc.append(f"- `{param['name']}` ({param_type}){default}")
                    
                    api_doc.append("")
                
                # Example request
                api_doc.extend([
                    "**Example Request**:",
                    "",
                    "```bash",
                    f"curl -X {route['method']} \\",
                    f"  'https://api.ai-nutritionist.com/v1{route['path']}' \\",
                    "  -H 'Authorization: Bearer <token>' \\",
                    "  -H 'Content-Type: application/json'",
                    "```",
                    "",
                    "---",
                    ""
                ])
        
        # Save main documentation
        main_doc_file = self.docs_dir / "README.md"
        with open(main_doc_file, 'w') as f:
            f.write('\n'.join(api_doc))
        
        print(f"API documentation saved to {main_doc_file}")
    
    def _generate_endpoint_docs(self):
        """Generate detailed endpoint documentation"""
        endpoints_dir = self.docs_dir / "endpoints"
        endpoints_dir.mkdir(exist_ok=True)
        
        for route in self.routes:
            # Create endpoint-specific documentation
            endpoint_doc = [
                f"# {route['method']} {route['path']}",
                "",
                route.get('docstring', 'No description available.'),
                "",
                f"**Implementation**: `{route['function_name']}` in `{route['file']}`",
                "",
                "## Request",
                ""
            ]
            
            # Request details
            if route.get('parameters'):
                endpoint_doc.extend([
                    "### Parameters",
                    ""
                ])
                
                for param in route['parameters']:
                    endpoint_doc.extend([
                        f"#### `{param['name']}`",
                        "",
                        f"- **Type**: {param.get('annotation', 'unknown')}",
                        f"- **Required**: {'No' if param.get('default') is not None else 'Yes'}",
                    ])
                    
                    if param.get('default') is not None:
                        endpoint_doc.append(f"- **Default**: `{param['default']}`")
                    
                    endpoint_doc.append("")
            
            # Response
            endpoint_doc.extend([
                "## Response",
                "",
                "### Success Response",
                "",
                "```json",
                "{",
                '  "success": true,',
                '  "data": {},',
                '  "message": "Operation completed successfully"',
                "}",
                "```",
                "",
                "### Error Response",
                "",
                "```json",
                "{",
                '  "success": false,',
                '  "message": "Error description",',
                '  "errors": ["Detailed error messages"]',
                "}",
                "```",
                ""
            ])
            
            # Examples
            endpoint_doc.extend([
                "## Examples",
                "",
                "### cURL",
                "",
                "```bash",
                f"curl -X {route['method']} \\",
                f"  'https://api.ai-nutritionist.com/v1{route['path']}' \\",
                "  -H 'Authorization: Bearer <your_token>' \\",
                "  -H 'Content-Type: application/json'",
                "```",
                "",
                "### Python",
                "",
                "```python",
                "import requests",
                "",
                "headers = {",
                "    'Authorization': 'Bearer <your_token>',",
                "    'Content-Type': 'application/json'",
                "}",
                "",
                f"response = requests.{route['method'].lower()}(",
                f"    'https://api.ai-nutritionist.com/v1{route['path']}',",
                "    headers=headers",
                ")",
                "",
                "print(response.json())",
                "```",
                ""
            ])
            
            # Save endpoint documentation
            filename = f"{route['method'].lower()}_{route['path'].replace('/', '_').replace('{', '').replace('}', '')}.md"
            endpoint_file = endpoints_dir / filename
            
            with open(endpoint_file, 'w') as f:
                f.write('\n'.join(endpoint_doc))
    
    def _generate_schema_docs(self):
        """Generate schema documentation"""
        schemas_dir = self.docs_dir / "schemas"
        schemas_dir.mkdir(exist_ok=True)
        
        # Schema index
        schema_index = [
            "# API Schemas",
            "",
            "This directory contains documentation for all API schemas and data models.",
            "",
            "## Available Schemas",
            ""
        ]
        
        for schema in self.schemas:
            schema_name = schema['name']
            schema_index.append(f"- [{schema_name}](./{schema_name.lower()}.md)")
            
            # Generate individual schema documentation
            schema_doc = [
                f"# {schema_name} Schema",
                "",
                schema.get('docstring', 'No description available.'),
                "",
                f"**File**: `{schema['file']}`",
                "",
                "## Fields",
                ""
            ]
            
            for field in schema.get('fields', []):
                schema_doc.extend([
                    f"### `{field['name']}`",
                    "",
                    f"- **Type**: `{field['type']}`",
                ])
                
                if field.get('default') is not None:
                    schema_doc.append(f"- **Default**: `{field['default']}`")
                    schema_doc.append("- **Required**: No")
                else:
                    schema_doc.append("- **Required**: Yes")
                
                schema_doc.append("")
            
            # Example JSON
            schema_doc.extend([
                "## Example",
                "",
                "```json",
                "{",
            ])
            
            for i, field in enumerate(schema.get('fields', [])):
                comma = "," if i < len(schema['fields']) - 1 else ""
                example_value = self._get_example_value(field['type'])
                schema_doc.append(f'  "{field["name"]}": {json.dumps(example_value)}{comma}')
            
            schema_doc.extend([
                "}",
                "```",
                ""
            ])
            
            # Save schema documentation
            schema_file = schemas_dir / f"{schema_name.lower()}.md"
            with open(schema_file, 'w') as f:
                f.write('\n'.join(schema_doc))
        
        schema_index.append("")
        
        # Save schema index
        index_file = schemas_dir / "README.md"
        with open(index_file, 'w') as f:
            f.write('\n'.join(schema_index))
    
    def _get_example_value(self, field_type: str) -> Any:
        """Get example value for field type"""
        examples = {
            'str': "example_string",
            'int': 42,
            'float': 3.14,
            'bool': True,
            'datetime': "2025-10-12T10:30:00Z",
            'list': ["item1", "item2"],
            'dict': {"key": "value"}
        }
        
        return examples.get(field_type, "example_value")
    
    def _generate_client_examples(self):
        """Generate client code examples"""
        examples_dir = self.docs_dir / "examples"
        examples_dir.mkdir(exist_ok=True)
        
        # Python client example
        python_example = '''"""
AI Nutritionist API Python Client Example

This example demonstrates how to use the AI Nutritionist API with Python.
"""

import requests
import json
from typing import Dict, Any, Optional


class AINutritionistClient:
    """Python client for AI Nutritionist API"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
    
    # User Profile Methods
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile"""
        return self._make_request('GET', f'/users/{user_id}')
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile"""
        return self._make_request('PUT', f'/users/{user_id}', profile_data)
    
    # Meal Planning Methods
    def get_meal_plans(self, user_id: str) -> Dict[str, Any]:
        """Get user's meal plans"""
        return self._make_request('GET', f'/meal-plans?user_id={user_id}')
    
    def create_meal_plan(self, meal_plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new meal plan"""
        return self._make_request('POST', '/meal-plans', meal_plan_data)
    
    # Recipe Methods
    def search_recipes(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Search recipes"""
        params = f'?q={query}'
        if filters:
            for key, value in filters.items():
                params += f'&{key}={value}'
        
        return self._make_request('GET', f'/recipes{params}')
    
    def get_recipe(self, recipe_id: str) -> Dict[str, Any]:
        """Get recipe details"""
        return self._make_request('GET', f'/recipes/{recipe_id}')


# Example usage
if __name__ == "__main__":
    # Initialize client
    client = AINutritionistClient(
        base_url="https://api.ai-nutritionist.com/v1",
        api_token="your_api_token_here"
    )
    
    try:
        # Get user profile
        user_profile = client.get_user_profile("user123")
        print(f"User: {user_profile['data']['name']}")
        
        # Search for vegetarian recipes
        recipes = client.search_recipes("vegetarian", {"difficulty": "easy"})
        print(f"Found {len(recipes['data'])} vegetarian recipes")
        
        # Get meal plans
        meal_plans = client.get_meal_plans("user123")
        print(f"User has {len(meal_plans['data'])} meal plans")
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
'''
        
        python_file = examples_dir / "python_client.py"
        with open(python_file, 'w') as f:
            f.write(python_example)
        
        # JavaScript client example
        js_example = '''/**
 * AI Nutritionist API JavaScript Client Example
 * 
 * This example demonstrates how to use the AI Nutritionist API with JavaScript.
 */

class AINutritionistClient {
    constructor(baseUrl, apiToken) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = {
            'Authorization': `Bearer ${apiToken}`,
            'Content-Type': 'application/json'
        };
    }

    async _makeRequest(method, endpoint, data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const options = {
            method,
            headers: this.headers
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }

    // User Profile Methods
    async getUserProfile(userId) {
        return await this._makeRequest('GET', `/users/${userId}`);
    }

    async updateUserProfile(userId, profileData) {
        return await this._makeRequest('PUT', `/users/${userId}`, profileData);
    }

    // Meal Planning Methods
    async getMealPlans(userId) {
        return await this._makeRequest('GET', `/meal-plans?user_id=${userId}`);
    }

    async createMealPlan(mealPlanData) {
        return await this._makeRequest('POST', '/meal-plans', mealPlanData);
    }

    // Recipe Methods
    async searchRecipes(query, filters = {}) {
        const params = new URLSearchParams({ q: query, ...filters });
        return await this._makeRequest('GET', `/recipes?${params}`);
    }

    async getRecipe(recipeId) {
        return await this._makeRequest('GET', `/recipes/${recipeId}`);
    }
}

// Example usage
async function example() {
    // Initialize client
    const client = new AINutritionistClient(
        'https://api.ai-nutritionist.com/v1',
        'your_api_token_here'
    );

    try {
        // Get user profile
        const userProfile = await client.getUserProfile('user123');
        console.log(`User: ${userProfile.data.name}`);

        // Search for vegetarian recipes
        const recipes = await client.searchRecipes('vegetarian', { difficulty: 'easy' });
        console.log(`Found ${recipes.data.length} vegetarian recipes`);

        // Get meal plans
        const mealPlans = await client.getMealPlans('user123');
        console.log(`User has ${mealPlans.data.length} meal plans`);

    } catch (error) {
        console.error('API request failed:', error);
    }
}

// Run example
example();
'''
        
        js_file = examples_dir / "javascript_client.js"
        with open(js_file, 'w') as f:
            f.write(js_example)
        
        print(f"Client examples saved to {examples_dir}")
    
    def _generate_postman_collection(self):
        """Generate Postman collection"""
        collection = {
            "info": {
                "name": "AI Nutritionist API",
                "description": "Complete API collection for AI Nutritionist",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{api_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "https://api.ai-nutritionist.com/v1",
                    "type": "string"
                },
                {
                    "key": "api_token",
                    "value": "your_api_token_here",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # Group requests by tags
        for route in self.routes:
            request_item = {
                "name": f"{route['method']} {route['path']}",
                "request": {
                    "method": route['method'],
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}" + route['path'],
                        "host": ["{{base_url}}"],
                        "path": route['path'].strip('/').split('/')
                    },
                    "description": route.get('docstring', '')
                },
                "response": []
            }
            
            # Add request body for POST/PUT/PATCH
            if route['method'] in ['POST', 'PUT', 'PATCH']:
                request_item["request"]["body"] = {
                    "mode": "raw",
                    "raw": "{}",
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                }
            
            collection["item"].append(request_item)
        
        # Save Postman collection
        postman_file = self.docs_dir / "AI_Nutritionist_API.postman_collection.json"
        with open(postman_file, 'w') as f:
            json.dump(collection, f, indent=2)
        
        print(f"Postman collection saved to {postman_file}")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="API Documentation Generator")
    parser.add_argument("--output-dir", help="Output directory for documentation")
    parser.add_argument("--format", choices=["all", "openapi", "markdown", "postman"], 
                       default="all", help="Documentation format to generate")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    generator = APIDocumentationGenerator(project_root)
    
    if args.output_dir:
        generator.docs_dir = Path(args.output_dir)
        generator.docs_dir.mkdir(parents=True, exist_ok=True)
    
    success = generator.generate_complete_documentation()
    
    if success:
        print(f"\n✅ API documentation generated successfully in {generator.docs_dir}")
    else:
        print("\n❌ API documentation generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
