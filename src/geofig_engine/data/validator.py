"""
Function expression validator.

Validates mathematical expressions for safety and correctness,
ensuring variables exist and types match declarations.
"""

import ast
import re
from typing import Set

from geofig_engine.data.functions import FunctionType


class FunctionValidator:
    """Validates function expressions and metadata."""

    # Allowed built-in functions in expressions
    ALLOWED_FUNCTIONS = {
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
        'sinh', 'cosh', 'tanh',
        'sqrt', 'exp', 'log', 'log10', 'ln', 'abs',
        'ceil', 'floor', 'round',
        'pi', 'e'
    }

    # Allowed operators
    ALLOWED_OPERATORS = {'+', '-', '*', '/', '//', '%', '**', '^'}

    @staticmethod
    def validate_expression(
        expression: str,
        variables: tuple[str, ...],
        func_type: FunctionType | None = None
    ) -> tuple[bool, str]:
        """
        Validate function expression for safety and correctness.

        Args:
            expression: Mathematical expression string
            variables: Expected variables in the expression
            func_type: Optional function type for additional validation

        Returns:
            (is_valid, error_message)
        """
        # Check for empty expression
        if not expression or not isinstance(expression, str):
            return False, "Expression must be a non-empty string"

        # Check for empty variables
        if not variables:
            return False, "Variables tuple cannot be empty"

        try:
            # Extract variables from expression
            extracted_vars = FunctionValidator.extract_variables(expression)

            # Check that all declared variables are present in expression
            declared_vars = set(variables)
            undefined_declared = declared_vars - extracted_vars
            if undefined_declared:
                return False, f"Declared variables not in expression: {undefined_declared}"

            # Check that no unexpected variables appear
            unexpected = extracted_vars - declared_vars
            if unexpected:
                # Filter out known constants
                unexpected = unexpected - {'pi', 'e'}
                if unexpected:
                    return False, f"Unexpected variables in expression: {unexpected}"

            # Type-specific validation
            if func_type is not None:
                is_valid, msg = FunctionValidator._validate_type_match(expression, func_type)
                if not is_valid:
                    return False, msg

            return True, ""

        except Exception as e:
            return False, f"Expression parsing error: {str(e)}"

    @staticmethod
    def extract_variables(expression: str) -> Set[str]:
        """
        Extract all variable names from expression.

        Returns:
            Set of variable names found in the expression
        """
        # Replace common math functions with placeholders to avoid parsing issues
        modified_expr = expression
        for func_name in FunctionValidator.ALLOWED_FUNCTIONS:
            modified_expr = re.sub(rf'\b{func_name}\s*\(', f'f(', modified_expr)

        try:
            tree = ast.parse(modified_expr, mode='eval')
            variables = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    variables.add(node.id)

            return variables
        except SyntaxError:
            # Fallback: simple regex-based extraction for robustness
            # Match word-like identifiers
            matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', expression)
            return set(matches)

    @staticmethod
    def _validate_type_match(expression: str, func_type: FunctionType) -> tuple[bool, str]:
        """
        Validate that expression structure matches declared function type.

        Args:
            expression: Mathematical expression
            func_type: Declared function type

        Returns:
            (is_valid, error_message)
        """
        if func_type == FunctionType.LINEAR:
            # Linear should not have exponents > 1 or non-linear operations
            if '**' in expression and not re.search(r'\*\*\s*1(?:\D|$)', expression):
                # Exponent that's not ^1
                if re.search(r'\*\*\s*[^1]', expression):
                    return False, "LINEAR type should not contain exponents > 1"
            if '^' in expression:
                if not re.search(r'\^\s*1(?:\D|$)', expression):
                    return False, "LINEAR type should not contain exponents > 1"

        elif func_type == FunctionType.POLYNOMIAL:
            # Polynomial should have power operations
            if '**' not in expression and '^' not in expression:
                # Could be constant, but typically polynomials have powers
                pass

        elif func_type == FunctionType.EXPONENTIAL:
            # Should contain exp() or base^x patterns
            if 'exp' not in expression and '^' not in expression and '**' not in expression:
                return False, "EXPONENTIAL type should contain exp() or power operation"

        elif func_type == FunctionType.LOGARITHMIC:
            # Should contain log, ln, or log10
            if not any(func in expression for func in ['log', 'ln', 'log10']):
                return False, "LOGARITHMIC type should contain log, ln, or log10"

        elif func_type == FunctionType.POWER:
            # Should contain x^n or x**n
            if '**' not in expression and '^' not in expression:
                return False, "POWER type should contain exponentiation"

        return True, ""

    @staticmethod
    def validate_variables(variables: tuple[str, ...]) -> tuple[bool, str]:
        """
        Validate variable names are valid identifiers.

        Args:
            variables: Tuple of variable names

        Returns:
            (is_valid, error_message)
        """
        if not variables:
            return False, "Variables tuple cannot be empty"

        for var in variables:
            if not isinstance(var, str):
                return False, f"Variable '{var}' is not a string"
            if not var.isidentifier():
                return False, f"Variable '{var}' is not a valid Python identifier"
            if var in FunctionValidator.ALLOWED_FUNCTIONS:
                return False, f"Variable '{var}' conflicts with reserved function name"

        # Check for duplicates
        if len(variables) != len(set(variables)):
            return False, "Duplicate variables found"

        return True, ""
