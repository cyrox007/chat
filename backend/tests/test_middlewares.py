import ast
import inspect
import textwrap
import unittest

from middlewares import csrf_middleware


class MiddlewareTests(unittest.TestCase):
    def test_csrf_try_blocks_do_not_wrap_downstream_call_next(self):
        tree = ast.parse(textwrap.dedent(inspect.getsource(csrf_middleware)))
        handler = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "csrf_handler"
        )

        try_blocks = [node for node in ast.walk(handler) if isinstance(node, ast.Try)]
        self.assertTrue(try_blocks)

        for try_block in try_blocks:
            wrapped_names = {
                node.id
                for statement in try_block.body
                for node in ast.walk(statement)
                if isinstance(node, ast.Name)
            }
            self.assertNotIn("call_next", wrapped_names)

        handler_names = {node.id for node in ast.walk(handler) if isinstance(node, ast.Name)}
        self.assertIn("call_next", handler_names)
        self.assertIn("validate_csrf_token", handler_names)


if __name__ == "__main__":
    unittest.main()
