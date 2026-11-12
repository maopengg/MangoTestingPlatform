# -*- coding: utf-8 -*-
import ast

from mangotools.git import PytestNodeTypeEnum


class PytestMethodNodeService:
    @classmethod
    def list_nodes(cls, file_path: str, content: str) -> list[dict]:
        return cls._ast_nodes_from_content(content, file_path)

    @classmethod
    def _ast_nodes_from_content(cls, content: str, display_path: str, filename: str | None = None) -> list[dict]:
        tree = ast.parse(content or "", filename=filename or display_path)
        nodes = []
        for item in tree.body:
            if isinstance(item, ast.FunctionDef) and cls._is_test_name(item.name):
                nodes.append(
                    cls._node(
                        filename or display_path,
                        display_path,
                        item.name,
                        line_number=item.lineno,
                    )
                )
            if isinstance(item, ast.ClassDef) and item.name.startswith("Test"):
                for child in item.body:
                    if isinstance(child, ast.FunctionDef) and cls._is_test_name(child.name):
                        nodes.append(
                            cls._node(
                                filename or display_path,
                                display_path,
                                child.name,
                                class_name=item.name,
                                line_number=child.lineno,
                            )
                        )
        return nodes

    @staticmethod
    def _node(
            abs_path: str,
            display_path: str,
            method_name: str,
            class_name: str | None = None,
            line_number: int | None = None,
    ) -> dict:
        nodeid = f"{display_path}::{class_name}::{method_name}" if class_name else f"{display_path}::{method_name}"
        return {
            "file_path": display_path,
            "nodeid": nodeid,
            "node_type": PytestNodeTypeEnum.METHOD.value,
            "class_name": class_name,
            "method_name": method_name,
            "parameter_id": None,
            "display_name": method_name,
            "line_number": line_number,
        }

    @staticmethod
    def _is_test_name(name: str) -> bool:
        return name.startswith("test_") or name.endswith("_test")

    @staticmethod
    def _parameter_id(method_name: str) -> str | None:
        if "[" not in method_name or not method_name.endswith("]"):
            return None
        return method_name.rsplit("[", 1)[-1][:-1]
